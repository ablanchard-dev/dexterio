"""ICT Pattern Engine - BOS, FVG, SMT, CHOCH"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from models.market_data import Candle
from models.setup import ICTPattern
from utils.indicators import calculate_pivot_points

logger = logging.getLogger(__name__)

class ICTPatternEngine:
    """Moteur de détection des patterns ICT"""
    
    def __init__(self):
        logger.info("ICTPatternEngine initialized")
    
    def detect_bos(self, candles: List[Candle], timeframe: str, atr: float = None) -> List[ICTPattern]:
        """
        Détecte Break of Structure (BOS) avec validation mathématique stricte
        
        Critères (selon mathematisation):
        - BOS Bullish: close_t > swing_high_prev + validation_buffer
        - BOS Bearish: close_t < swing_low_prev - validation_buffer
        - validation_buffer = breakout_close_atr * ATR (ex: 0.1 * ATR)
        - Force basée sur: breakout distance, volume, follow-through
        """
        if len(candles) < 10:
            return []
        
        bos_detections = []
        
        # Calculer ATR si non fourni
        if atr is None and len(candles) >= 14:
            tr_vals = []
            for i in range(1, min(len(candles), 14)):
                c_prev, c_curr = candles[-(i+1)], candles[-i]
                tr = max(
                    c_curr.high - c_curr.low,
                    abs(c_curr.high - c_prev.close),
                    abs(c_curr.low - c_prev.close)
                )
                tr_vals.append(tr)
            atr = sum(tr_vals) / len(tr_vals) if tr_vals else 0
        
        # Calculer pivots (lookback selon TF)
        lookback = 3 if timeframe in ['1m', '5m'] else 5
        pivots = calculate_pivot_points([
            {'high': c.high, 'low': c.low, 'timestamp': c.timestamp}
            for c in candles
        ], lookback=lookback)
        
        if not pivots['pivot_highs'] or not pivots['pivot_lows']:
            return bos_detections
        
        last_pivot_high = pivots['pivot_highs'][-1]['price']
        last_pivot_low = pivots['pivot_lows'][-1]['price']
        
        current_candle = candles[-1]
        prev_candle = candles[-2] if len(candles) >= 2 else current_candle
        
        # Buffer validation: breakout doit être clair (0.1 * ATR)
        validation_buffer = 0.1 * atr if atr else 0
        
        # BOS Haussier: close > swing_high + buffer
        if current_candle.close > last_pivot_high + validation_buffer:
            breakout_strength = (current_candle.close - last_pivot_high) / last_pivot_high
            
            # Volume ratio (current vs prev)
            vol_ratio = current_candle.volume / prev_candle.volume if prev_candle.volume > 0 else 1.0
            vol_score = min(vol_ratio / 1.5, 1.0)  # normalize: 1.5x = score 1.0
            
            # Follow-through: body ratio (close conviction)
            body_ratio = abs(current_candle.close - current_candle.open) / (current_candle.high - current_candle.low) if (current_candle.high - current_candle.low) > 0 else 0
            
            # Unified strength: breakout (50%) + volume (25%) + body (25%)
            strength = min(
                0.5 * min(breakout_strength * 100, 1.0) +
                0.25 * vol_score +
                0.25 * body_ratio,
                1.0
            )
            
            bos_detections.append(ICTPattern(
                symbol=current_candle.symbol,
                timeframe=timeframe,
                pattern_type='bos',
                direction='bullish',
                details={
                    'pivot_high_broken': last_pivot_high,
                    'close_price': current_candle.close,
                    'breakout_strength': breakout_strength,
                    'validation_buffer': validation_buffer,
                    'vol_ratio': vol_ratio,
                    'body_ratio': body_ratio,
                    'candle_timestamp': current_candle.timestamp.isoformat(),
                    'atr_used': atr
                },
                strength=strength,
                confidence=min(0.8 + breakout_strength * 10 + vol_score * 0.1, 1.0)
            ))
            
            logger.debug(f"BOS Bullish detected on {current_candle.symbol} {timeframe}: "
                       f"broke {last_pivot_high:.2f}, close {current_candle.close:.2f}, "
                       f"strength={strength:.2f}, vol_ratio={vol_ratio:.2f}")
        
        # BOS Baissier: close < swing_low - buffer
        if current_candle.close < last_pivot_low - validation_buffer:
            breakout_strength = (last_pivot_low - current_candle.close) / last_pivot_low
            
            vol_ratio = current_candle.volume / prev_candle.volume if prev_candle.volume > 0 else 1.0
            vol_score = min(vol_ratio / 1.5, 1.0)
            
            body_ratio = abs(current_candle.close - current_candle.open) / (current_candle.high - current_candle.low) if (current_candle.high - current_candle.low) > 0 else 0
            
            strength = min(
                0.5 * min(breakout_strength * 100, 1.0) +
                0.25 * vol_score +
                0.25 * body_ratio,
                1.0
            )
            
            bos_detections.append(ICTPattern(
                symbol=current_candle.symbol,
                timeframe=timeframe,
                pattern_type='bos',
                direction='bearish',
                details={
                    'pivot_low_broken': last_pivot_low,
                    'close_price': current_candle.close,
                    'breakout_strength': breakout_strength,
                    'validation_buffer': validation_buffer,
                    'vol_ratio': vol_ratio,
                    'body_ratio': body_ratio,
                    'candle_timestamp': current_candle.timestamp.isoformat(),
                    'atr_used': atr
                },
                strength=strength,
                confidence=min(0.8 + breakout_strength * 10 + vol_score * 0.1, 1.0)
            ))
            
            logger.debug(f"BOS Bearish detected on {current_candle.symbol} {timeframe}: "
                       f"broke {last_pivot_low:.2f}, close {current_candle.close:.2f}, "
                       f"strength={strength:.2f}, vol_ratio={vol_ratio:.2f}")
        
        return bos_detections
    
    def detect_fvg(self, candles: List[Candle], timeframe: str, 
                   min_size_pct: float = 0.1, atr: float = None) -> List[ICTPattern]:
        """
        Détecte Fair Value Gaps avec validation mathématique renforcée
        
        Critères (selon mathematisation):
        - FVG Bullish: high_{t-2} < low_t (gap clair)
        - FVG Bearish: low_{t-2} > high_t
        - Taille minimale: min_size_pct % du prix OU 0.3 * ATR
        - Force basée sur: gap_size, volume impulse candle, distance à price actuel
        """
        if len(candles) < 3:
            return []
        
        fvgs = []
        
        # Calculer ATR si non fourni
        if atr is None and len(candles) >= 14:
            tr_vals = []
            for i in range(1, min(len(candles), 14)):
                c_prev, c_curr = candles[-(i+1)], candles[-i]
                tr = max(
                    c_curr.high - c_curr.low,
                    abs(c_curr.high - c_prev.close),
                    abs(c_curr.low - c_prev.close)
                )
                tr_vals.append(tr)
            atr = sum(tr_vals) / len(tr_vals) if tr_vals else 0
        
        # Scanner les 30 dernières bougies (extend for better detection)
        start_idx = max(0, len(candles) - 30)
        current_price = candles[-1].close
        
        for i in range(start_idx + 2, len(candles)):
            c1, c2, c3 = candles[i-2], candles[i-1], candles[i]
            
            # FVG Bullish: gap entre c1.high et c3.low
            if c1.high < c3.low:
                gap_size = c3.low - c1.high
                gap_size_pct = (gap_size / c2.close) * 100
                
                # Validation: taille significative
                min_gap = max(c2.close * (min_size_pct / 100), 0.3 * atr if atr else 0)
                if gap_size < min_gap:
                    continue
                
                # Force basée sur:
                # - gap size (weighted)
                # - impulse candle volume (c3)
                # - proximité au prix actuel
                impulse_body_ratio = abs(c3.close - c3.open) / (c3.high - c3.low) if (c3.high - c3.low) > 0 else 0
                distance_to_current = abs(current_price - ((c3.low + c1.high) / 2))
                proximity_score = max(0, 1 - (distance_to_current / (current_price * 0.01)))  # decay sur 1%
                
                # Unified strength: gap (40%) + impulse (30%) + proximity (30%)
                strength = min(
                    0.4 * min(gap_size_pct * 2, 1.0) +
                    0.3 * impulse_body_ratio +
                    0.3 * proximity_score,
                    1.0
                )
                
                fvgs.append(ICTPattern(
                    symbol=c1.symbol,
                    timeframe=timeframe,
                    pattern_type='fvg',
                    direction='bullish',
                    details={
                        'top': c3.low,
                        'bottom': c1.high,
                        'midpoint': (c3.low + c1.high) / 2,
                        'size': gap_size,
                        'size_pct': gap_size_pct,
                        'impulse_body_ratio': impulse_body_ratio,
                        'proximity_score': proximity_score,
                        'candle_indices': [i-2, i-1, i],
                        'timestamp': c3.timestamp.isoformat(),
                        'atr_multiple': gap_size / atr if atr and atr > 0 else 0
                    },
                    strength=strength,
                    confidence=min(0.75 + gap_size_pct * 0.05 + impulse_body_ratio * 0.1, 0.95)
                ))
                
                logger.debug(f"FVG Bullish on {c1.symbol} {timeframe}: "
                            f"{c1.high:.2f} - {c3.low:.2f} ({gap_size_pct:.2f}%), "
                            f"strength={strength:.2f}, proximity={proximity_score:.2f}")
            
            # FVG Bearish: gap entre c3.high et c1.low
            if c1.low > c3.high:
                gap_size = c1.low - c3.high
                gap_size_pct = (gap_size / c2.close) * 100
                
                min_gap = max(c2.close * (min_size_pct / 100), 0.3 * atr if atr else 0)
                if gap_size < min_gap:
                    continue
                
                impulse_body_ratio = abs(c3.close - c3.open) / (c3.high - c3.low) if (c3.high - c3.low) > 0 else 0
                distance_to_current = abs(current_price - ((c1.low + c3.high) / 2))
                proximity_score = max(0, 1 - (distance_to_current / (current_price * 0.01)))
                
                strength = min(
                    0.4 * min(gap_size_pct * 2, 1.0) +
                    0.3 * impulse_body_ratio +
                    0.3 * proximity_score,
                    1.0
                )
                
                fvgs.append(ICTPattern(
                    symbol=c1.symbol,
                    timeframe=timeframe,
                    pattern_type='fvg',
                    direction='bearish',
                    details={
                        'top': c1.low,
                        'bottom': c3.high,
                        'midpoint': (c1.low + c3.high) / 2,
                        'size': gap_size,
                        'size_pct': gap_size_pct,
                        'impulse_body_ratio': impulse_body_ratio,
                        'proximity_score': proximity_score,
                        'candle_indices': [i-2, i-1, i],
                        'timestamp': c3.timestamp.isoformat(),
                        'atr_multiple': gap_size / atr if atr and atr > 0 else 0
                    },
                    strength=strength,
                    confidence=min(0.75 + gap_size_pct * 0.05 + impulse_body_ratio * 0.1, 0.95)
                ))
                
                logger.debug(f"FVG Bearish on {c1.symbol} {timeframe}: "
                            f"{c3.high:.2f} - {c1.low:.2f} ({gap_size_pct:.2f}%), "
                            f"strength={strength:.2f}, proximity={proximity_score:.2f}")
        
        # Filtrer les FVG trop anciens ou déjà invalidés (fill complet)
        valid_fvgs = []
        for fvg in fvgs:
            # Invalide si prix a traversé complètement le gap
            if fvg.direction == 'bullish' and current_price < fvg.details['bottom']:
                continue  # prix en dessous du gap = invalidé
            if fvg.direction == 'bearish' and current_price > fvg.details['top']:
                continue  # prix au dessus du gap = invalidé
            valid_fvgs.append(fvg)
        
        return valid_fvgs
    
    def detect_liquidity_sweep(self, candles: List[Candle], timeframe: str, 
                               lookback: int = 10, eps_atr: float = 0.05) -> List[ICTPattern]:
        """
        Détecte Liquidity Sweeps (stop hunts) selon mathematisation
        
        Critères:
        - Sweep High: high_t > swing_high_prev + eps BUT close_t < swing_high_prev (rejection)
        - Sweep Low: low_t < swing_low_prev - eps BUT close_t > swing_low_prev (rejection)
        - eps = eps_atr * ATR (buffer)
        - Force basée sur: wick size, rejection strength, follow-through
        """
        if len(candles) < lookback + 5:
            return []
        
        sweeps = []
        
        # Calculer ATR
        atr = 0
        if len(candles) >= 14:
            tr_vals = []
            for i in range(1, 14):
                c_prev, c_curr = candles[-(i+1)], candles[-i]
                tr = max(
                    c_curr.high - c_curr.low,
                    abs(c_curr.high - c_prev.close),
                    abs(c_curr.low - c_prev.close)
                )
                tr_vals.append(tr)
            atr = sum(tr_vals) / len(tr_vals)
        
        eps = eps_atr * atr if atr > 0 else 0
        
        # Identifier swings
        pivots = calculate_pivot_points([
            {'high': c.high, 'low': c.low, 'timestamp': c.timestamp}
            for c in candles
        ], lookback=3)
        
        if not pivots['pivot_highs'] or not pivots['pivot_lows']:
            return sweeps
        
        # Récupérer dernier swing high/low
        last_swing_high = pivots['pivot_highs'][-1]['price']
        last_swing_low = pivots['pivot_lows'][-1]['price']
        
        current_candle = candles[-1]
        
        # Sweep High (stop hunt above resistance)
        if current_candle.high > last_swing_high + eps and current_candle.close < last_swing_high:
            # Wick size (rejection magnitude)
            upper_wick = current_candle.high - max(current_candle.open, current_candle.close)
            wick_pct = (upper_wick / current_candle.high) * 100
            
            # Rejection strength: close vs swing
            rejection_dist = last_swing_high - current_candle.close
            rejection_score = min(rejection_dist / atr, 1.0) if atr > 0 else 0.5
            
            # Direction reversal (bearish after sweep)
            body_bearish = 1.0 if current_candle.close < current_candle.open else 0.5
            
            # Unified strength: wick (40%) + rejection (40%) + body (20%)
            strength = min(
                0.4 * min(wick_pct / 1.0, 1.0) +
                0.4 * rejection_score +
                0.2 * body_bearish,
                1.0
            )
            
            sweeps.append(ICTPattern(
                symbol=current_candle.symbol,
                timeframe=timeframe,
                pattern_type='liquidity_sweep',
                direction='bearish',  # bearish after sweep high
                details={
                    'sweep_level': last_swing_high,
                    'high_reached': current_candle.high,
                    'close_price': current_candle.close,
                    'upper_wick': upper_wick,
                    'wick_pct': wick_pct,
                    'rejection_dist': rejection_dist,
                    'rejection_score': rejection_score,
                    'eps_used': eps,
                    'timestamp': current_candle.timestamp.isoformat()
                },
                strength=strength,
                confidence=min(0.80 + rejection_score * 0.15, 0.95)
            ))
            
            logger.info(f"Liquidity Sweep HIGH detected on {current_candle.symbol} {timeframe}: "
                       f"swept {last_swing_high:.2f}, rejected to {current_candle.close:.2f}, "
                       f"strength={strength:.2f}")
        
        # Sweep Low (stop hunt below support)
        if current_candle.low < last_swing_low - eps and current_candle.close > last_swing_low:
            lower_wick = min(current_candle.open, current_candle.close) - current_candle.low
            wick_pct = (lower_wick / current_candle.low) * 100
            
            rejection_dist = current_candle.close - last_swing_low
            rejection_score = min(rejection_dist / atr, 1.0) if atr > 0 else 0.5
            
            body_bullish = 1.0 if current_candle.close > current_candle.open else 0.5
            
            strength = min(
                0.4 * min(wick_pct / 1.0, 1.0) +
                0.4 * rejection_score +
                0.2 * body_bullish,
                1.0
            )
            
            sweeps.append(ICTPattern(
                symbol=current_candle.symbol,
                timeframe=timeframe,
                pattern_type='liquidity_sweep',
                direction='bullish',  # bullish after sweep low
                details={
                    'sweep_level': last_swing_low,
                    'low_reached': current_candle.low,
                    'close_price': current_candle.close,
                    'lower_wick': lower_wick,
                    'wick_pct': wick_pct,
                    'rejection_dist': rejection_dist,
                    'rejection_score': rejection_score,
                    'eps_used': eps,
                    'timestamp': current_candle.timestamp.isoformat()
                },
                strength=strength,
                confidence=min(0.80 + rejection_score * 0.15, 0.95)
            ))
            
            logger.info(f"Liquidity Sweep LOW detected on {current_candle.symbol} {timeframe}: "
                       f"swept {last_swing_low:.2f}, rejected to {current_candle.close:.2f}, "
                       f"strength={strength:.2f}")
        
        return sweeps

    
    def detect_order_block(self, candles: List[Candle], timeframe: str, 
                          lookback: int = 20) -> List[ICTPattern]:
        """
        Détecte Order Blocks (OB) selon mathématisation ICT
        
        Critères:
        - Bullish OB: dernière bougie bearish avant BOS bullish
          Zone = [low, open] ou [low, close] selon plus conservateur
        - Bearish OB: dernière bougie bullish avant BOS bearish
          Zone = [open, high] ou [close, high]
        - Force basée sur: BOS magnitude, volume OB candle, zone size
        """
        if len(candles) < lookback + 5:
            return []
        
        order_blocks = []
        
        # Detect BOS first
        bos_patterns = self.detect_bos(candles, timeframe)
        
        for bos in bos_patterns:
            # Find the impulse candle that caused BOS
            bos_timestamp = bos.details.get('candle_timestamp')
            bos_idx = None
            for i, c in enumerate(candles):
                if c.timestamp.isoformat() == bos_timestamp:
                    bos_idx = i
                    break
            
            if bos_idx is None or bos_idx < 5:
                continue
            
            # Bullish BOS: find last bearish candle before impulse
            if bos.direction == 'bullish':
                # Scan backwards from BOS candle
                ob_candle = None
                for i in range(bos_idx - 1, max(0, bos_idx - 10), -1):
                    c = candles[i]
                    if c.close < c.open:  # bearish candle
                        ob_candle = c
                        ob_idx = i
                        break
                
                if ob_candle is None:
                    continue
                
                # OB zone: [low, open] (conservative) or [low, close]
                ob_bottom = ob_candle.low
                ob_top = min(ob_candle.open, ob_candle.close)
                zone_size = ob_top - ob_bottom
                zone_size_pct = (zone_size / ob_candle.close) * 100
                
                # Force basée sur BOS strength + OB zone quality
                bos_strength = bos.strength
                zone_score = min(zone_size_pct / 0.5, 1.0)  # 0.5% = score 1.0
                
                # Volume ratio (OB candle vs average)
                avg_vol = sum(c.volume for c in candles[max(0, ob_idx-10):ob_idx]) / min(10, ob_idx) if ob_idx > 0 else 1
                vol_ratio = ob_candle.volume / avg_vol if avg_vol > 0 else 1.0
                vol_score = min(vol_ratio / 1.5, 1.0)
                
                # Unified strength: BOS (50%) + zone (25%) + volume (25%)
                strength = min(
                    0.5 * bos_strength +
                    0.25 * zone_score +
                    0.25 * vol_score,
                    1.0
                )
                
                order_blocks.append(ICTPattern(
                    symbol=ob_candle.symbol,
                    timeframe=timeframe,
                    pattern_type='order_block',
                    direction='bullish',
                    details={
                        'zone_top': ob_top,
                        'zone_bottom': ob_bottom,
                        'zone_midpoint': (ob_top + ob_bottom) / 2,
                        'zone_size': zone_size,
                        'zone_size_pct': zone_size_pct,
                        'ob_candle_timestamp': ob_candle.timestamp.isoformat(),
                        'bos_triggered': bos_timestamp,
                        'vol_ratio': vol_ratio,
                        'caused_by_bos_strength': bos_strength
                    },
                    strength=strength,
                    confidence=min(0.80 + bos_strength * 0.15, 0.95)
                ))
                
                logger.info(f"Bullish Order Block detected on {ob_candle.symbol} {timeframe}: "
                           f"zone [{ob_bottom:.2f}, {ob_top:.2f}], strength={strength:.2f}")
            
            # Bearish BOS: find last bullish candle before impulse
            elif bos.direction == 'bearish':
                ob_candle = None
                for i in range(bos_idx - 1, max(0, bos_idx - 10), -1):
                    c = candles[i]
                    if c.close > c.open:  # bullish candle
                        ob_candle = c
                        ob_idx = i
                        break
                
                if ob_candle is None:
                    continue
                
                # OB zone: [open, high] or [close, high]
                ob_bottom = max(ob_candle.open, ob_candle.close)
                ob_top = ob_candle.high
                zone_size = ob_top - ob_bottom
                zone_size_pct = (zone_size / ob_candle.close) * 100
                
                bos_strength = bos.strength
                zone_score = min(zone_size_pct / 0.5, 1.0)
                
                avg_vol = sum(c.volume for c in candles[max(0, ob_idx-10):ob_idx]) / min(10, ob_idx) if ob_idx > 0 else 1
                vol_ratio = ob_candle.volume / avg_vol if avg_vol > 0 else 1.0
                vol_score = min(vol_ratio / 1.5, 1.0)
                
                strength = min(
                    0.5 * bos_strength +
                    0.25 * zone_score +
                    0.25 * vol_score,
                    1.0
                )
                
                order_blocks.append(ICTPattern(
                    symbol=ob_candle.symbol,
                    timeframe=timeframe,
                    pattern_type='order_block',
                    direction='bearish',
                    details={
                        'zone_top': ob_top,
                        'zone_bottom': ob_bottom,
                        'zone_midpoint': (ob_top + ob_bottom) / 2,
                        'zone_size': zone_size,
                        'zone_size_pct': zone_size_pct,
                        'ob_candle_timestamp': ob_candle.timestamp.isoformat(),
                        'bos_triggered': bos_timestamp,
                        'vol_ratio': vol_ratio,
                        'caused_by_bos_strength': bos_strength
                    },
                    strength=strength,
                    confidence=min(0.80 + bos_strength * 0.15, 0.95)
                ))
                
                logger.info(f"Bearish Order Block detected on {ob_candle.symbol} {timeframe}: "
                           f"zone [{ob_bottom:.2f}, {ob_top:.2f}], strength={strength:.2f}")
        
        return order_blocks
    
    def detect_smt(self, spy_candles: List[Candle], qqq_candles: List[Candle], 
                   lookback: int = 10) -> Optional[ICTPattern]:
        """
        Détecte SMT divergence entre SPY et QQQ
        
        Critères:
        - SMT Bearish: QQQ fait nouveau high, SPY ne confirme pas
        - SMT Bullish: QQQ fait nouveau low, SPY ne confirme pas
        """
        if len(spy_candles) < lookback + 10 or len(qqq_candles) < lookback + 10:
            return None
        
        # Récents highs/lows (lookback dernières bougies)
        spy_recent = spy_candles[-lookback:]
        qqq_recent = qqq_candles[-lookback:]
        
        spy_high = max(c.high for c in spy_recent)
        spy_low = min(c.low for c in spy_recent)
        qqq_high = max(c.high for c in qqq_recent)
        qqq_low = min(c.low for c in qqq_recent)
        
        # Highs/lows précédents
        spy_prev = spy_candles[-lookback-10:-lookback]
        qqq_prev = qqq_candles[-lookback-10:-lookback]
        
        spy_prev_high = max(c.high for c in spy_prev)
        spy_prev_low = min(c.low for c in spy_prev)
        qqq_prev_high = max(c.high for c in qqq_prev)
        qqq_prev_low = min(c.low for c in qqq_prev)
        
        # SMT Bearish: QQQ higher high, SPY lower high
        if qqq_high > qqq_prev_high and spy_high < spy_prev_high:
            divergence_strength = abs((qqq_high/qqq_prev_high - 1) - (spy_high/spy_prev_high - 1))
            
            logger.info(f"SMT Bearish detected: QQQ HH {qqq_high:.2f} > {qqq_prev_high:.2f}, "
                       f"SPY fails {spy_high:.2f} < {spy_prev_high:.2f}")
            
            return ICTPattern(
                symbol='SPY/QQQ',
                timeframe='comparison',
                pattern_type='smt',
                direction='bearish',
                details={
                    'qqq_high': qqq_high,
                    'qqq_prev_high': qqq_prev_high,
                    'spy_high': spy_high,
                    'spy_prev_high': spy_prev_high,
                    'divergence_type': 'QQQ makes HH, SPY fails',
                    'strength': divergence_strength
                },
                confidence=min(0.85 + divergence_strength * 5, 0.95)
            )
        
        # SMT Bullish: QQQ lower low, SPY higher low
        if qqq_low < qqq_prev_low and spy_low > spy_prev_low:
            divergence_strength = abs((qqq_low/qqq_prev_low - 1) - (spy_low/spy_prev_low - 1))
            
            logger.info(f"SMT Bullish detected: QQQ LL {qqq_low:.2f} < {qqq_prev_low:.2f}, "
                       f"SPY holds {spy_low:.2f} > {spy_prev_low:.2f}")
            
            return ICTPattern(
                symbol='SPY/QQQ',
                timeframe='comparison',
                pattern_type='smt',
                direction='bullish',
                details={
                    'qqq_low': qqq_low,
                    'qqq_prev_low': qqq_prev_low,
                    'spy_low': spy_low,
                    'spy_prev_low': spy_prev_low,
                    'divergence_type': 'QQQ makes LL, SPY holds',
                    'strength': divergence_strength
                },
                confidence=min(0.85 + divergence_strength * 5, 0.95)
            )
        
        return None
    
    def detect_choch(self, candles: List[Candle], recent_sweep: Optional[Dict[str, Any]]) -> Optional[ICTPattern]:
        """
        Détecte Change of Character (CHOCH)
        
        Critères:
        - Un sweep récent s'est produit
        - BOS dans direction opposée au sweep
        """
        if not recent_sweep:
            return None
        
        # Détecter BOS
        bos_list = self.detect_bos(candles, timeframe='5m')
        
        if not bos_list:
            return None
        
        for bos in bos_list:
            sweep_type = recent_sweep.get('sweep_type')
            
            # Sweep high → CHOCH bearish
            if sweep_type == 'high_sweep' and bos.direction == 'bearish':
                logger.info("CHOCH Bearish detected: high sweep followed by bearish BOS")
                
                return ICTPattern(
                    symbol=bos.symbol,
                    timeframe=bos.timeframe,
                    pattern_type='choch',
                    direction='bearish',
                    details={
                        'sweep_level': recent_sweep['level'].price,
                        'sweep_type': sweep_type,
                        'bos_level': bos.details.get('pivot_low_broken'),
                        'character_change': 'bullish_to_bearish'
                    },
                    confidence=0.9
                )
            
            # Sweep low → CHOCH bullish
            if sweep_type == 'low_sweep' and bos.direction == 'bullish':
                logger.info("CHOCH Bullish detected: low sweep followed by bullish BOS")
                
                return ICTPattern(
                    symbol=bos.symbol,
                    timeframe=bos.timeframe,
                    pattern_type='choch',
                    direction='bullish',
                    details={
                        'sweep_level': recent_sweep['level'].price,
                        'sweep_type': sweep_type,
                        'bos_level': bos.details.get('pivot_high_broken'),
                        'character_change': 'bearish_to_bullish'
                    },
                    confidence=0.9
                )
        
        return None
