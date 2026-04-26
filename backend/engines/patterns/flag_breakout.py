"""Flag breakout pattern — Plan v4.0 Priorité #1 J4 (post-TSMOM ARCHIVED).

Hypothèse : impulsion directionnelle nette → consolidation flag courte (3-5 bars)
→ breakout dans le sens impulsion confirmé par volume → continuation 1R.

Logique :
  1. Scan window : look back N bars depuis current
  2. Impulsion candidat : bar avec body > impulse_atr_mult × ATR(14)
  3. Flag : 3-5 bars suivants, total range < flag_max_range_ratio × impulse range
  4. Breakout : current close > max(flag highs) si bullish (mirror SHORT)
  5. Volume gate : current volume > vol_mult × avg(last vol_lookback bars)
  6. SL = swing opposite à impulsion + padding ATR

Différence vs ORB / BOS / IFVG existants :
  - ORB = opening range 9:30+15min static. Flag = patterns intraday récurrents
  - BOS = simple structure break. Flag = impulsion + pause + breakout (séquence)
  - IFVG = liquidity void retest. Flag = directional momentum continuation

Output : ICTPattern(pattern_type='flag_breakout', direction, price_level=SL,
         details={impulse_size, n_flag_bars, flag_range, vol_ratio, target_1r})
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from models.market_data import Candle
from models.setup import ICTPattern


def _atr(candles: List[Candle], period: int = 14) -> Optional[float]:
    """Simple ATR (true range mean) on last `period` bars."""
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(len(candles) - period, len(candles)):
        c = candles[i]
        prev_close = candles[i - 1].close
        tr = max(
            c.high - c.low,
            abs(c.high - prev_close),
            abs(c.low - prev_close),
        )
        trs.append(tr)
    if not trs:
        return None
    return sum(trs) / len(trs)


def detect_flag_breakout(
    candles: List[Candle],
    timeframe: str,
    config: Optional[Dict[str, Any]] = None,
) -> List[ICTPattern]:
    """Detect flag breakout pattern on the most recent candle.

    Stateless detector : looks back N bars from current to find
    impulsion + flag + breakout sequence ending on current bar.
    """
    cfg = config or {}
    atr_period = int(cfg.get("atr_period", 14))
    impulse_atr_mult = float(cfg.get("impulse_atr_mult", 1.5))
    flag_min_bars = int(cfg.get("flag_min_bars", 3))
    flag_max_bars = int(cfg.get("flag_max_bars", 5))
    # flag_max_range_ratio recalibration structurelle 2026-04-25 (one-shot,
    # non-outcome-based) : valeur initiale 0.6 venait de la littérature
    # chartiste classique manuelle (Edwards & Magee, Bulkowski). Sur SPY 5m
    # intraday HFT moderne, distribution réelle observée (1 semaine nov_w4,
    # 30 impulsions ≥1.5×ATR) : p10=0.76 / p50=1.03 / p90=1.30. 0% des cas
    # sont < 0.6. Recalibration à 1.0 = sous-médiane (encore conservateur :
    # exige flag plus tight que la moyenne) sans regarder aucune métrique
    # outcome (E[R], Sharpe). Distinction p-hacking : calibration basée sur
    # microstructure marché observée, pas sur performance signal.
    flag_max_range_ratio = float(cfg.get("flag_max_range_ratio", 1.0))
    vol_mult = float(cfg.get("vol_mult", 1.2))
    vol_lookback = int(cfg.get("vol_lookback", 20))
    sl_padding_atr_mult = float(cfg.get("sl_padding_atr_mult", 0.3))

    n = len(candles)
    min_required = atr_period + flag_max_bars + 2 + vol_lookback
    if n < min_required:
        return []

    last = candles[-1]
    atr = _atr(candles[:-1], period=atr_period)
    if atr is None or atr <= 0:
        return []

    # Volume average (excluding current)
    vol_window = [c.volume for c in candles[-(vol_lookback + 1):-1] if c.volume > 0]
    if len(vol_window) < vol_lookback // 2:
        return []  # insufficient volume data
    avg_vol = sum(vol_window) / len(vol_window)
    if avg_vol <= 0:
        return []

    results: List[ICTPattern] = []

    # Scan : impulsion candidate at position i ∈ [-(flag_max_bars+2), -(flag_min_bars+1)]
    # current = last (-1), flag spans (i+1, i+2, ..., -2)
    for n_flag in range(flag_min_bars, flag_max_bars + 1):
        impulse_idx = -(n_flag + 2)  # flag has n_flag bars between impulse and current
        if abs(impulse_idx) > n:
            continue
        impulse_bar = candles[impulse_idx]
        impulse_body = abs(impulse_bar.close - impulse_bar.open)
        if impulse_body < impulse_atr_mult * atr:
            continue

        flag_bars = candles[impulse_idx + 1:-1]
        if len(flag_bars) != n_flag:
            continue

        flag_high = max(c.high for c in flag_bars)
        flag_low = min(c.low for c in flag_bars)
        flag_range = flag_high - flag_low
        impulse_range = impulse_bar.high - impulse_bar.low
        if impulse_range <= 0:
            continue
        if flag_range > flag_max_range_ratio * impulse_range:
            continue

        # Determine direction from impulsion bar
        is_bull_impulse = impulse_bar.close > impulse_bar.open
        is_bear_impulse = impulse_bar.close < impulse_bar.open
        if not (is_bull_impulse or is_bear_impulse):
            continue

        # Volume gate
        if last.volume <= 0:
            continue
        vol_ratio = last.volume / avg_vol
        if vol_ratio < vol_mult:
            continue

        if is_bull_impulse and last.close > flag_high:
            # Bullish flag breakout
            sl = flag_low - sl_padding_atr_mult * atr
            entry = last.close
            risk = entry - sl
            if risk <= 0:
                continue
            target_1r = entry + risk
            strength = min(1.0, (last.close - flag_high) / (flag_range + 1e-9))
            results.append(ICTPattern(
                symbol=last.symbol,
                timeframe=timeframe,
                timestamp=last.timestamp,
                pattern_type='flag_breakout',
                direction='bullish',
                price_level=sl,
                strength=strength,
                confidence=min(1.0, vol_ratio / vol_mult * 0.5 + strength * 0.5),
                details={
                    'impulse_body_atr_mult': float(impulse_body / atr),
                    'n_flag_bars': n_flag,
                    'flag_range': float(flag_range),
                    'flag_range_ratio': float(flag_range / impulse_range),
                    'vol_ratio': float(vol_ratio),
                    'entry': float(entry),
                    'sl': float(sl),
                    'target_1r': float(target_1r),
                    'flag_high': float(flag_high),
                    'flag_low': float(flag_low),
                },
            ))
            break  # stop at first valid (smaller flag preferred)

        if is_bear_impulse and last.close < flag_low:
            # Bearish flag breakout (mirror)
            sl = flag_high + sl_padding_atr_mult * atr
            entry = last.close
            risk = sl - entry
            if risk <= 0:
                continue
            target_1r = entry - risk
            strength = min(1.0, (flag_low - last.close) / (flag_range + 1e-9))
            results.append(ICTPattern(
                symbol=last.symbol,
                timeframe=timeframe,
                timestamp=last.timestamp,
                pattern_type='flag_breakout',
                direction='bearish',
                price_level=sl,
                strength=strength,
                confidence=min(1.0, vol_ratio / vol_mult * 0.5 + strength * 0.5),
                details={
                    'impulse_body_atr_mult': float(impulse_body / atr),
                    'n_flag_bars': n_flag,
                    'flag_range': float(flag_range),
                    'flag_range_ratio': float(flag_range / impulse_range),
                    'vol_ratio': float(vol_ratio),
                    'entry': float(entry),
                    'sl': float(sl),
                    'target_1r': float(target_1r),
                    'flag_high': float(flag_high),
                    'flag_low': float(flag_low),
                },
            ))
            break

    return results
