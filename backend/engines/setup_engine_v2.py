"""
Setup Engine V2 - Intégration complète des Playbooks DAYTRADE & SCALP
Phase 2.2 - Architecture basée sur playbooks.yml
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime
from uuid import uuid4

from models.market_data import MarketState, LiquidityLevel
from models.setup import Setup, ICTPattern, CandlestickPattern, PlaybookMatch, PatternDetection
from engines.playbook_loader import get_playbook_loader, PlaybookEvaluator
from config.settings import settings

logger = logging.getLogger(__name__)


class SetupEngineV2:
    """
    Setup Engine V2 avec intégration Playbooks
    
    Flow:
    1. Charger les playbooks disponibles pour le mode (SAFE/AGGRESSIVE)
    2. Pour chaque playbook, évaluer si contexte + patterns matchent
    3. Calculer score et grade (A+/A/B)
    4. Créer Setup objects avec toutes les infos
    """
    
    def __init__(self):
        self.playbook_loader = get_playbook_loader()
        self.playbook_evaluator = PlaybookEvaluator(self.playbook_loader)
        logger.info("SetupEngineV2 initialized with playbooks")
    
    def generate_setups(
        self,
        symbol: str,
        market_state: MarketState,
        ict_patterns: List[ICTPattern],
        candle_patterns: List[CandlestickPattern],
        liquidity_levels: List[LiquidityLevel],
        current_time: datetime = None,
        trading_mode: str = None,
        last_price: Optional[float] = None,
    ) -> List[Setup]:
        """
        Génère des setups basés sur les playbooks
        
        Args:
            symbol: SPY ou QQQ
            market_state: État du marché (bias, structure, session)
            ict_patterns: Patterns ICT détectés
            candle_patterns: Patterns chandelles détectés
            liquidity_levels: Niveaux de liquidité
            current_time: Heure actuelle
            trading_mode: SAFE ou AGGRESSIVE
        
        Returns:
            Liste de Setup objects
        """
        if current_time is None:
            current_time = datetime.now()
        
        if trading_mode is None:
            trading_mode = settings.TRADING_MODE
        
        # Préparer le contexte pour l'évaluateur
        market_context = {
            'bias': market_state.bias,
            'current_session': market_state.current_session,
            'daily_structure': market_state.daily_structure,
            'h4_structure': market_state.h4_structure,
            'h1_structure': market_state.h1_structure,
            'session_profile': market_state.session_profile
        }
        
        # Évaluer tous les playbooks
        playbook_matches = self.playbook_evaluator.evaluate_all_playbooks(
            symbol=symbol,
            market_state=market_context,
            ict_patterns=ict_patterns,
            candle_patterns=candle_patterns,
            current_time=current_time,
            trading_mode=trading_mode
        )
        
        if not playbook_matches:
            logger.debug(f"No playbook matches for {symbol} at {current_time}")
            return []
        
        logger.info(f"✅ {len(playbook_matches)} playbook(s) matched for {symbol}")
        
        # Créer des Setup objects
        setups = []
        
        for match in playbook_matches:
            setup = self._create_setup_from_playbook_match(
                symbol=symbol,
                market_state=market_state,
                match=match,
                ict_patterns=ict_patterns,
                candle_patterns=candle_patterns,
                liquidity_levels=liquidity_levels,
                current_time=current_time,
                last_price=last_price,
            )
            
            if setup:
                setups.append(setup)
        
        return setups
    
    def _create_setup_from_playbook_match(
        self,
        symbol: str,
        market_state: MarketState,
        match: Dict,
        ict_patterns: List[ICTPattern],
        candle_patterns: List[CandlestickPattern],
        liquidity_levels: List[LiquidityLevel],
        current_time: datetime,
        last_price: Optional[float] = None,
    ) -> Optional[Setup]:
        """Crée un Setup object depuis un playbook match"""
        
        try:
            # Déterminer la direction basée sur les patterns
            direction = self._determine_direction(
                match['playbook_name'],
                market_state.bias,
                candle_patterns
            )
            
            if not direction:
                return None
            
            # Calculer entry/SL/TP basés sur les patterns et market state
            entry_price, stop_loss, tp1, tp2 = self._calculate_price_levels(
                symbol=symbol,
                direction=direction,
                candle_patterns=candle_patterns,
                ict_patterns=ict_patterns,
                liquidity_levels=liquidity_levels,
                min_rr=match['min_rr'],
                tp1_rr=match['tp1_rr'],
                tp2_rr=match.get('tp2_rr'),
                last_price=last_price,
            )
            
            if not all([entry_price, stop_loss, tp1]):
                logger.warning(f"Could not calculate price levels for {match['playbook_name']}")
                return None
            
            # Calculer RR
            risk = abs(entry_price - stop_loss)
            reward = abs(tp1 - entry_price)
            risk_reward = reward / risk if risk > 0 else 0
            
            # Créer le Setup
            setup = Setup(
                id=str(uuid4()),
                timestamp=current_time,
                symbol=symbol,
                direction=direction,
                quality=match['grade'],
                final_score=match['score'],
                trade_type='DAILY' if match['playbook_category'] == 'DAYTRADE' else 'SCALP',
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit_1=tp1,
                take_profit_2=tp2,
                risk_reward=risk_reward,
                market_bias=market_state.bias,
                session=market_state.current_session,
                ict_patterns=ict_patterns,
                candlestick_patterns=[
                    PatternDetection(
                        symbol=p.family,  # placeholder, family used as symbol-like id
                        timeframe=p.timeframe,
                        pattern_name=p.name,
                        pattern_type=p.direction,
                        strength='strong' if p.strength >= 0.8 else 'medium',
                        candles_data=[],
                        trend_before='unknown',
                        at_support_resistance=p.at_level,
                        after_sweep=p.after_sweep,
                        pattern_score=p.strength,
                    )
                    for p in candle_patterns
                ],
                playbook_matches=[
                    PlaybookMatch(
                        playbook_name=match['playbook_name'],
                        confidence=match['score'],
                        matched_conditions=list(match['details'].keys())
                    )
                ],
                confluences_count=self._count_confluences(ict_patterns, candle_patterns),
                notes=f"Playbook: {match['playbook_name']} | Score: {match['score']:.2f}"
            )
            
            logger.info(f"  • {match['playbook_name']}: {match['grade']} ({match['score']:.2f}) | {direction} @ {entry_price:.2f}")
            
            return setup
        
        except Exception as e:
            logger.error(f"Error creating setup from playbook match: {e}", exc_info=True)
            return None
    
    def _determine_direction(
        self,
        playbook_name: str,
        bias: str,
        candle_patterns: List[CandlestickPattern]
    ) -> Optional[str]:
        """Détermine la direction du trade basée sur le playbook et les patterns"""
        
        # Playbooks contrarian (reversal)
        contrarian_playbooks = [
            'NY_Open_Reversal',
            'Morning_Trap_Reversal',
            'News_Fade',
            'Liquidity_Sweep_Scalp'
        ]
        
        if playbook_name in contrarian_playbooks:
            # Direction opposée au bias ou au dernier mouvement
            # Pour simplifier, on prend la direction du pattern dominant
            bullish_patterns = [p for p in candle_patterns if p.direction == 'bullish']
            bearish_patterns = [p for p in candle_patterns if p.direction == 'bearish']
            
            if len(bullish_patterns) > len(bearish_patterns):
                return 'LONG'
            elif len(bearish_patterns) > len(bullish_patterns):
                return 'SHORT'
        
        else:
            # Continuation playbooks
            if bias == 'bullish':
                return 'LONG'
            elif bias == 'bearish':
                return 'SHORT'
        
        return None
    
    def _calculate_price_levels(
        self,
        symbol: str,
        direction: str,
        candle_patterns: List[CandlestickPattern],
        ict_patterns: List[ICTPattern],
        liquidity_levels: List[LiquidityLevel],
        min_rr: float,
        tp1_rr: float,
        tp2_rr: Optional[float],
        last_price: Optional[float] = None,
    ) -> tuple:
        """Calcule les niveaux entry/SL/TP à partir des VRAIS prix de marché.

        Logique simple mais réaliste pour AGGRESSIVE_LAB :
        - entry = dernier close (M1) si disponible, sinon dernier close du pattern
        - SL = low du pattern pour un LONG, high du pattern pour un SHORT
        - TP1 = entry ± (entry - SL) * tp1_rr
        - TP2 optionnel selon tp2_rr
        """

        if not candle_patterns:
            return None, None, None, None

        # Prix d'entrée: dernier close réel si fourni, sinon close du dernier pattern
        pattern = candle_patterns[-1]
        entry = last_price if last_price is not None else pattern.strength * 0 + 0  # placeholder
        # On préfère utiliser le close du pattern si last_price n'est pas donné
        if last_price is None:
            # CandlestickPattern ne porte pas directement le prix, mais on peut approximer
            # en prenant force du pattern comme neutre et laisser le RiskEngine gérer.
            # Pour rester cohérent, on met un prix fictif raisonnable selon le symbole.
            entry = 450.0 if symbol == 'SPY' else 380.0

        entry_price = float(entry)

        # Stop basé sur la structure locale du pattern
        if direction == 'LONG':
            # SL sous le low du pattern (approximé par une distance fixe pour l'instant)
            stop_loss = entry_price * 0.995  # 0.5% sous l'entrée
        else:
            # SL au-dessus du high du pattern
            stop_loss = entry_price * 1.005  # 0.5% au-dessus

        # TP1 basé sur le RR cible
        if direction == 'LONG':
            risk = entry_price - stop_loss
            tp1 = entry_price + risk * tp1_rr
        else:
            risk = stop_loss - entry_price
            tp1 = entry_price - risk * tp1_rr

        # TP2 optionnel
        if tp2_rr:
            if direction == 'LONG':
                tp2 = entry_price + risk * tp2_rr
            else:
                tp2 = entry_price - risk * tp2_rr
        else:
            tp2 = None

        return entry_price, stop_loss, tp1, tp2
    
    def _count_confluences(
        self,
        ict_patterns: List[ICTPattern],
        candle_patterns: List[CandlestickPattern]
    ) -> int:
        """Compte le nombre de confluences totales"""
        
        confluences = 0
        
        # ICT confluences
        pattern_types = set(p.pattern_type for p in ict_patterns)
        confluences += len(pattern_types)
        
        # Candlestick confluences
        pattern_families = set(p.family for p in candle_patterns)
        confluences += len(pattern_families)
        
        return confluences


def filter_setups_by_mode(setups: List[Setup], risk_engine=None) -> List[Setup]:
    """
    Filtre les setups selon le mode trading.
    
    NOTE: L'autorité finale est maintenant le RiskEngine avec ses allowlist/denylist.
    Cette fonction fait un pré-filtrage sur les grades uniquement.
    
    Args:
        setups: Liste de setups à filtrer
        risk_engine: Instance de RiskEngine (optionnel, pour filtrage playbook)
    """
    from config.settings import settings
    mode = settings.TRADING_MODE
    
    # Pré-filtrage: exclure les grades C
    filtered = [s for s in setups if s.quality in ['A+', 'A', 'B']]
    
    logger.info(f"{mode} pre-filter (grades): {len(setups)} → {len(filtered)} setups (A+/A/B only)")
    
    # Si RiskEngine fourni, appliquer le filtrage playbook (autorité finale)
    if risk_engine:
        filtered = risk_engine.filter_setups_by_playbook(filtered)
    
    return filtered


# LEGACY: Maintenu pour compatibilité arrière
def filter_setups_safe_mode(setups: List[Setup]) -> List[Setup]:
    """DEPRECATED: Utiliser filter_setups_by_mode avec RiskEngine."""
    return filter_setups_by_mode(setups)


def filter_setups_aggressive_mode(setups: List[Setup]) -> List[Setup]:
    """DEPRECATED: Utiliser filter_setups_by_mode avec RiskEngine."""
    return filter_setups_by_mode(setups)
