"""Setup Engine - Scoring vectoriel & Classification A+/A/B/C"""
import logging
from typing import List, Optional
from datetime import datetime
from models.market_data import MarketState, LiquidityLevel
from models.setup import Setup, PatternDetection, PlaybookMatch, ICTPattern
from config.settings import settings

logger = logging.getLogger(__name__)

def calculate_ict_score(ict_patterns: List[ICTPattern], 
                        swept_levels: List[LiquidityLevel]) -> float:
    """
    Calcule score ICT basé sur présence des éléments
    
    Composants (Architecture SPY/QQQ):
    - Sweep: 0.3
    - BOS: 0.3
    - FVG: 0.2
    - SMT: 0.2
    
    Returns:
        Score 0.0-1.0
    """
    score = 0.0
    
    # Sweep détecté (0.3)
    if swept_levels:
        # Bonus si sweep fort (rejection forte)
        recent_sweeps = [s for s in swept_levels 
                        if s.sweep_details and s.sweep_details.get('is_strong_rejection')]
        if recent_sweeps:
            score += 0.3
        elif swept_levels:
            score += 0.2  # Sweep sans rejection forte
    
    # BOS détecté (0.3)
    bos_patterns = [p for p in ict_patterns if p.pattern_type == 'bos']
    if bos_patterns:
        # Utiliser confidence du dernier BOS
        score += 0.3 * bos_patterns[-1].confidence
    
    # FVG présent (0.2)
    fvg_patterns = [p for p in ict_patterns if p.pattern_type == 'fvg']
    if fvg_patterns:
        score += 0.2
    
    # SMT divergence (0.2)
    smt_patterns = [p for p in ict_patterns if p.pattern_type == 'smt']
    if smt_patterns:
        score += 0.2 * smt_patterns[-1].confidence
    
    return min(score, 1.0)


def calculate_pattern_score(candlestick_patterns: List[PatternDetection]) -> float:
    """
    Score basé sur qualité des patterns chandeliers
    
    Returns:
        Score 0.0-1.0
    """
    if not candlestick_patterns:
        return 0.0
    
    # Prendre le meilleur pattern
    best_pattern = max(candlestick_patterns, key=lambda p: p.pattern_score)
    
    # Mapping strength → multiplier
    strength_map = {
        'strong': 1.0,
        'medium': 0.7,
        'weak': 0.4
    }
    
    base_score = best_pattern.pattern_score
    strength_multiplier = strength_map.get(best_pattern.strength, 0.5)
    
    # Bonus contexte
    context_bonus = 0.0
    if best_pattern.at_htf_level:
        context_bonus += 0.15
    if best_pattern.after_sweep:
        context_bonus += 0.15
    if best_pattern.at_support_resistance:
        context_bonus += 0.10
    
    final_score = (base_score * strength_multiplier) + context_bonus
    
    return min(final_score, 1.0)


def calculate_playbook_score(playbook_matches: List[PlaybookMatch]) -> float:
    """
    Score basé sur match avec playbooks
    
    Returns:
        Score 0.0-1.0
    """
    if not playbook_matches:
        return 0.0
    
    # Prendre le meilleur match
    best_match = max(playbook_matches, key=lambda p: p.match_score)
    
    return best_match.match_score


