"""Playbook Engine - NY Open, London Sweep, Continuation, ICT Manipulation"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from models.market_data import MarketState
from models.setup import PlaybookMatch, ICTPattern
from engines.liquidity import LiquidityEngine
from utils.timeframes import get_session_info, is_in_kill_zone

logger = logging.getLogger(__name__)

class NYOpenReversalPlaybook:
    """Playbook NY Open Reversal (Fake Breakout)"""
    
    name = "NY_Open_Reversal"
    description = "Faux départ ouverture NY puis inversion"
    
    @staticmethod
    def check_conditions(market_state: MarketState,
                        liquidity_engine: LiquidityEngine,
                        ict_patterns: List[ICTPattern],
                        current_time: datetime) -> Optional[PlaybookMatch]:
        """Vérifie conditions du playbook"""
        
        conditions_met = {}
        
        # 1. Range Asie défini
        conditions_met['asia_range_defined'] = (
            market_state.asia_high is not None and
            market_state.asia_low is not None
        )
        
        # 2. Session NY
        session_info = get_session_info(current_time)
        conditions_met['correct_session'] = session_info.get('name') == 'ny'
        
        # 3. Kill zone NY morning
        kz_info = is_in_kill_zone(current_time)
        conditions_met['in_kill_zone'] = (
            kz_info.get('in_kill_zone', False) and
            'Morning' in kz_info.get('zone_name', '')
        )
        
        # 4. Sweep détecté (récent = 30 min)
        swept_levels = liquidity_engine.get_swept_levels(market_state.symbol)
        recent_sweeps = [
            s for s in swept_levels
            if (current_time - s.sweep_timestamp).total_seconds() < 1800
        ]
        conditions_met['sweep_detected'] = len(recent_sweeps) > 0
        
        # 5. BOS opposé au sweep
        bos_patterns = [p for p in ict_patterns if p.pattern_type == 'bos']
        conditions_met['bos_opposite_sweep'] = False
        
        if recent_sweeps and bos_patterns:
            last_sweep = recent_sweeps[-1]
            last_bos = bos_patterns[-1]
            
            # Sweep high → BOS bearish
            if 'high' in last_sweep.level_type and last_bos.direction == 'bearish':
                conditions_met['bos_opposite_sweep'] = True
            # Sweep low → BOS bullish
            elif 'low' in last_sweep.level_type and last_bos.direction == 'bullish':
                conditions_met['bos_opposite_sweep'] = True
        
        # 6. Alignement biais HTF
        if bos_patterns:
            conditions_met['htf_alignment'] = bos_patterns[-1].direction == market_state.bias
        else:
            conditions_met['htf_alignment'] = False
        
        # Total
        total_conditions = len(conditions_met)
        met_count = sum(1 for v in conditions_met.values() if v)
        
        # Minimum 4/6 pour valider
        if met_count < 4:
            return None
        
        # Direction
        direction = bos_patterns[-1].direction if bos_patterns else 'unknown'
        if direction == 'unknown':
            return None
        
        # Suggestions niveaux
        if recent_sweeps:
            sweep_details = recent_sweeps[-1].sweep_details
            if direction == 'bearish':
                entry_suggestion = sweep_details['candle'].high * 0.998
                stop_loss_suggestion = sweep_details['candle'].high * 1.001
                take_profit_suggestion = market_state.asia_low or market_state.pdl
            else:  # bullish
                entry_suggestion = sweep_details['candle'].low * 1.002
                stop_loss_suggestion = sweep_details['candle'].low * 0.999
                take_profit_suggestion = market_state.asia_high or market_state.pdh
        else:
            entry_suggestion = None
            stop_loss_suggestion = None
            take_profit_suggestion = None
        
        logger.info(f"NY Open Reversal playbook matched: {met_count}/{total_conditions} conditions")
        
        return PlaybookMatch(
            symbol=market_state.symbol,
            playbook_name=NYOpenReversalPlaybook.name,
            playbook_description=NYOpenReversalPlaybook.description,
            conditions_total=total_conditions,
            conditions_met=met_count,
            conditions_details=conditions_met,
            match_score=met_count / total_conditions,
            direction='LONG' if direction == 'bullish' else 'SHORT',
            entry_suggestion=entry_suggestion,
            stop_loss_suggestion=stop_loss_suggestion,
            take_profit_suggestion=take_profit_suggestion
        )


class LondonSweepPlaybook:
    """Playbook London Sweep / Fake Breakout"""
    
    name = "London_Sweep"
    description = "Fake breakout session Londres puis reversal"
    
    @staticmethod
    def check_conditions(market_state: MarketState,
                        liquidity_engine: LiquidityEngine,
                        ict_patterns: List[ICTPattern],
                        current_time: datetime) -> Optional[PlaybookMatch]:
        """Vérifie conditions"""
        
        conditions_met = {}
        
        # 1. Range Asie défini
        conditions_met['asia_range_defined'] = (
            market_state.asia_high is not None and
            market_state.asia_low is not None
        )
        
        # 2. Session Londres ou début NY
        session_info = get_session_info(current_time)
        conditions_met['correct_session'] = session_info.get('name') in ['london', 'ny']
        
        # 3. Sweep du range Asie
        swept_levels = liquidity_engine.get_swept_levels(market_state.symbol)
        asia_swept = any(
            'asia' in s.level_type for s in swept_levels
            if (current_time - s.sweep_timestamp).total_seconds() < 3600  # 1h
        )
        conditions_met['asia_sweep_detected'] = asia_swept
        
        # 4. BOS opposé
        bos_patterns = [p for p in ict_patterns if p.pattern_type == 'bos']
        conditions_met['bos_detected'] = len(bos_patterns) > 0
        
        # 5. FVG créé
        fvg_patterns = [p for p in ict_patterns if p.pattern_type == 'fvg']
        conditions_met['fvg_present'] = len(fvg_patterns) > 0
        
        total_conditions = len(conditions_met)
        met_count = sum(1 for v in conditions_met.values() if v)
        
        # Minimum 3/5
        if met_count < 3:
            return None
        
        direction = bos_patterns[-1].direction if bos_patterns else 'unknown'
        if direction == 'unknown':
            return None
        
        logger.info(f"London Sweep playbook matched: {met_count}/{total_conditions}")
        
        return PlaybookMatch(
            symbol=market_state.symbol,
            playbook_name=LondonSweepPlaybook.name,
            playbook_description=LondonSweepPlaybook.description,
            conditions_total=total_conditions,
            conditions_met=met_count,
            conditions_details=conditions_met,
            match_score=met_count / total_conditions,
            direction='LONG' if direction == 'bullish' else 'SHORT'
        )


class TrendContinuationPlaybook:
    """Playbook Continuation de Tendance sur Pullback"""
    
    name = "Trend_Continuation_Pullback"
    description = "Rejoindre tendance établie sur correction"
    
    @staticmethod
    def check_conditions(market_state: MarketState,
                        liquidity_engine: LiquidityEngine,
                        ict_patterns: List[ICTPattern],
                        current_time: datetime) -> Optional[PlaybookMatch]:
        """Vérifie conditions"""
        
        conditions_met = {}
        
        # 1. Biais HTF clair
        conditions_met['htf_bias_clear'] = (
            market_state.bias in ['bullish', 'bearish'] and
            market_state.bias_confidence > 0.6
        )
        
        # 2. Structure confirmée
        conditions_met['structure_confirmed'] = (
            market_state.daily_structure in ['uptrend', 'downtrend']
        )
        
        # 3. FVG présent (zone de pullback)
        fvg_patterns = [p for p in ict_patterns if p.pattern_type == 'fvg']
        conditions_met['fvg_pullback_zone'] = len(fvg_patterns) > 0
        
        # 4. BOS dans sens du biais
        bos_patterns = [p for p in ict_patterns if p.pattern_type == 'bos']
        if bos_patterns:
            conditions_met['bos_aligned'] = bos_patterns[-1].direction == market_state.bias
        else:
            conditions_met['bos_aligned'] = False
        
        total_conditions = len(conditions_met)
        met_count = sum(1 for v in conditions_met.values() if v)
        
        # Minimum 3/4
        if met_count < 3:
            return None
        
        direction = market_state.bias
        
        logger.info(f"Trend Continuation playbook matched: {met_count}/{total_conditions}")
        
        return PlaybookMatch(
            symbol=market_state.symbol,
            playbook_name=TrendContinuationPlaybook.name,
            playbook_description=TrendContinuationPlaybook.description,
            conditions_total=total_conditions,
            conditions_met=met_count,
            conditions_details=conditions_met,
            match_score=met_count / total_conditions,
            direction='LONG' if direction == 'bullish' else 'SHORT'
        )


class ICTManipulationReversalPlaybook:
    """Playbook ICT Manipulation + Reversal"""
    
    name = "ICT_Manipulation_Reversal"
    description = "Sweep de liquidité + BOS opposé"
    
    @staticmethod
    def check_conditions(market_state: MarketState,
                        liquidity_engine: LiquidityEngine,
                        ict_patterns: List[ICTPattern],
                        current_time: datetime) -> Optional[PlaybookMatch]:
        """Vérifie conditions"""
        
        conditions_met = {}
        
        # 1. Niveau liquidité identifié et sweeped
        swept_levels = liquidity_engine.get_swept_levels(market_state.symbol)
        recent_sweeps = [
            s for s in swept_levels
            if (current_time - s.sweep_timestamp).total_seconds() < 1800  # 30min
        ]
        conditions_met['liquidity_swept'] = len(recent_sweeps) > 0
        
        # 2. BOS opposé
        bos_patterns = [p for p in ict_patterns if p.pattern_type == 'bos']
        conditions_met['bos_opposite'] = False
        
        if recent_sweeps and bos_patterns:
            last_sweep = recent_sweeps[-1]
            last_bos = bos_patterns[-1]
            
            if 'high' in last_sweep.level_type and last_bos.direction == 'bearish':
                conditions_met['bos_opposite'] = True
            elif 'low' in last_sweep.level_type and last_bos.direction == 'bullish':
                conditions_met['bos_opposite'] = True
        
        # 3. FVG créé
        fvg_patterns = [p for p in ict_patterns if p.pattern_type == 'fvg']
        conditions_met['fvg_created'] = len(fvg_patterns) > 0
        
        # 4. SMT favorable (optionnel)
        smt_patterns = [p for p in ict_patterns if p.pattern_type == 'smt']
        conditions_met['smt_favorable'] = len(smt_patterns) > 0
        
        # 5. Alignement HTF
        if bos_patterns:
            conditions_met['htf_aligned'] = bos_patterns[-1].direction == market_state.bias
        else:
            conditions_met['htf_aligned'] = False
        
        # 6. Kill zone
        kz_info = is_in_kill_zone(current_time)
        conditions_met['in_kill_zone'] = kz_info.get('in_kill_zone', False)
        
        total_conditions = len(conditions_met)
        met_count = sum(1 for v in conditions_met.values() if v)
        
        # Minimum 4/6
        if met_count < 4:
            return None
        
        direction = bos_patterns[-1].direction if bos_patterns else 'unknown'
        if direction == 'unknown':
            return None
        
        logger.info(f"ICT Manipulation playbook matched: {met_count}/{total_conditions}")
        
        return PlaybookMatch(
            symbol=market_state.symbol,
            playbook_name=ICTManipulationReversalPlaybook.name,
            playbook_description=ICTManipulationReversalPlaybook.description,
            conditions_total=total_conditions,
            conditions_met=met_count,
            conditions_details=conditions_met,
            match_score=met_count / total_conditions,
            direction='LONG' if direction == 'bullish' else 'SHORT'
        )


class PlaybookEngine:
    """Moteur de gestion des playbooks"""
    
    def __init__(self):
        self.ny_open_reversal = NYOpenReversalPlaybook()
        self.london_sweep = LondonSweepPlaybook()
        self.trend_continuation = TrendContinuationPlaybook()
        self.ict_manipulation = ICTManipulationReversalPlaybook()
        
        logger.info("PlaybookEngine initialized with 4 playbooks")
    
    def check_all_playbooks(self, market_state: MarketState,
                           liquidity_engine: LiquidityEngine,
                           ict_patterns: List[ICTPattern],
                           current_time: datetime) -> List[PlaybookMatch]:
        """Vérifie tous les playbooks et retourne les matches"""
        
        matches = []
        
        # NY Open
        ny_match = self.ny_open_reversal.check_conditions(
            market_state, liquidity_engine, ict_patterns, current_time
        )
        if ny_match:
            matches.append(ny_match)
        
        # London Sweep
        london_match = self.london_sweep.check_conditions(
            market_state, liquidity_engine, ict_patterns, current_time
        )
        if london_match:
            matches.append(london_match)
        
        # Trend Continuation
        trend_match = self.trend_continuation.check_conditions(
            market_state, liquidity_engine, ict_patterns, current_time
        )
        if trend_match:
            matches.append(trend_match)
        
        # ICT Manipulation
        ict_match = self.ict_manipulation.check_conditions(
            market_state, liquidity_engine, ict_patterns, current_time
        )
        if ict_match:
            matches.append(ict_match)
        
        logger.info(f"Playbook check complete: {len(matches)} matches found")
        
        return matches
