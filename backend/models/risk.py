"""Modèles Risk Engine - P0 Guardrails + 2R/1R Money Management"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import date, datetime


class TwoTierRiskState(BaseModel):
    """
    Machine d'état 2R/1R pour Money Management.
    
    Règles:
    - Start: 2R
    - Win à 2R → reste 2R
    - Loss à 2R → passe à 1R
    - Loss à 1R → reste 1R
    - Win à 1R → remonte 2R
    - BE (0R) = neutre (ne change pas le tier)
    """
    current_tier: int = 2  # 1 ou 2
    
    def on_trade_closed(self, r_multiple: float, trade_tier: int) -> int:
        """
        Met à jour le tier après clôture d'un trade.
        
        Args:
            r_multiple: Performance normalisée du setup (pnl_$ / risk_$)
            trade_tier: Tier utilisé pour ce trade (1 ou 2)
        
        Returns:
            Nouveau tier (1 ou 2)
        """
        # BE = neutre
        if r_multiple == 0:
            return self.current_tier
        
        is_win = r_multiple > 0
        is_loss = r_multiple < 0
        
        if trade_tier == 2 and is_loss:
            self.current_tier = 1
        elif trade_tier == 1 and is_win:
            self.current_tier = 2
        # sinon: rester dans l'état actuel
        
        return self.current_tier


class PlaybookStats(BaseModel):
    """Statistiques runtime d'un playbook pour kill-switch."""
    playbook_name: str
    trades: int = 0
    wins: int = 0
    losses: int = 0
    total_r: float = 0.0
    gross_profit_r: float = 0.0
    gross_loss_r: float = 0.0
    disabled: bool = False
    disable_reason: str = ''
    
    @property
    def profit_factor(self) -> float:
        """PF = gross_profit / |gross_loss|"""
        if self.gross_loss_r == 0:
            return float('inf') if self.gross_profit_r > 0 else 0.0
        return self.gross_profit_r / abs(self.gross_loss_r)


class DailyStats(BaseModel):
    """Statistiques d'un jour pour instrumentation."""
    date: str
    pnl_r: float = 0.0
    nb_trades: int = 0
    nb_setups_raw: int = 0
    nb_setups_passed: int = 0
    stop_day_triggered: bool = False
    playbook_breakdown: Dict[str, float] = Field(default_factory=dict)


class RiskEngineState(BaseModel):
    """État du Risk Engine (capital, risque, compteurs)"""
    
    # Capital
    account_balance: float
    initial_capital: float
    peak_balance: float
    
    # Risque dynamique - LEGACY (maintenu pour compatibilité)
    current_risk_pct: float = 0.02  # 2% par défaut
    base_risk_pct: float = 0.02
    reduced_risk_pct: float = 0.01
    
    # Money Management 2R/1R (P0)
    risk_tier_state: TwoTierRiskState = Field(default_factory=TwoTierRiskState)
    base_r_unit_dollars: float = 0.0  # Valeur $ d'1R (calculée à l'init)
    
    # Compteurs journaliers
    today_date: date = Field(default_factory=lambda: datetime.now().date())
    daily_trade_count: int = 0
    daily_daily_count: int = 0
    daily_scalp_count: int = 0

    # Compteurs A+ par jour
    daily_aplus_daily_count: int = 0
    daily_aplus_scalp_count: int = 0
    
    # Résultats journaliers
    daily_pnl_dollars: float = 0.0
    daily_pnl_pct: float = 0.0
    daily_pnl_r: float = 0.0
    
    # Streaks
    last_trade_result: str = 'none'  # 'win', 'loss', 'none'
    current_win_streak: int = 0
    current_loss_streak: int = 0
    consecutive_losses_today: int = 0
    
    # Mode
    trading_mode: str = 'SAFE'
    
    # État
    trading_allowed: bool = True
    day_frozen: bool = False
    freeze_reason: str = ''
    run_stopped: bool = False  # P0: stop_run circuit breaker
    
    # Positions
    open_positions_count: int = 0
    open_positions: List[str] = []
    
    # P0: Kill-switch stats par playbook
    playbook_stats: Dict[str, PlaybookStats] = Field(default_factory=dict)
    disabled_playbooks: List[str] = Field(default_factory=list)
    
    # P0: Daily stats pour instrumentation
    daily_stats_history: Dict[str, DailyStats] = Field(default_factory=dict)
    
    # P0: MaxDD tracking
    max_drawdown_r: float = 0.0
    current_drawdown_r: float = 0.0
    run_peak_r: float = 0.0
    run_total_r: float = 0.0
    
    # P0: Trades per day per symbol
    trades_per_day_symbol: Dict[str, int] = Field(default_factory=dict)
    
    # P0: Anti-spam tracking
    last_trade_time: Dict[tuple, datetime] = Field(default_factory=dict)  # (symbol, playbook) -> last_trade_time
    trades_per_session: Dict[tuple, int] = Field(default_factory=dict)   # (symbol, playbook, session) -> count


class PositionSizingResult(BaseModel):
    """Résultat du calcul de position sizing"""
    valid: bool
    reason: str = ''
    position_size: float = 0.0
    position_type: str = ''  # 'shares' or 'contracts'
    risk_amount: float = 0.0
    risk_tier: int = 2  # P0: Tier utilisé (1 ou 2)
    required_capital: float = 0.0
    distance_stop: float = 0.0
    multiplier: float = 1.0
