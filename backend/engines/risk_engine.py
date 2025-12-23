"""
Risk Engine P0 - Guardrails + 2R/1R Money Management

Commit 1: AGGRESSIVE non destructif (allowlist/denylist)
Commit 2: Guardrails runtime (kill-switch, circuit breakers)
Commit 3: Money Management 2R/1R (TwoTierRiskState)
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from models.risk import (
    RiskEngineState, 
    PositionSizingResult, 
    TwoTierRiskState,
    PlaybookStats,
    DailyStats
)
from models.setup import Setup
from config.settings import settings

logger = logging.getLogger(__name__)


# ============================================================================
# P0 COMMIT 1: ALLOWLIST/DENYLIST PLAYBOOKS
# ============================================================================

# Playbooks AUTORISÉS en mode AGGRESSIVE (baseline +88R + A+ fonctionnels)
AGGRESSIVE_ALLOWLIST = [
    'News_Fade',                               # +90.64R, 32.5% WR ✅
    'Session_Open_Scalp',                      # -2.4R, 38.4% WR ✅
    'SCALP_Aplus_1_Mini_FVG_Retest_NY_Open',   # +10.5R, 41% WR ✅ (SNIPER)
    # Playbooks du YAML (activation progressive selon calibration)
    'NY_Open_Reversal',
    'Trend_Continuation_FVG_Retest',
    'Morning_Trap_Reversal',
    'Liquidity_Sweep_Scalp',
    'FVG_Fill_Scalp',
]

# Playbooks DÉSACTIVÉS (destructeurs ou non calibrés)
AGGRESSIVE_DENYLIST = [
    'London_Sweep_NY_Continuation',            # -326R ❌
    'BOS_Momentum_Scalp',                      # -142R ❌
    'Power_Hour_Expansion',                    # -31R ❌
    'DAY_Aplus_1_Liquidity_Sweep_OB_Retest',   # Sweep/BOS non détectés ❌
    'Lunch_Range_Scalp',                       # Toxique ❌
]

# Playbooks AUTORISÉS en mode SAFE (sniper A+ uniquement)
SAFE_ALLOWLIST = [
    'SCALP_Aplus_1_Mini_FVG_Retest_NY_Open',   # SNIPER mode
]


# ============================================================================
# P0 COMMIT 2: GUARDRAILS CONSTANTS
# ============================================================================

# Kill-switch playbook
KILLSWITCH_MIN_TRADES = 30          # N minimum de trades avant évaluation
KILLSWITCH_MAX_LOSS_R = -10.0       # Total_R max avant disable
KILLSWITCH_MIN_PF = 0.85            # PF minimum
KILLSWITCH_HARD_STOP_R = -25.0      # Hard stop immédiat

# Circuit breakers
CIRCUIT_STOP_DAY_R = -4.0           # Stop day si PnL_day ≤ -4R
CIRCUIT_STOP_RUN_DD_R = 20.0        # Stop run si MaxDD ≥ 20R
CIRCUIT_MAX_TRADES_DAY_SYMBOL = 12  # Max trades/day/symbol

# Anti-spam settings
COOLDOWN_MINUTES = 15               # Cooldown entre 2 trades du même playbook/symbol
MAX_TRADES_PER_SESSION_PLAYBOOK = 1 # Max trades par playbook par session


class RiskEngine:
    """
    Moteur de gestion du risque avec guardrails P0.
    
    Features:
    - Allowlist/Denylist playbooks (autorité finale)
    - Kill-switch par playbook (runtime)
    - Circuit breakers (stop_day, stop_run, cap trades)
    - Money Management 2R/1R
    """
    
    def __init__(self, initial_capital: float = None):
        initial_capital = initial_capital or settings.INITIAL_CAPITAL
        
        # Calculer base_r_unit (1R = 2% du capital initial)
        base_r_unit = initial_capital * 0.02
        
        self.state = RiskEngineState(
            account_balance=initial_capital,
            initial_capital=initial_capital,
            peak_balance=initial_capital,
            trading_mode=settings.TRADING_MODE,
            base_r_unit_dollars=base_r_unit,
        )
        
        logger.info(f"RiskEngine P0 initialized: ${initial_capital:,.2f}, "
                   f"mode={self.state.trading_mode}, 1R=${base_r_unit:.2f}")
    
    # ========================================================================
    # P0 COMMIT 1: PLAYBOOK AUTHORIZATION
    # ========================================================================
    
    def is_playbook_allowed(self, playbook_name: str) -> tuple[bool, str]:
        """
        Vérifie si un playbook est autorisé selon mode + allowlist/denylist.
        
        Returns:
            (allowed: bool, reason: str)
        """
        mode = self.state.trading_mode
        
        # Check denylist globale (prioritaire)
        if playbook_name in AGGRESSIVE_DENYLIST:
            return False, f"Playbook '{playbook_name}' is in DENYLIST (destructeur)"
        
        # Check si désactivé par kill-switch runtime
        if playbook_name in self.state.disabled_playbooks:
            stats = self.state.playbook_stats.get(playbook_name)
            reason = stats.disable_reason if stats else "kill-switch triggered"
            return False, f"Playbook '{playbook_name}' disabled: {reason}"
        
        # Check allowlist selon mode
        if mode == 'SAFE':
            if playbook_name not in SAFE_ALLOWLIST:
                return False, f"Playbook '{playbook_name}' not in SAFE allowlist"
        else:  # AGGRESSIVE
            if playbook_name not in AGGRESSIVE_ALLOWLIST:
                return False, f"Playbook '{playbook_name}' not in AGGRESSIVE allowlist"
        
        return True, "OK"
    
    def check_cooldown_and_session_limit(self, setup: Setup, current_time: datetime, current_session: str) -> tuple[bool, str]:
        """
        Vérifie le cooldown et les limites par session pour anti-spam.
        
        Returns:
            (allowed: bool, reason: str)
        """
        # Extract playbook name
        playbook_name = "UNKNOWN"
        if setup.playbook_matches:
            playbook_name = setup.playbook_matches[0].playbook_name
        
        key_cooldown = (setup.symbol, playbook_name)
        key_session = (setup.symbol, playbook_name, current_session)
        
        # Check cooldown
        if key_cooldown in self.state.last_trade_time:
            last_time = self.state.last_trade_time[key_cooldown]
            elapsed = (current_time - last_time).total_seconds() / 60.0
            if elapsed < COOLDOWN_MINUTES:
                return False, f"Cooldown active ({elapsed:.1f}/{COOLDOWN_MINUTES}min)"
        
        # Check session limit
        session_count = self.state.trades_per_session.get(key_session, 0)
        if session_count >= MAX_TRADES_PER_SESSION_PLAYBOOK:
            return False, f"Max trades per session reached ({session_count}/{MAX_TRADES_PER_SESSION_PLAYBOOK})"
        
        return True, "OK"
    
    def record_trade_for_cooldown(self, setup: Setup, current_time: datetime, current_session: str):
        """Enregistre un trade pour le tracking cooldown/session."""
        playbook_name = "UNKNOWN"
        if setup.playbook_matches:
            playbook_name = setup.playbook_matches[0].playbook_name
        
        key_cooldown = (setup.symbol, playbook_name)
        key_session = (setup.symbol, playbook_name, current_session)
        
        self.state.last_trade_time[key_cooldown] = current_time
        self.state.trades_per_session[key_session] = self.state.trades_per_session.get(key_session, 0) + 1
    
    def filter_setups_by_playbook(self, setups: List[Setup]) -> List[Setup]:
        """
        Filtre les setups selon allowlist/denylist + kill-switch.
        Cette méthode est l'AUTORITÉ FINALE pour les playbooks.
        """
        filtered = []
        for setup in setups:
            if not setup.playbook_matches:
                continue
            
            # Check chaque playbook matché
            allowed_matches = []
            for pb_match in setup.playbook_matches:
                allowed, reason = self.is_playbook_allowed(pb_match.playbook_name)
                if allowed:
                    allowed_matches.append(pb_match)
                else:
                    logger.debug(f"Setup filtered: {reason}")
            
            if allowed_matches:
                # Garder le setup avec seulement les playbooks autorisés
                setup.playbook_matches = allowed_matches
                filtered.append(setup)
        
        logger.info(f"RiskEngine playbook filter: {len(setups)} → {len(filtered)} setups")
        return filtered
    
    # ========================================================================
    # P0 COMMIT 2: KILL-SWITCH & CIRCUIT BREAKERS
    # ========================================================================
    
    def update_playbook_stats(self, playbook_name: str, pnl_r: float, is_win: bool):
        """
        Met à jour les stats d'un playbook et vérifie le kill-switch.
        """
        if playbook_name not in self.state.playbook_stats:
            self.state.playbook_stats[playbook_name] = PlaybookStats(playbook_name=playbook_name)
        
        stats = self.state.playbook_stats[playbook_name]
        
        # Update stats
        stats.trades += 1
        stats.total_r += pnl_r
        
        if is_win:
            stats.wins += 1
            stats.gross_profit_r += pnl_r
        else:
            stats.losses += 1
            stats.gross_loss_r += pnl_r  # pnl_r est déjà négatif
        
        # Check kill-switch
        self._check_killswitch(playbook_name)
    
    def _check_killswitch(self, playbook_name: str):
        """
        Vérifie si un playbook doit être désactivé (kill-switch).
        
        Règles:
        - Hard stop immédiat si Total_R ≤ -25R
        - Après N≥30 trades: si Total_R ≤ -10R OU PF < 0.85 → disable
        """
        if playbook_name in self.state.disabled_playbooks:
            return  # Déjà désactivé
        
        stats = self.state.playbook_stats.get(playbook_name)
        if not stats:
            return
        
        # Hard stop immédiat
        if stats.total_r <= KILLSWITCH_HARD_STOP_R:
            stats.disabled = True
            stats.disable_reason = f"HARD STOP: Total_R={stats.total_r:.2f}R ≤ {KILLSWITCH_HARD_STOP_R}R"
            self.state.disabled_playbooks.append(playbook_name)
            logger.warning(f"🛑 KILL-SWITCH HARD STOP: {playbook_name} - {stats.disable_reason}")
            return
        
        # Check après N trades
        if stats.trades >= KILLSWITCH_MIN_TRADES:
            pf = stats.profit_factor
            
            if stats.total_r <= KILLSWITCH_MAX_LOSS_R:
                stats.disabled = True
                stats.disable_reason = f"Total_R={stats.total_r:.2f}R ≤ {KILLSWITCH_MAX_LOSS_R}R (after {stats.trades} trades)"
                self.state.disabled_playbooks.append(playbook_name)
                logger.warning(f"🛑 KILL-SWITCH: {playbook_name} - {stats.disable_reason}")
            
            elif pf < KILLSWITCH_MIN_PF:
                stats.disabled = True
                stats.disable_reason = f"PF={pf:.2f} < {KILLSWITCH_MIN_PF} (after {stats.trades} trades)"
                self.state.disabled_playbooks.append(playbook_name)
                logger.warning(f"🛑 KILL-SWITCH: {playbook_name} - {stats.disable_reason}")
    
    def check_circuit_breakers(self, current_day: date) -> Dict[str, Any]:
        """
        Vérifie les circuit breakers globaux.
        
        Returns:
            Dict avec 'trading_allowed', 'stop_day', 'stop_run', 'reason'
        """
        result = {
            'trading_allowed': True,
            'stop_day': False,
            'stop_run': False,
            'cap_trades_reached': False,
            'reason': 'OK'
        }
        
        # Check stop_run (MaxDD)
        if self.state.max_drawdown_r >= CIRCUIT_STOP_RUN_DD_R:
            result['trading_allowed'] = False
            result['stop_run'] = True
            result['reason'] = f"STOP RUN: MaxDD={self.state.max_drawdown_r:.2f}R ≥ {CIRCUIT_STOP_RUN_DD_R}R"
            self.state.run_stopped = True
            logger.warning(f"🛑 {result['reason']}")
            return result
        
        # Check stop_day
        if self.state.daily_pnl_r <= CIRCUIT_STOP_DAY_R:
            result['trading_allowed'] = False
            result['stop_day'] = True
            result['reason'] = f"STOP DAY: PnL_day={self.state.daily_pnl_r:.2f}R ≤ {CIRCUIT_STOP_DAY_R}R"
            self.state.day_frozen = True
            
            # Update daily stats
            day_str = str(current_day)
            if day_str in self.state.daily_stats_history:
                self.state.daily_stats_history[day_str].stop_day_triggered = True
            
            logger.warning(f"🛑 {result['reason']}")
            return result
        
        return result
    
    def check_trades_cap(self, symbol: str, current_day: date) -> tuple[bool, str]:
        """
        Vérifie le cap de trades par jour par symbole.
        
        Returns:
            (allowed: bool, reason: str)
        """
        key = f"{current_day}_{symbol}"
        count = self.state.trades_per_day_symbol.get(key, 0)
        
        if count >= CIRCUIT_MAX_TRADES_DAY_SYMBOL:
            return False, f"Cap trades reached: {count} trades for {symbol} today"
        
        return True, "OK"
    
    def increment_trades_count(self, symbol: str, current_day: date):
        """Incrémente le compteur de trades pour un symbole/jour."""
        key = f"{current_day}_{symbol}"
        self.state.trades_per_day_symbol[key] = self.state.trades_per_day_symbol.get(key, 0) + 1
    
    # ========================================================================
    # P0 COMMIT 3: MONEY MANAGEMENT 2R/1R
    # ========================================================================
    
    def get_current_risk_tier(self) -> int:
        """Retourne le tier de risque actuel (1 ou 2)."""
        return self.state.risk_tier_state.current_tier
    
    def get_risk_dollars(self) -> float:
        """
        Retourne le risque en $ pour le prochain trade.
        risk_$ = risk_tier * base_r_unit_$
        """
        return self.get_current_risk_tier() * self.state.base_r_unit_dollars
    
    def update_risk_after_trade(
        self, 
        trade_result: str, 
        trade_pnl_dollars: float,
        trade_risk_dollars: float,
        trade_tier: int,
        playbook_name: str,
        current_day: date
    ) -> Dict[str, Any]:
        """
        Met à jour le risque et les stats après un trade.
        
        Args:
            trade_result: 'win', 'loss', 'breakeven'
            trade_pnl_dollars: P&L en $
            trade_risk_dollars: Risque utilisé en $
            trade_tier: Tier utilisé (1 ou 2)
            playbook_name: Nom du playbook
            current_day: Date du trade
        
        Returns:
            Dict avec metrics calculées
        """
        # Calculer les métriques
        base_r = self.state.base_r_unit_dollars
        
        # r_multiple = pnl_$ / risk_$ (performance normalisée du setup)
        r_multiple = trade_pnl_dollars / trade_risk_dollars if trade_risk_dollars > 0 else 0.0
        
        # pnl_R_account = pnl_$ / base_r_unit_$ (impact "account")
        pnl_r_account = trade_pnl_dollars / base_r if base_r > 0 else 0.0
        
        # Update capital
        self.state.account_balance += trade_pnl_dollars
        
        # Update peak
        if self.state.account_balance > self.state.peak_balance:
            self.state.peak_balance = self.state.account_balance
        
        # Update run totals
        self.state.run_total_r += pnl_r_account
        if self.state.run_total_r > self.state.run_peak_r:
            self.state.run_peak_r = self.state.run_total_r
        
        # Update drawdown
        self.state.current_drawdown_r = self.state.run_peak_r - self.state.run_total_r
        if self.state.current_drawdown_r > self.state.max_drawdown_r:
            self.state.max_drawdown_r = self.state.current_drawdown_r
        
        # Update daily stats
        self.state.daily_pnl_dollars += trade_pnl_dollars
        self.state.daily_pnl_r += pnl_r_account
        
        day_str = str(current_day)
        if day_str not in self.state.daily_stats_history:
            self.state.daily_stats_history[day_str] = DailyStats(date=day_str)
        daily = self.state.daily_stats_history[day_str]
        daily.pnl_r += pnl_r_account
        daily.nb_trades += 1
        daily.playbook_breakdown[playbook_name] = daily.playbook_breakdown.get(playbook_name, 0.0) + pnl_r_account
        
        # Update 2R/1R state machine
        is_win = trade_result == 'win'
        new_tier = self.state.risk_tier_state.on_trade_closed(r_multiple, trade_tier)
        
        # Update playbook stats (pour kill-switch)
        self.update_playbook_stats(playbook_name, pnl_r_account, is_win)
        
        # Update streaks
        if is_win:
            self.state.current_win_streak += 1
            self.state.current_loss_streak = 0
            self.state.consecutive_losses_today = 0
        elif trade_result == 'loss':
            self.state.current_loss_streak += 1
            self.state.current_win_streak = 0
            self.state.consecutive_losses_today += 1
        
        self.state.last_trade_result = trade_result
        
        # Log
        logger.info(
            f"Trade closed: {playbook_name} | {trade_result.upper()} | "
            f"pnl=${trade_pnl_dollars:+.2f} | r_mult={r_multiple:+.2f} | "
            f"pnl_R={pnl_r_account:+.2f} | tier {trade_tier}→{new_tier} | "
            f"run_total={self.state.run_total_r:+.2f}R | DD={self.state.current_drawdown_r:.2f}R"
        )
        
        return {
            'r_multiple': r_multiple,
            'pnl_r_account': pnl_r_account,
            'new_tier': new_tier,
            'run_total_r': self.state.run_total_r,
            'max_drawdown_r': self.state.max_drawdown_r,
        }
    
    # ========================================================================
    # MÉTHODES LEGACY (maintenues pour compatibilité)
    # ========================================================================
    
    def check_daily_limits(self) -> Dict[str, Any]:
        """
        Vérifie toutes les limites quotidiennes (legacy + circuit breakers).
        """
        # Reset si nouveau jour
        if datetime.now().date() != self.state.today_date:
            self.reset_daily_counters()
        
        # Check circuit breakers
        cb_result = self.check_circuit_breakers(self.state.today_date)
        if not cb_result['trading_allowed']:
            return {
                'trading_allowed': False,
                'reason': cb_result['reason'],
                'limits_status': {'circuit_breaker': True}
            }
        
        limits_status = {}
        reasons = []
        
        # Pertes consécutives (mode SAFE uniquement)
        if self.state.trading_mode == 'SAFE' and self.state.consecutive_losses_today >= 3:
            self.state.trading_allowed = False
            self.state.day_frozen = True
            self.state.freeze_reason = "3 consecutive losses today"
            reasons.append(self.state.freeze_reason)
            limits_status['consecutive_losses'] = True
        
        # Nombre de trades/jour global
        max_total = 4 if self.state.trading_mode == 'SAFE' else 50
        if self.state.daily_trade_count >= max_total:
            if self.state.trading_mode == 'SAFE':
                self.state.trading_allowed = False
                self.state.freeze_reason = f"Max total trades/day ({max_total})"
                reasons.append(self.state.freeze_reason)
            limits_status['total_trades_max'] = True
        
        return {
            'trading_allowed': self.state.trading_allowed,
            'reason': '; '.join(reasons) if reasons else 'OK',
            'limits_status': limits_status
        }
    
    def reset_daily_counters(self):
        """Reset compteurs à minuit."""
        logger.info("Resetting daily counters (new day)")
        
        self.state.today_date = datetime.now().date()
        self.state.daily_trade_count = 0
        self.state.daily_daily_count = 0
        self.state.daily_scalp_count = 0
        self.state.daily_aplus_daily_count = 0
        self.state.daily_aplus_scalp_count = 0
        self.state.daily_pnl_dollars = 0.0
        self.state.daily_pnl_pct = 0.0
        self.state.daily_pnl_r = 0.0
        self.state.consecutive_losses_today = 0
        self.state.trading_allowed = True
        self.state.day_frozen = False
        self.state.freeze_reason = ''
        self.state.trades_per_day_symbol = {}
    
    def can_take_setup(self, setup: Setup, playbook_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Vérifie si un setup peut être pris (limites + playbook auth + circuit breakers).
        """
        # 1) Vérifier circuit breakers
        cb_result = self.check_circuit_breakers(self.state.today_date)
        if not cb_result['trading_allowed']:
            return {'allowed': False, 'reason': cb_result['reason']}
        
        # 2) Vérifier les limites journalières
        limits = self.check_daily_limits()
        if not limits['trading_allowed']:
            return {'allowed': False, 'reason': limits['reason']}
        
        # 3) Vérifier cap trades par symbole
        allowed, reason = self.check_trades_cap(setup.symbol, self.state.today_date)
        if not allowed:
            return {'allowed': False, 'reason': reason}
        
        # 4) Vérifier authorization playbook
        if setup.playbook_matches:
            for pb_match in setup.playbook_matches:
                allowed, reason = self.is_playbook_allowed(pb_match.playbook_name)
                if not allowed:
                    return {'allowed': False, 'reason': reason}
        
        # 5) Règle A+ quota (1 Day A+ et 1 Scalp A+ max / jour)
        meta = playbook_meta or {}
        grade = meta.get('grade') or getattr(setup, 'quality', None)
        category = meta.get('category')
        
        if grade == 'APLUS' or category == 'A_PLUS_ONLY':
            if setup.trade_type == 'DAILY' and self.state.daily_aplus_daily_count >= 1:
                return {'allowed': False, 'reason': 'A+ DAILY quota reached for today'}
            if setup.trade_type == 'SCALP' and self.state.daily_aplus_scalp_count >= 1:
                return {'allowed': False, 'reason': 'A+ SCALP quota reached for today'}
        
        return {'allowed': True, 'reason': 'OK'}
    
    def _get_max_capital_factor(self, trading_mode: str, setup_quality: str) -> float:
        """Définit le levier max autorisé."""
        if trading_mode == 'SAFE':
            return 0.95
        if setup_quality == 'B':
            return 1.0
        if setup_quality == 'A':
            return 1.5
        if setup_quality == 'A+':
            return 2.0
        return 1.0
    
    def calculate_position_size(self, setup: Setup, risk_pct: float = None) -> PositionSizingResult:
        """
        Calcule la taille de position avec 2R/1R.
        """
        # Utiliser le tier actuel pour déterminer le risque
        tier = self.get_current_risk_tier()
        risk_dollars = self.get_risk_dollars()
        
        # Distance stop
        if setup.direction == 'LONG':
            distance_stop = setup.entry_price - setup.stop_loss
        else:
            distance_stop = setup.stop_loss - setup.entry_price
        
        if distance_stop <= 0:
            return PositionSizingResult(valid=False, reason='Invalid stop distance')
        
        # Calcul pour ETF
        if setup.symbol in ['SPY', 'QQQ']:
            position_size = risk_dollars / distance_stop
            position_size = int(position_size)
            
            if position_size < 1:
                return PositionSizingResult(valid=False, reason='Position size < 1 share')
            
            required_capital = position_size * setup.entry_price
            factor = self._get_max_capital_factor(self.state.trading_mode, setup.quality)
            max_capital = self.state.account_balance * factor
            
            if required_capital > max_capital:
                position_size = int(max_capital / setup.entry_price)
                if position_size < 1:
                    return PositionSizingResult(valid=False, reason='Position size < 1 share after cap')
                required_capital = position_size * setup.entry_price
            
            return PositionSizingResult(
                valid=True,
                position_size=position_size,
                position_type='shares',
                risk_amount=risk_dollars,
                risk_tier=tier,
                required_capital=required_capital,
                distance_stop=distance_stop
            )
        
        return PositionSizingResult(valid=False, reason='Unknown symbol type')
    
    # ========================================================================
    # INSTRUMENTATION (export stats)
    # ========================================================================
    
    def get_run_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du run pour export."""
        return {
            'run_total_r': self.state.run_total_r,
            'run_peak_r': self.state.run_peak_r,
            'max_drawdown_r': self.state.max_drawdown_r,
            'current_drawdown_r': self.state.current_drawdown_r,
            'final_balance': self.state.account_balance,
            'initial_capital': self.state.initial_capital,
            'trading_mode': self.state.trading_mode,
            'run_stopped': self.state.run_stopped,
            'disabled_playbooks': self.state.disabled_playbooks,
        }
    
    def get_playbook_stats(self) -> Dict[str, Dict[str, Any]]:
        """Retourne les statistiques par playbook pour export."""
        result = {}
        for name, stats in self.state.playbook_stats.items():
            result[name] = {
                'trades': stats.trades,
                'wins': stats.wins,
                'losses': stats.losses,
                'winrate': (stats.wins / stats.trades * 100) if stats.trades > 0 else 0,
                'total_r': stats.total_r,
                'profit_factor': stats.profit_factor,
                'disabled': stats.disabled,
                'disable_reason': stats.disable_reason,
            }
        return result
    
    def get_daily_stats(self) -> Dict[str, Dict[str, Any]]:
        """Retourne les statistiques journalières pour export."""
        result = {}
        for day_str, daily in self.state.daily_stats_history.items():
            result[day_str] = {
                'date': daily.date,
                'pnl_r': daily.pnl_r,
                'nb_trades': daily.nb_trades,
                'nb_setups_raw': daily.nb_setups_raw,
                'nb_setups_passed': daily.nb_setups_passed,
                'stop_day_triggered': daily.stop_day_triggered,
                'playbook_breakdown': daily.playbook_breakdown,
            }
        return result
    
    def update_daily_setup_counts(self, current_day: date, raw_count: int, passed_count: int):
        """Met à jour les compteurs de setups pour le jour."""
        day_str = str(current_day)
        if day_str not in self.state.daily_stats_history:
            self.state.daily_stats_history[day_str] = DailyStats(date=day_str)
        daily = self.state.daily_stats_history[day_str]
        daily.nb_setups_raw += raw_count
        daily.nb_setups_passed += passed_count
    
    # ========================================================================
    # CALLBACKS POUR ExecutionEngine (compatibilité paper_trading)
    # ========================================================================
    
    def on_trade_opened(self, trade):
        """Callback appelé quand un trade est ouvert (par ExecutionEngine)."""
        # Incrémenter les compteurs journaliers
        self.state.daily_trade_count += 1
        
        if getattr(trade, 'trade_type', 'DAILY') == 'DAILY':
            self.state.daily_daily_count += 1
        else:
            self.state.daily_scalp_count += 1
        
        # Check if A+ trade
        playbook = getattr(trade, 'playbook', '')
        if 'Aplus' in playbook:
            if getattr(trade, 'trade_type', 'DAILY') == 'DAILY':
                self.state.daily_aplus_daily_count += 1
            else:
                self.state.daily_aplus_scalp_count += 1
        
        self.state.open_positions_count += 1
        logger.debug(f"Trade opened: {trade.symbol} - daily_count={self.state.daily_trade_count}")
    
    def on_trade_closed(self, trade):
        """
        Callback appelé quand un trade est fermé (par ExecutionEngine).
        NOTE: L'update principal du risk state est fait dans _ingest_closed_trades du backtest.
        Ce callback gère uniquement les compteurs de positions.
        """
        self.state.open_positions_count = max(0, self.state.open_positions_count - 1)
        logger.debug(f"Trade closed callback: {trade.symbol} - open_positions={self.state.open_positions_count}")
