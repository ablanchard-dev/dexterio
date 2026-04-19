"""Execution Engine - Paper Trading"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from models.trade import Trade, Position
from models.setup import Setup
from engines.risk_engine import RiskEngine
from engines.playbook_loader import get_playbook_loader
from engines.execution.phase3b_execution import (
    compute_session_window_end_utc,
    is_phase3b_playbook,
    should_attach_session_window_end,
)

logger = logging.getLogger(__name__)

class ExecutionEngine:
    """Moteur d'exécution des trades (Paper Trading)"""
    
    def __init__(self, risk_engine: RiskEngine):
        self.risk_engine = risk_engine
        self.playbook_loader = get_playbook_loader()
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
        
        # P0: Propagation grading debug info (depuis Setup) - AVANT création du Trade
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
        
        playbook_name = setup.playbook_name or (
            setup.playbook_matches[0].playbook_name if setup.playbook_matches else 'None'
        )
        pb_def = self.playbook_loader.get_playbook_by_name(playbook_name)
        be_trigger_rr = None
        session_window_end_utc = None
        max_hold_minutes = None

        # Always read breakeven_at_rr from playbook YAML (not just Phase3B)
        if pb_def is not None:
            try:
                be_trigger_rr = float(pb_def.breakeven_at_rr)
            except Exception:
                be_trigger_rr = 1.0
        else:
            be_trigger_rr = 1.0

        if is_phase3b_playbook(playbook_name):
            if setup.trade_type == "DAILY":
                if pb_def is not None and should_attach_session_window_end(playbook_name, setup.trade_type):
                    session_window_end_utc = compute_session_window_end_utc(pb_def, now_ts)
            elif setup.trade_type == "SCALP":
                if pb_def is not None and getattr(pb_def, "max_duration_minutes", None) is not None:
                    try:
                        max_hold_minutes = float(pb_def.max_duration_minutes)
                    except Exception:
                        max_hold_minutes = None

        init_sl = float(setup.stop_loss)
        if playbook_name == "News_Fade":
            if abs(float(setup.entry_price) - init_sl) < 1e-9:
                raise ValueError(
                    "News_Fade: stop_loss must differ from entry_price (zero risk at open is invalid)"
                )

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
            playbook=playbook_name,
            setup_quality=trade_quality,  # TASK 2: Utiliser trade_quality (pas setup.quality directement)
            setup_score=setup.final_score,
            trade_type=setup.trade_type,
            
            # P0: Propagation grading debug info (depuis Setup)
            match_score=match_score_setup,
            match_grade=match_grade_setup,
            grade_thresholds=grade_thresholds_setup,
            score_scale_hint=score_scale_hint_setup,
            breakeven_trigger_rr=be_trigger_rr,
            trailing_mode=getattr(pb_def, 'trailing_mode', None) if pb_def else None,
            trailing_trigger_rr=getattr(pb_def, 'trailing_trigger_rr', None) if pb_def else None,
            trailing_offset_rr=getattr(pb_def, 'trailing_offset_rr', None) if pb_def else None,
            peak_r=0.0,
            mae_r=0.0,
            session_window_end_utc=session_window_end_utc,
            max_hold_minutes=max_hold_minutes,
            
            # P1: Propagation Master Candle info (Sprint 2)
            mc_high=getattr(setup, 'mc_high', None),
            mc_low=getattr(setup, 'mc_low', None),
            mc_range=getattr(setup, 'mc_range', None),
            mc_breakout_dir=getattr(setup, 'mc_breakout_dir', None),
            mc_window_minutes=getattr(setup, 'mc_window_minutes', None),
            mc_session_date=getattr(setup, 'mc_session_date', None),
            
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
            initial_stop_loss=init_sl,
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
            
            raw = market_data[trade.symbol]
            if isinstance(raw, dict):
                current_price = raw['close']
                candle_high = raw['high']
                candle_low = raw['low']
            else:
                current_price = raw
                candle_high = raw
                candle_low = raw

            # Calculer P&L unrealized
            if trade.direction == 'LONG':
                pnl_points = current_price - trade.entry_price
            else:
                pnl_points = trade.entry_price - current_price
            
            # pnl_dollars = pnl_points * trade.position_size  # Unused in update logic
            sl0 = trade.initial_stop_loss if trade.initial_stop_loss is not None else trade.stop_loss
            risk_distance = abs(trade.entry_price - sl0)
            r_multiple = pnl_points / risk_distance if risk_distance > 0 else 0

            # Track peak R for trailing stop (MFE proxy)
            if hasattr(trade, 'peak_r'):
                if trade.direction == 'LONG':
                    peak_pnl = candle_high - trade.entry_price
                else:
                    peak_pnl = trade.entry_price - candle_low
                peak_r = peak_pnl / risk_distance if risk_distance > 0 else 0
                trade.peak_r = max(trade.peak_r, peak_r)

            # Track MAE (Max Adverse Excursion) for SL calibration
            if hasattr(trade, 'mae_r'):
                if trade.direction == 'LONG':
                    adverse_pnl = candle_low - trade.entry_price
                else:
                    adverse_pnl = trade.entry_price - candle_high
                adverse_r = adverse_pnl / risk_distance if risk_distance > 0 else 0
                trade.mae_r = min(trade.mae_r, adverse_r)

            # 1. Vérifier Stop Loss (intrabar: use candle extremes)
            if trade.direction == 'LONG' and candle_low <= trade.stop_loss:
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
            
            elif trade.direction == 'SHORT' and candle_high >= trade.stop_loss:
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

            def try_take_profits() -> bool:
                """TP2 > TP1 ; retourne True si une clôture TP est programmée ce tick."""
                tp1_hit = False
                tp2_hit = False
                if trade.take_profit_2:
                    if trade.direction == 'LONG' and candle_high >= trade.take_profit_2:
                        tp2_hit = True
                    elif trade.direction == 'SHORT' and candle_low <= trade.take_profit_2:
                        tp2_hit = True
                if not tp2_hit and trade.take_profit_1:
                    if trade.direction == 'LONG' and candle_high >= trade.take_profit_1:
                        tp1_hit = True
                    elif trade.direction == 'SHORT' and candle_low <= trade.take_profit_1:
                        tp1_hit = True
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
                    if trade.take_profit_1:
                        tp1_would_hit = (trade.direction == 'LONG' and candle_high >= trade.take_profit_1) or \
                                        (trade.direction == 'SHORT' and candle_low <= trade.take_profit_1)
                        if tp1_would_hit:
                            logger.debug(
                                f"Trade {trade_id}: TP2 hit ({trade.take_profit_2:.2f}), "
                                f"TP1 ({trade.take_profit_1:.2f}) also hit but skipped (priority TP2)"
                            )
                    return True
                if tp1_hit:
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
                    return True
                return False

            # 1.b / 2 Phase 3B : News_Fade seul — TP avant session_end (NY et autres inchangés)
            if trade.playbook == "News_Fade":
                if try_take_profits():
                    continue
                if current_time and trade.trade_type == "DAILY" and trade.session_window_end_utc is not None:
                    if current_time >= trade.session_window_end_utc:
                        trades_to_close.append({
                            'trade_id': trade_id,
                            'reason': 'session_end',
                            'close_price': current_price
                        })
                        events.append({
                            'trade_id': trade_id,
                            'event_type': 'SESSION_END',
                            'session_window_end_utc': str(trade.session_window_end_utc),
                        })
                        continue
            else:
                if current_time and trade.trade_type == "DAILY" and trade.session_window_end_utc is not None:
                    if current_time >= trade.session_window_end_utc:
                        trades_to_close.append({
                            'trade_id': trade_id,
                            'reason': 'session_end',
                            'close_price': current_price
                        })
                        events.append({
                            'trade_id': trade_id,
                            'event_type': 'SESSION_END',
                            'session_window_end_utc': str(trade.session_window_end_utc),
                        })
                        continue
                if try_take_profits():
                    continue
            
            # 3. Time-stop pour SCALP (Phase 3B: max_hold_minutes playbook, sinon cap global legacy)
            if current_time and trade.trade_type == 'SCALP':
                elapsed_minutes = (current_time - trade.time_entry).total_seconds() / 60.0
                max_scalp_minutes = (
                    float(trade.max_hold_minutes)
                    if trade.max_hold_minutes is not None
                    else float(getattr(self.risk_engine, '_max_scalp_minutes', 120.0))
                )
                if elapsed_minutes >= max_scalp_minutes:
                    close_time = trade.time_entry + timedelta(minutes=max_scalp_minutes)
                    trades_to_close.append({
                        'trade_id': trade_id,
                        'reason': 'time_stop',
                        'close_price': current_price,  # Close au prix actuel
                        'close_time': close_time,
                    })
                    events.append({
                        'trade_id': trade_id,
                        'event_type': 'TIME_STOP',
                        'elapsed_minutes': elapsed_minutes,
                        'max_minutes': max_scalp_minutes
                    })
                    logger.info(f"Trade {trade_id}: Time-stop SCALP after {elapsed_minutes:.1f}min (max={max_scalp_minutes})")
                    continue
            
            # 4. Break-even (Phase 3B: seuil par playbook ; legacy: 0.5R)
            if hasattr(trade, 'breakeven_moved'):
                trigger = trade.breakeven_trigger_rr if trade.breakeven_trigger_rr is not None else 1.0
                if not trade.breakeven_moved and r_multiple >= trigger:
                    trade.stop_loss = trade.entry_price
                    trade.breakeven_moved = True
                    events.append({
                        'trade_id': trade_id,
                        'event_type': 'BREAKEVEN_MOVED',
                        'new_sl': trade.entry_price
                    })
                    logger.info(f"Trade {trade_id}: Stop moved to breakeven @ {trade.entry_price:.2f}")

            # 5. Trailing stop
            if hasattr(trade, 'trailing_mode') and trade.trailing_mode == 'trail_rr':
                trigger = trade.trailing_trigger_rr if trade.trailing_trigger_rr is not None else 1.0
                offset = trade.trailing_offset_rr if trade.trailing_offset_rr is not None else 0.5
                if trade.peak_r >= trigger:
                    trail_r = trade.peak_r - offset
                    if trail_r > 0:
                        if trade.direction == 'LONG':
                            new_sl = trade.entry_price + trail_r * risk_distance
                        else:
                            new_sl = trade.entry_price - trail_r * risk_distance
                        if trade.direction == 'LONG' and new_sl > trade.stop_loss:
                            trade.stop_loss = new_sl
                        elif trade.direction == 'SHORT' and new_sl < trade.stop_loss:
                            trade.stop_loss = new_sl

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
                current_time=close_req.get('close_time') or current_time  # P0 FIX: Transmettre current_time
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
        
        sl0 = trade.initial_stop_loss if trade.initial_stop_loss is not None else trade.stop_loss
        risk_distance = abs(trade.entry_price - sl0)
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