class SetupEngine:
    """Moteur de scoring et classification des setups"""
    
    def __init__(self):
        self.weights = settings.SETUP_WEIGHTS
        logger.info(f"SetupEngine initialized with weights: {self.weights}")
    
    def score_setup(self,
                   symbol: str,
                   market_state: MarketState,
                   ict_patterns: List[ICTPattern],
                   candlestick_patterns: List[PatternDetection],
                   playbook_matches: List[PlaybookMatch],
                   swept_levels: List[LiquidityLevel],
                   current_price: float) -> Optional[Setup]:
        """
        Score un setup complet et le classifie
        
        Returns:
            Setup object avec quality A+/A/B/C ou None si pas de signal
        """
        
        # Vérifier qu'on a au moins un signal
        if not ict_patterns and not candlestick_patterns and not playbook_matches:
            return None
        
        # Calculer scores composants
        ict_score = calculate_ict_score(ict_patterns, swept_levels)
        pattern_score = calculate_pattern_score(candlestick_patterns)
        playbook_score = calculate_playbook_score(playbook_matches)
        
        # Score final pondéré (formule Architecture SPY/QQQ)
        final_score = (
            self.weights['ict'] * ict_score +
            self.weights['pattern'] * pattern_score +
            self.weights['playbook'] * playbook_score
        )
        
        # Classification selon seuils (settings.py)
        # TODO: à calibrer avec backtests
        if final_score >= settings.QUALITY_THRESHOLD_A_PLUS:
            quality = 'A+'
        elif final_score >= settings.QUALITY_THRESHOLD_A:
            quality = 'A'
        elif final_score >= settings.QUALITY_THRESHOLD_B:
            quality = 'B'
        else:
            quality = 'C'
        
        # Déterminer direction
        direction = self._determine_direction(ict_patterns, candlestick_patterns, playbook_matches)
        
        if not direction:
            return None
        
        # Comptage confluences
        confluences_count = self._count_confluences(
            has_sweep=len(swept_levels) > 0,
            has_bos=any(p.pattern_type == 'bos' for p in ict_patterns),
            has_fvg=any(p.pattern_type == 'fvg' for p in ict_patterns),
            has_pattern=len(candlestick_patterns) > 0,
            has_smt=any(p.pattern_type == 'smt' for p in ict_patterns),
            htf_aligned=self._check_htf_alignment(direction, market_state.bias)
        )
        
        # Déterminer type de trade (Daily vs Scalp)
        trade_type = self._determine_trade_type(playbook_matches, confluences_count)
        
        # Calculer entry/SL/TP
        entry, sl, tp1, tp2, rr = self._calculate_trade_levels(
            direction, current_price, ict_patterns, swept_levels, market_state
        )
        
        # Créer Setup
        setup = Setup(
            symbol=symbol,
            quality=quality,
            final_score=final_score,
            ict_score=ict_score,
            pattern_score=pattern_score,
            playbook_score=playbook_score,
            ict_patterns=ict_patterns,
            candlestick_patterns=candlestick_patterns,
            playbook_matches=playbook_matches,
            trade_type=trade_type,
            direction=direction,
            entry_price=entry,
            stop_loss=sl,
            take_profit_1=tp1,
            take_profit_2=tp2,
            risk_reward=rr,
            market_bias=market_state.bias,
            session=market_state.current_session,
            confluences_count=confluences_count,
            notes=f"Score: ICT={ict_score:.2f}, Pattern={pattern_score:.2f}, Playbook={playbook_score:.2f}"
        )
        
        logger.info(f"Setup scored: {symbol} {quality} ({final_score:.3f}), "
                   f"{direction}, {confluences_count} confluences, R:R {rr:.2f}")
        
        return setup
    
    def _determine_direction(self, ict_patterns: List[ICTPattern],
                            candlestick_patterns: List[PatternDetection],
                            playbook_matches: List[PlaybookMatch]) -> Optional[str]:
        """Détermine direction du trade (LONG/SHORT)"""
        
        # Priorité 1: Playbook
        if playbook_matches:
            best_playbook = max(playbook_matches, key=lambda p: p.match_score)
            return best_playbook.direction
        
        # Priorité 2: ICT BOS
        bos_patterns = [p for p in ict_patterns if p.pattern_type == 'bos']
        if bos_patterns:
            direction_map = {'bullish': 'LONG', 'bearish': 'SHORT'}
            return direction_map.get(bos_patterns[-1].direction)
        
        # Priorité 3: Pattern chandelier
        if candlestick_patterns:
            best_pattern = max(candlestick_patterns, key=lambda p: p.pattern_score)
            if 'bullish' in best_pattern.pattern_type:
                return 'LONG'
            elif 'bearish' in best_pattern.pattern_type:
                return 'SHORT'
        
        return None
    
    def _count_confluences(self, **kwargs) -> int:
        """Compte le nombre de confluences présentes"""
        return sum(1 for v in kwargs.values() if v)
    
    def _check_htf_alignment(self, direction: str, bias: str) -> bool:
        """Vérifie alignement avec biais HTF"""
        if direction == 'LONG' and bias == 'bullish':
            return True
        if direction == 'SHORT' and bias == 'bearish':
            return True
        return False
    
    def _determine_trade_type(self, playbook_matches: List[PlaybookMatch],
                             confluences_count: int) -> str:
        """Détermine DAILY vs SCALP"""
        
        # Si playbook NY Open ou London Sweep → Daily
        if playbook_matches:
            daily_playbooks = ['NY_Open_Reversal', 'London_Sweep', 'ICT_Manipulation_Reversal']
            for pb in playbook_matches:
                if pb.playbook_name in daily_playbooks:
                    return 'DAILY'
        
        # Si moins de 4 confluences → Scalp
        if confluences_count < 4:
            return 'SCALP'
        
        return 'DAILY'
    
    def _calculate_trade_levels(self, direction: str, current_price: float,
                                ict_patterns: List[ICTPattern],
                                swept_levels: List[LiquidityLevel],
                                market_state: MarketState) -> tuple:
        """
        Calcule entry, SL, TP1, TP2, R:R
        
        Returns:
            (entry, stop_loss, tp1, tp2, risk_reward)
        """
        
        # Logique simplifiée pour MVP
        # TODO: affiner avec FVG optimal entry, Order Blocks, etc.
        
        # Entry: prix actuel avec léger offset
        if direction == 'LONG':
            entry = current_price * 1.001  # 0.1% au-dessus
        else:
            entry = current_price * 0.999  # 0.1% en-dessous
        
        # Stop Loss: basé sur sweep si disponible, sinon ATR
        if swept_levels:
            last_sweep = swept_levels[-1]
            if direction == 'LONG':
                sl = last_sweep.price * 0.999  # Sous le sweep
            else:
                sl = last_sweep.price * 1.001  # Au-dessus du sweep
        else:
            # Fallback: 0.5% du prix
            if direction == 'LONG':
                sl = entry * 0.995
            else:
                sl = entry * 1.005
        
        # Take Profit: basé sur niveaux HTF
        if direction == 'LONG':
            # TP1: mid-range, TP2: high
            tp1 = market_state.asia_high or (entry * 1.015)
            tp2 = market_state.pdh or (entry * 1.025)
        else:
            # TP1: mid-range, TP2: low
            tp1 = market_state.asia_low or (entry * 0.985)
            tp2 = market_state.pdl or (entry * 0.975)
        
        # Risk:Reward
        if direction == 'LONG':
            risk = entry - sl
            reward = tp1 - entry
        else:
            risk = sl - entry
            reward = entry - tp1
        
        rr = reward / risk if risk > 0 else 0
        
        return (entry, sl, tp1, tp2, rr)


