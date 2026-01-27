"""Execution Engine - Paper Trading"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from models.trade import Trade, Position
from models.setup import Setup
from engines.risk_engine import RiskEngine

logger = logging.getLogger(__name__)

class ExecutionEngine:
    """Moteur d'exécution des trades (Paper Trading)"""
    
    def __init__(self, risk_engine: RiskEngine):
        self.risk_engine = risk_engine
        self.open_trades = {}  # {trade_id: Trade}
        self.closed_trades = []
        self.slippage_ticks = 0.02  # $0.02
        
        logger.info("ExecutionEngine initialized (Paper Trading mode)")
    
    def place_order(self, setup: Setup, risk_allocation: Dict[str, Any], current_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Place un ordre de trade (paper trading)
        
        Args:
            setup: Setup validé
            risk_allocation: {'risk_pct': float, 'position_calc': PositionSizingResult}
        
        Returns:
            {'success': bool, 'trade_id': str, 'trade': Trade} ou {'success': False, 'reason': str}
        """
        # 1. Vérifier limites
        limits_check = self.risk_engine.check_daily_limits()
        if not limits_check['trading_allowed']:
            logger.info(f"⚠️ Order refused by daily limits: {limits_check['reason']}")
            return {'success': False, 'reason': limits_check['reason']}
        
        # 2. Position size
        position_calc = risk_allocation.get('position_calc')
        if not position_calc or not position_calc.valid:
            return {'success': False, 'reason': position_calc.reason if position_calc else 'No position calc'}
        
        # P0 FIX: Ne PAS appliquer slippage ici (éviter double comptage)
        # Le slippage sera appliqué uniquement dans calculate_total_execution_costs
        # entry_price contient le prix idéal (sans slippage)
        
        # 4. Créer Trade (utiliser current_time du backtest si fourni)
        now_ts = current_time or datetime.now()
        
        # P0 CRITICAL: Vérifier que setup.quality est défini et valide AVANT création du trade
        if not setup.quality or not setup.quality.strip() or setup.quality.upper() == "UNKNOWN":
            error_msg = f"GRADE_NOT_COMPUTED: Setup {setup.id} has no valid quality (got: {setup.quality}). Cannot create trade."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Valider que le grade est dans la liste autorisée
        valid_grades = {'A+', 'A', 'B', 'C'}
        if setup.quality.upper() not in valid_grades and setup.quality not in valid_grades:
            error_msg = f"GRADE_NOT_COMPUTED: Invalid quality '{setup.quality}' for setup {setup.id}. Must be one of {valid_grades}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        trade_quality = setup.quality
        
        trade = Trade(
            date=now_ts.date(),
            time_entry=now_ts,
            symbol=setup.symbol,
            direction=setup.direction,
            
            # Contexte
            bias_htf=setup.market_bias,
            session_profile=0,  # TODO: get from market_state
            session=setup.session,
            market_conditions=setup.notes,
            
            # Setup
            playbook=setup.playbook_matches[0].playbook_name if setup.playbook_matches else 'None',
            setup_quality=trade_quality,  # TASK 2: Utiliser trade_quality (pas setup.quality directement)
            setup_score=setup.final_score,
            trade_type=setup.trade_type,
            
            # P0: Propagation grading debug info (depuis Setup)
            match_score_setup = getattr(setup, 'match_score', None)
            match_grade_setup = getattr(setup, 'match_grade', None)
            grade_thresholds_setup = getattr(setup, 'grade_thresholds', None)
            score_scale_hint_setup = getattr(setup, 'score_scale_hint', None)
            
            # P0: Trace de propagation - log si valeurs None (pour les 3 premiers trades)
            if not hasattr(self, '_grading_trace_count'):
                self._grading_trace_count = 0
            if self._grading_trace_count < 3:
                logger.warning(f"[GRADING TRACE] Trade {setup.id}: setup.match_score={match_score_setup}, setup.match_grade={match_grade_setup}, setup.grade_thresholds={'present' if grade_thresholds_setup else 'None'}")
                self._grading_trace_count += 1
            
            match_score=match_score_setup,
            match_grade=match_grade_setup,
            grade_thresholds=grade_thresholds_setup,
            score_scale_hint=score_scale_hint_setup,
            
            # Confluences
            confluences={
                'sweep': any(p.pattern_type == 'sweep' for p in setup.ict_patterns) if setup.ict_patterns else False,
                'bos': any(p.pattern_type == 'bos' for p in setup.ict_patterns) if setup.ict_patterns else False,
                'fvg': any(p.pattern_type == 'fvg' for p in setup.ict_patterns) if setup.ict_patterns else False,
                'pattern': len(setup.candlestick_patterns) > 0 if setup.candlestick_patterns else False,
                'smt': any(p.pattern_type == 'smt' for p in setup.ict_patterns) if setup.ict_patterns else False,
                'htf_alignment': setup.direction == ('LONG' if setup.market_bias == 'bullish' else 'SHORT')
            },
            
            # Exécution (prix idéal, slippage appliqué dans calculate_total_execution_costs)
            entry_price=setup.entry_price,
            stop_loss=setup.stop_loss,
            take_profit_1=setup.take_profit_1,
            take_profit_2=setup.take_profit_2,
            position_size=position_calc.position_size,
            risk_amount=position_calc.risk_amount,
            risk_pct=risk_allocation['risk_pct'],
            
            # Résultat (initial)
            pnl_dollars=0.0,
            pnl_pct=0.0,
            r_multiple=0.0,
            outcome='pending',
            exit_reason='',
            exit_price=0.0
        )
        
        # 5. Enregistrer
        self.open_trades[trade.id] = trade
        
        # 6. Notifier Risk Engine
        self.risk_engine.on_trade_opened(trade)
        
        logger.info(f"Trade opened: {trade.symbol} {trade.direction} @ {setup.entry_price:.2f}, "
                   f"size={position_calc.position_size}, risk={risk_allocation['risk_pct']*100:.1f}%")
        
        return {
            'success': True,
            'trade_id': trade.id,
            'trade': trade
        }
    
    def _apply_slippage(self, ideal_price: float, direction: str) -> float:
        """Simule slippage réaliste"""
        if direction == 'LONG':
            return ideal_price + self.slippage_ticks
        else:
            return ideal_price - self.slippage_ticks
    
    def update_open_trades(self, market_data: Dict[str, float], current_time: Optional[datetime] = None) -> List[Dict]:
        """
        Met à jour toutes les positions avec nouveaux prix
        
        Args:
            market_data: {symbol: current_price}
            current_time: Timestamp actuel (pour calculer duration_minutes)
        
        Returns:
            Liste d'events: {'trade_id', 'event_type', 'details'}
        """
        events = []
        trades_to_close = []
        
        for trade_id, trade in list(self.open_trades.items()):
            if trade.symbol not in market_data:
                continue
            
            current_price = market_data[trade.symbol]
            
            # Calculer P&L unrealized
            if trade.direction == 'LONG':
                pnl_points = current_price - trade.entry_price
            else:
                pnl_points = trade.entry_price - current_price
            
            # pnl_dollars = pnl_points * trade.position_size  # Unused in update logic
            risk_distance = abs(trade.entry_price - trade.stop_loss)
            r_multiple = pnl_points / risk_distance if risk_distance > 0 else 0
            
            # 1. Vérifier Stop Loss
            if trade.direction == 'LONG' and current_price <= trade.stop_loss:
                trades_to_close.append({
                    'trade_id': trade_id,
                    'reason': 'SL',
                    'close_price': trade.stop_loss
                })
                events.append({
                    'trade_id': trade_id,
                    'event_type': 'SL_HIT',
                    'r_multiple': r_multiple
                })
                continue
            
            elif trade.direction == 'SHORT' and current_price >= trade.stop_loss:
                trades_to_close.append({
                    'trade_id': trade_id,
                    'reason': 'SL',
                    'close_price': trade.stop_loss
                })
                events.append({
                    'trade_id': trade_id,
                    'event_type': 'SL_HIT',
                    'r_multiple': r_multiple
                })
                continue
            
            # 2. Vérifier Take Profit (priorité TP2 > TP1, une seule close par tick)
            # BUGFIX: Si TP2 et TP1 tous deux hit, on close TP2 uniquement (le plus profitable)
            tp1_hit = False
            tp2_hit = False
            
            if trade.take_profit_2:
                if trade.direction == 'LONG' and current_price >= trade.take_profit_2:
                    tp2_hit = True
                elif trade.direction == 'SHORT' and current_price <= trade.take_profit_2:
                    tp2_hit = True
            
            if not tp2_hit and trade.take_profit_1:
                if trade.direction == 'LONG' and current_price >= trade.take_profit_1:
                    tp1_hit = True
                elif trade.direction == 'SHORT' and current_price <= trade.take_profit_1:
                    tp1_hit = True
            
            # Décision : TP2 prioritaire (plus profitable), sinon TP1
            if tp2_hit:
                trades_to_close.append({
                    'trade_id': trade_id,
                    'reason': 'TP2',
                    'close_price': trade.take_profit_2
                })
                events.append({
                    'trade_id': trade_id,
                    'event_type': 'TP2_HIT',
                    'r_multiple': r_multiple
                })
                # Log si TP1 était aussi hit (debug)
                if trade.take_profit_1:
                    tp1_would_hit = (trade.direction == 'LONG' and current_price >= trade.take_profit_1) or \
                                    (trade.direction == 'SHORT' and current_price <= trade.take_profit_1)
                    if tp1_would_hit:
                        logger.debug(f"Trade {trade_id}: TP2 hit ({trade.take_profit_2:.2f}), TP1 ({trade.take_profit_1:.2f}) also hit but skipped (priority TP2)")
            elif tp1_hit:
                trades_to_close.append({
                    'trade_id': trade_id,
                    'reason': 'TP1',
                    'close_price': trade.take_profit_1
                })
                events.append({
                    'trade_id': trade_id,
                    'event_type': 'TP1_HIT',
                    'r_multiple': r_multiple
                })
            
            # 3. PATCH 3: Time-stop pour SCALP (empêcher overnight)
            if current_time and trade.trade_type == 'SCALP':
                elapsed_minutes = (current_time - trade.time_entry).total_seconds() / 60.0
                # Récupérer max_scalp_minutes depuis la config (via risk_engine si disponible)
                max_scalp_minutes = getattr(self.risk_engine, '_max_scalp_minutes', 120.0)
                if elapsed_minutes >= max_scalp_minutes:
                    trades_to_close.append({
                        'trade_id': trade_id,
                        'reason': 'time_stop',
                        'close_price': current_price  # Close au prix actuel
                    })
                    events.append({
                        'trade_id': trade_id,
                        'event_type': 'TIME_STOP',
                        'elapsed_minutes': elapsed_minutes,
                        'max_minutes': max_scalp_minutes
                    })
                    logger.info(f"Trade {trade_id}: Time-stop SCALP after {elapsed_minutes:.1f}min (max={max_scalp_minutes})")
                    continue
            
            # 4. Break-even (TJR: +0.5R)
            if hasattr(trade, 'breakeven_moved'):
                if not trade.breakeven_moved and r_multiple >= 0.5:
                    trade.stop_loss = trade.entry_price
                    trade.breakeven_moved = True
                    events.append({
                        'trade_id': trade_id,
                        'event_type': 'BREAKEVEN_MOVED',
                        'new_sl': trade.entry_price
                    })
                    logger.info(f"Trade {trade_id}: Stop moved to breakeven @ {trade.entry_price:.2f}")
        
        # Fermer trades (sécurité: dédupliquer par trade_id)
        closed_trades = set()
        for close_req in trades_to_close:
            trade_id = close_req['trade_id']
            if trade_id in closed_trades:
                logger.warning(f"Trade {trade_id} already closed this tick, skipping duplicate close")
                continue
            
            self.close_trade(
                trade_id,
                close_req['reason'],
                close_req['close_price'],
                current_time=current_time  # P0 FIX: Transmettre current_time
            )
            closed_trades.add(trade_id)
        
        return events
    
    def close_trade(self, trade_id: str, reason: str, 
                   close_price: Optional[float] = None, current_time: Optional[datetime] = None) -> Trade:
        """
        Ferme un trade et calcule résultat final
        
        Args:
            reason: 'TP1', 'TP2', 'SL', 'manual', 'eod'
            close_price: Prix de clôture (optionnel, utilise entry_price si None)
            current_time: Timestamp actuel (pour time_exit et duration_minutes)
        """
        trade = self.open_trades.get(trade_id)
        if not trade:
            raise ValueError(f"Trade {trade_id} not found")
        
        # Prix fermeture
        if close_price is None:
            close_price = trade.entry_price
        
        # P0 FIX: Calculer time_exit et duration_minutes correctement
        if current_time is not None:
            trade.time_exit = current_time
            # Calculer duration_minutes
            if trade.time_entry and trade.time_exit:
                delta = trade.time_exit - trade.time_entry
                trade.duration_minutes = delta.total_seconds() / 60.0
            else:
                trade.duration_minutes = 0.0
        else:
            # Fallback: utiliser time_entry si current_time non fourni (legacy)
            trade.time_exit = trade.time_entry
            trade.duration_minutes = 0.0
            logger.warning(f"[P0] close_trade called without current_time for trade {trade_id}, using time_entry as time_exit")
        
        # Calculer résultat
        if trade.direction == 'LONG':
            pnl_points = close_price - trade.entry_price
        else:
            pnl_points = trade.entry_price - close_price
        
        pnl_dollars = pnl_points * trade.position_size
        pnl_pct = (pnl_dollars / (trade.entry_price * trade.position_size)) * 100
        
        risk_distance = abs(trade.entry_price - trade.stop_loss)
        r_multiple = pnl_points / risk_distance if risk_distance > 0 else 0
        
        outcome = 'win' if pnl_dollars > 0 else ('loss' if pnl_dollars < 0 else 'breakeven')
        
        # Mettre à jour trade
        trade.exit_price = close_price
        trade.exit_reason = reason
        trade.pnl_dollars = pnl_dollars
        trade.pnl_pct = pnl_pct
        trade.r_multiple = r_multiple
        trade.outcome = outcome
        
        # Retirer
        del self.open_trades[trade_id]
        self.closed_trades.append(trade)
        
        # Notifier Risk Engine
        self.risk_engine.on_trade_closed(trade)
        
        logger.info(f"Trade closed: {trade.symbol} {outcome.upper()} @ {close_price:.2f}, "
                   f"P&L: ${pnl_dollars:.2f} ({r_multiple:+.2f}R)")
        
        return trade
    
    def get_open_trades(self) -> List[Trade]:
        """Retourne les trades ouverts"""
        return list(self.open_trades.values())
    
    def get_closed_trades(self) -> List[Trade]:
        """Retourne les trades fermés"""
        return self.closed_trades
