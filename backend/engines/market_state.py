"""Module Market State - Analyse HTF et détermination du biais"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from models.market_data import Candle, MarketState
from utils.indicators import detect_structure, calculate_pivot_points

logger = logging.getLogger(__name__)

class MarketStateEngine:
    """Moteur d'analyse de l'état du marché et détermination du biais"""
    
    def __init__(self):
        self.current_states = {}  # {symbol: MarketState}
        logger.info("MarketStateEngine initialized")
    
    def analyze_htf_structure(self, daily: List[Candle], h4: List[Candle], h1: List[Candle]) -> Dict[str, str]:
        """
        Analyse la structure sur les timeframes élevés
        
        Returns:
            Dict avec 'daily_structure', 'h4_structure', 'h1_structure'
        """
        structures = {}
        
        # Analyser chaque timeframe
        if daily:
            structures['daily_structure'] = detect_structure([
                {'high': c.high, 'low': c.low, 'close': c.close, 'timestamp': c.timestamp}
                for c in daily
            ])
        
        if h4:
            structures['h4_structure'] = detect_structure([
                {'high': c.high, 'low': c.low, 'close': c.close, 'timestamp': c.timestamp}
                for c in h4
            ])
        
        if h1:
            structures['h1_structure'] = detect_structure([
                {'high': c.high, 'low': c.low, 'close': c.close, 'timestamp': c.timestamp}
                for c in h1
            ])
        
        return structures
    
    def determine_bias(self, daily: List[Candle], h4: List[Candle], h1: List[Candle], 
                       session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Détermine le biais directionnel du jour
        
        Logic:
        - Daily uptrend + H4 uptrend + H1 uptrend = Strong Bullish
        - Daily downtrend + H4 downtrend + H1 downtrend = Strong Bearish
        - Mix = Neutral / Attente de confirmation
        - Prendre en compte la liquidité prise/non prise
        
        Returns:
            Dict avec 'bias', 'confidence', 'reasoning'
        """
        if not daily or not h4 or not h1:
            return {'bias': 'neutral', 'confidence': 0.0, 'reasoning': 'Insufficient data'}
        
        # Analyser structures
        structures = self.analyze_htf_structure(daily, h4, h1)
        daily_structure = structures.get('daily_structure', 'unknown')
        h4_structure = structures.get('h4_structure', 'unknown')
        h1_structure = structures.get('h1_structure', 'unknown')
        
        # Scoring
        bullish_score = 0
        bearish_score = 0
        
        if daily_structure == 'uptrend':
            bullish_score += 3
        elif daily_structure == 'downtrend':
            bearish_score += 3
        
        if h4_structure == 'uptrend':
            bullish_score += 2
        elif h4_structure == 'downtrend':
            bearish_score += 2
        
        if h1_structure == 'uptrend':
            bullish_score += 1
        elif h1_structure == 'downtrend':
            bearish_score += 1
        
        # Déterminer biais
        total_score = bullish_score + bearish_score
        if total_score == 0:
            return {'bias': 'neutral', 'confidence': 0.0, 'reasoning': 'No clear structure'}
        
        if bullish_score > bearish_score:
            bias = 'bullish'
            confidence = bullish_score / 6.0  # Max = 6
            reasoning = f"Daily: {daily_structure}, H4: {h4_structure}, H1: {h1_structure}"
        elif bearish_score > bullish_score:
            bias = 'bearish'
            confidence = bearish_score / 6.0
            reasoning = f"Daily: {daily_structure}, H4: {h4_structure}, H1: {h1_structure}"
        else:
            bias = 'neutral'
            confidence = 0.5
            reasoning = "Mixed signals across timeframes"
        
        return {
            'bias': bias,
            'confidence': confidence,
            'reasoning': reasoning,
            'structures': structures
        }
    
    def classify_session_profile(self, previous_session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classifie le profil de session selon les 3 types TJR
        
        Profils:
        1. Session précédente plate (consolidation) → manipulation + reversal
        2. Session précédente avec manipulation sans gros trend → reversal principal
        3. Session précédente avec manipulation & trend → continuation
        
        Args:
            previous_session_data: Données de la session précédente
                - 'range_pct': % du range de la session
                - 'had_manipulation': bool
                - 'had_trend': bool
        
        Returns:
            Dict avec 'profile' (1, 2, ou 3), 'description', 'expected_behavior'
        """
        range_pct = previous_session_data.get('range_pct', 0)
        had_manipulation = previous_session_data.get('had_manipulation', False)
        had_trend = previous_session_data.get('had_trend', False)
        
        # Profil 1: Consolidation (range serré)
        if range_pct < 0.5:  # Range < 0.5% du prix
            return {
                'profile': 1,
                'description': 'Consolidation précédente',
                'expected_behavior': 'Attente manipulation + reversal directionnel',
                'reasoning': f"Range serré ({range_pct:.2f}%), accumulation d'énergie"
            }
        
        # Profil 2: Manipulation sans gros trend
        if had_manipulation and not had_trend:
            return {
                'profile': 2,
                'description': 'Manipulation sans trend soutenu',
                'expected_behavior': 'Reversal principal dans direction opposée',
                'reasoning': 'Manipulation détectée mais trend non confirmé'
            }
        
        # Profil 3: Manipulation + Trend fort
        if had_manipulation and had_trend:
            return {
                'profile': 3,
                'description': 'Manipulation + Trend établi',
                'expected_behavior': 'Continuation de la tendance',
                'reasoning': 'Trend confirmé après manipulation initiale'
            }
        
        # Par défaut: Profil 2 (plus commun)
        return {
            'profile': 2,
            'description': 'Profil mixte',
            'expected_behavior': 'Attente de confirmation directionnelle',
            'reasoning': 'Signaux mixés, rester prudent'
        }
    
    def calculate_day_type(self, daily_structure: str, ict_patterns: List) -> str:
        """
        Calculate day_type for playbook filtering (P1 implementation)
        
        Args:
            daily_structure: 'uptrend', 'downtrend', 'range', 'unknown'
            ict_patterns: List[ICTPattern] (may be empty in current call)
        
        Returns:
            'trend', 'manipulation_reversal', 'range', or 'unknown'
        """
        # Count pattern types if available
        bos_count = len([p for p in ict_patterns if p.pattern_type == 'bos']) if ict_patterns else 0
        sweep_count = len([p for p in ict_patterns if p.pattern_type == 'sweep']) if ict_patterns else 0
        
        # Rule 1: Range structure → range day
        if daily_structure == 'range':
            return 'range'
        
        # Rule 2: Sweep + BOS → manipulation_reversal
        if sweep_count >= 1 and bos_count >= 1:
            return 'manipulation_reversal'
        
        # Rule 3: Clear trend structure + multiple BOS → trend day
        if daily_structure in ['uptrend', 'downtrend']:
            if bos_count >= 2:
                return 'trend'
            # Default to trend if structure is clear (even without BOS count)
            return 'trend'
        
        # Rule 4: Unknown structure → unknown day_type
        return 'unknown'
    
    def mark_htf_levels(self, daily: List[Candle], h4: List[Candle], 
                        session_highs_lows: Dict[str, float]) -> Dict[str, float]:
        """
        Marque les niveaux HTF importants
        
        Args:
            daily: Bougies daily
            h4: Bougies H4
            session_highs_lows: Dict avec asia_high, asia_low, london_high, london_low
        
        Returns:
            Dict avec tous les niveaux importants
        """
        levels = {}
        
        # Previous Day High/Low
        if len(daily) >= 2:
            levels['pdh'] = daily[-2].high
            levels['pdl'] = daily[-2].low
        
        # Session levels
        levels.update(session_highs_lows)
        
        # Weekly High/Low (si disponible)
        if len(daily) >= 5:
            last_week = daily[-5:]
            levels['weekly_high'] = max(c.high for c in last_week)
            levels['weekly_low'] = min(c.low for c in last_week)
        
        return levels
    
    def create_market_state(self, symbol: str, multi_tf_data: Dict[str, List[Candle]], 
                           session_info: Dict[str, Any]) -> MarketState:
        """
        Crée un objet MarketState complet pour un symbole
        
        Args:
            symbol: Ticker
            multi_tf_data: Dict avec clés = timeframes, valeurs = listes de Candles
            session_info: Infos sur les sessions (highs/lows Asia, London)
        
        Returns:
            MarketState object
        """
        import time
        t_start = time.perf_counter()
        
        # 1. Prepare inputs
        t0 = time.perf_counter()
        daily = multi_tf_data.get('1d', [])
        h4 = multi_tf_data.get('4h', [])
        h1 = multi_tf_data.get('1h', [])
        t_prepare_inputs = (time.perf_counter() - t0) * 1000
        
        # 2. Detect structure
        t0 = time.perf_counter()
        structures = self.analyze_htf_structure(daily, h4, h1)
        t_detect_structure = (time.perf_counter() - t0) * 1000
        
        # 3. Bias calculation
        t0 = time.perf_counter()
        bias_analysis = self.determine_bias(daily, h4, h1, session_info)
        bias_analysis['structures'] = structures  # Merge
        t_bias_calc = (time.perf_counter() - t0) * 1000
        
        # 4. Profile & confluence
        t0 = time.perf_counter()
        # Classifier profil session
        session_profile = self.classify_session_profile({
            'range_pct': 0.3,
            'had_manipulation': True,
            'had_trend': False
        })
        
        # Marquer niveaux HTF
        htf_levels = self.mark_htf_levels(daily, h4, session_info.get('session_levels', {}))
        t_profile_confluence = (time.perf_counter() - t0) * 1000
        
        # 4b. Day_type calculation (P1: trend/manipulation_reversal/range)
        t0 = time.perf_counter()
        day_type = self.calculate_day_type(
            daily_structure=structures.get('daily_structure', 'unknown'),
            ict_patterns=[]  # Placeholder: will be populated by BacktestEngine
        )
        t_day_type = (time.perf_counter() - t0) * 1000
        
        # 5. Finalize state
        t0 = time.perf_counter()
        market_state = MarketState(
            symbol=symbol,
            bias=bias_analysis['bias'],
            bias_confidence=bias_analysis['confidence'],
            session_profile=session_profile['profile'],
            session_profile_description=session_profile['description'],
            daily_structure=structures.get('daily_structure', 'unknown'),
            h4_structure=structures.get('h4_structure', 'unknown'),
            h1_structure=structures.get('h1_structure', 'unknown'),
            day_type=day_type,  # Inject calculated day_type
            pdh=htf_levels.get('pdh'),
            pdl=htf_levels.get('pdl'),
            asia_high=htf_levels.get('asia_high'),
            asia_low=htf_levels.get('asia_low'),
            london_high=htf_levels.get('london_high'),
            london_low=htf_levels.get('london_low'),
            weekly_high=htf_levels.get('weekly_high'),
            weekly_low=htf_levels.get('weekly_low')
        )
        t_finalize_state = (time.perf_counter() - t0) * 1000
        
        t_total = (time.perf_counter() - t_start) * 1000
        
        # Log instrumentation
        if hasattr(self, '_instrumentation_log'):
            self._instrumentation_log.append({
                'symbol': symbol,
                't_prepare_ms': t_prepare_inputs,
                't_detect_structure_ms': t_detect_structure,
                't_bias_calc_ms': t_bias_calc,
                't_profile_confluence_ms': t_profile_confluence,
                't_finalize_ms': t_finalize_state,
                't_total_ms': t_total,
                'daily_candles': len(daily),
                'h4_candles': len(h4),
                'h1_candles': len(h1)
            })
        
        return market_state
        
        logger.info(f"Market State created for {symbol}: Bias={market_state.bias} "
                   f"({market_state.bias_confidence:.2f}), Profile={market_state.session_profile}")
        
        return market_state
    
    def get_current_state(self, symbol: str) -> Optional[MarketState]:
        """Récupère l'état actuel du marché pour un symbole"""
        return self.current_states.get(symbol)