def filter_setups_safe_mode(setups: List[Setup]) -> List[Setup]:
    """
    Filtre setups pour Mode SAFE
    
    Critères (spec Phase 1.2):
    - Quality A+ uniquement
    - Confluences minimum: 4/6 (Daily), 3/5 (Scalp)
    - R:R minimum: 2:1 (Daily), 1.5:1 (Scalp)
    - Alignement HTF obligatoire
    """
    filtered = []
    
    for setup in setups:
        # Qualité A+ uniquement
        if setup.quality != 'A+':
            continue
        
        # Confluences minimum
        if setup.trade_type == 'DAILY' and setup.confluences_count < 4:
            continue
        if setup.trade_type == 'SCALP' and setup.confluences_count < 3:
            continue
        
        # R:R minimum
        if setup.trade_type == 'DAILY' and setup.risk_reward < 2.0:
            continue
        if setup.trade_type == 'SCALP' and setup.risk_reward < 1.5:
            continue
        
        # Alignement HTF obligatoire
        if setup.direction == 'LONG' and setup.market_bias != 'bullish':
            continue
        if setup.direction == 'SHORT' and setup.market_bias != 'bearish':
            continue
        
        filtered.append(setup)
    
    logger.info(f"SAFE mode filter: {len(filtered)}/{len(setups)} setups passed")
    return filtered


def filter_setups_aggressive_mode(setups: List[Setup]) -> List[Setup]:
    """
    Filtre setups pour Mode AGRESSIF
    
    Critères:
    - Quality A ou A+
    - Confluences minimum: 3/6 (Daily), 2/5 (Scalp)
    - R:R minimum: 1.5:1
    - Alignement HTF recommandé mais non obligatoire
    """
    filtered = []
    
    for setup in setups:
        # Qualité A ou A+
        if setup.quality not in ['A+', 'A']:
            continue
        
        # Confluences minimum réduites
        if setup.trade_type == 'DAILY' and setup.confluences_count < 3:
            continue
        if setup.trade_type == 'SCALP' and setup.confluences_count < 2:
            continue
        
        # R:R minimum unifié
        if setup.risk_reward < 1.5:
            continue
        
        filtered.append(setup)
    
    logger.info(f"AGGRESSIVE mode filter: {len(filtered)}/{len(setups)} setups passed")
    return filtered
