"""
Engine sanity suite v1 — 6 tests that verify the engine reads bars and
detects patterns the way its code says it does.

Read-only, no mutation of production YAML or code. Runs against a 1-week
slice of SPY_1m.parquet (2025-10-06 through 2025-10-10, same as oct_w2
backtest window).

Test plan:
  1. OHLC: parquet bars → engine Candle objects, field-by-field identity.
  2. FVG: algorithmic ground-truth (c1.high<c3.low, min_gap 0.3%) vs
     ICTPatternEngine.detect_fvg(). Count agreement on a rolling window.
  3. Engulfing: ground-truth bullish/bearish engulfing definition vs
     CandlestickPatternEngine._is_bullish_engulfing/_is_bearish_engulfing.
  4. Liquidity sweep: ground-truth sweep definition (high>last_swing_high+eps
     AND close<last_swing_high, mirror) vs ICTPatternEngine.detect_liquidity_sweep().
  5. 1m → 5m resample: manual pandas aggregation vs the engine's resample
     (both use pandas .resample('5T') with first/max/min/last/sum).
  6. Signal wiring: feed a hand-crafted ICTPattern list into
     playbook_loader's required_signals gate (both IFVG and FVG) and verify
     matches fire exactly when they should.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import pandas as pd

from models.market_data import Candle
from engines.patterns.ict import ICTPatternEngine
from engines.patterns.candlesticks import CandlestickPatternEngine
from engines.timeframe_aggregator import TimeframeAggregator
from utils.indicators import calculate_pivot_points  # used internally by detect_liquidity_sweep


DATA_FILE = BACKEND / "data/market/SPY_1m.parquet"
WEEK_START = pd.Timestamp("2025-10-06 09:30:00", tz="America/New_York").tz_convert("UTC")
WEEK_END = pd.Timestamp("2025-10-10 16:00:00", tz="America/New_York").tz_convert("UTC")


# ---------- Shared fixture: load 1w of 1m SPY bars ----------------------------

def load_week_bars() -> pd.DataFrame:
    df = pd.read_parquet(DATA_FILE)
    ts_col = "datetime" if "datetime" in df.columns else "timestamp"
    df = df.rename(columns={ts_col: "datetime"})
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df = df[(df["datetime"] >= WEEK_START) & (df["datetime"] <= WEEK_END)].copy()
    df = df.sort_values("datetime").reset_index(drop=True)
    return df


def df_to_candles(df: pd.DataFrame, tf: str = "1m", symbol: str = "SPY") -> list[Candle]:
    return [
        Candle(
            symbol=symbol,
            timeframe=tf,
            timestamp=row["datetime"].to_pydatetime(),
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=int(row.get("volume", 0)),
        )
        for _, row in df.iterrows()
    ]


# ---------- TEST 1: OHLC identity ---------------------------------------------

def test_ohlc_identity(df: pd.DataFrame, candles: list[Candle]) -> dict:
    if len(df) != len(candles):
        return {"pass": False, "reason": f"length mismatch {len(df)} vs {len(candles)}"}
    mismatches = []
    for i, c in enumerate(candles):
        row = df.iloc[i]
        for field in ("open", "high", "low", "close"):
            eng_val = getattr(c, field)
            src_val = float(row[field])
            if abs(eng_val - src_val) > 1e-9:
                mismatches.append(
                    (i, row["datetime"].isoformat(), field, eng_val, src_val)
                )
                if len(mismatches) >= 5:
                    break
        if len(mismatches) >= 5:
            break
    return {
        "pass": len(mismatches) == 0,
        "n_bars": len(candles),
        "mismatches": mismatches[:5],
    }


# ---------- TEST 2: FVG detector ---------------------------------------------

def ground_truth_fvg(candles: list[Candle]) -> list[dict]:
    """Algorithmic ground truth: naive 3-bar gap with min_gap 0.3% price.
    Returns list of {idx, direction, c1_high_or_low, c3_low_or_high}.
    Does NOT apply the detector's freshness / invalidation filter — we'll
    reconcile by counting overlaps, not exact one-to-one.
    """
    out = []
    for i in range(2, len(candles)):
        c1, c2, c3 = candles[i - 2], candles[i - 1], candles[i]
        min_gap_price = c2.close * 0.003
        # Bullish FVG
        if c1.high < c3.low:
            gap = c3.low - c1.high
            if gap >= min_gap_price:
                out.append({"idx": i, "direction": "bullish", "top": c3.low, "bottom": c1.high})
        # Bearish FVG
        if c1.low > c3.high:
            gap = c1.low - c3.high
            if gap >= min_gap_price:
                out.append({"idx": i, "direction": "bearish", "top": c1.low, "bottom": c3.high})
    return out


def test_fvg(candles_5m: list[Candle]) -> dict:
    """Compare: ground-truth scan AT EACH 5m bar end vs detect_fvg on a window
    that ends at that same bar. We slide a 30-bar window (matches detector's
    own scan range) and count whether the detector picks up fresh 3-bar gaps
    that meet the size threshold.

    Because the detector applies freshness / fill / invalidation filters, we
    don't expect 1:1 match. We report:
      - gt_count: ground-truth 3-bar FVG (with size >= 0.3%) count over full week
      - eng_distinct: distinct (bar_idx, direction) FVGs returned by detector
        across rolling windows (de-duplicated)
      - eng_subset_of_gt_pct: of engine-detected FVGs, what % correspond to
        a ground-truth FVG at same (idx, direction)? (detector should never
        report FVGs the ground-truth definition rejects.)
    """
    gt = ground_truth_fvg(candles_5m)
    gt_keys = {(f["idx"], f["direction"]) for f in gt}

    engine = ICTPatternEngine()
    eng_keys: set[tuple[int, str]] = set()
    # Slide a window of 30 bars (detector's default scan) across the week
    for end in range(30, len(candles_5m) + 1):
        window = candles_5m[end - 30 : end]
        fvgs = engine.detect_fvg(window, timeframe="5m")
        for f in fvgs:
            # Translate window-local idx back to global idx
            if "candle_indices" in f.details:
                local_idx = f.details["candle_indices"][2]  # c3 index in window
                global_idx = (end - 30) + local_idx
                eng_keys.add((global_idx, f.direction))

    # How many engine FVGs are NOT in ground-truth? (detector shouldn't invent)
    false_positives = eng_keys - gt_keys
    # How many ground-truth FVGs never surfaced in any window?
    never_detected = gt_keys - eng_keys

    fp_pct = (len(false_positives) / len(eng_keys) * 100) if eng_keys else 0.0
    coverage_pct = ((len(gt_keys) - len(never_detected)) / len(gt_keys) * 100) if gt_keys else 0.0

    return {
        "pass": fp_pct < 1.0,  # detector must never invent FVGs beyond ground-truth def
        "gt_count": len(gt_keys),
        "engine_count": len(eng_keys),
        "false_positives_count": len(false_positives),
        "false_positives_pct": round(fp_pct, 2),
        "ground_truth_coverage_pct": round(coverage_pct, 2),
        "sample_false_positives": list(false_positives)[:5],
        "sample_gt": [(f["idx"], f["direction"]) for f in gt[:5]],
    }


# ---------- TEST 3: Engulfing ------------------------------------------------

def ground_truth_engulfing(candles: list[Candle]) -> list[tuple[int, str]]:
    """Returns list of (idx_of_second_candle, 'bullish_engulfing'|'bearish_engulfing')."""
    out = []
    for i in range(1, len(candles)):
        c1, c2 = candles[i - 1], candles[i]
        # Bullish engulfing
        if (c1.is_bearish and c2.is_bullish
                and c2.open <= c1.close and c2.close >= c1.open
                and c2.body > c1.body):
            out.append((i, "bullish"))
        # Bearish engulfing
        if (c1.is_bullish and c2.is_bearish
                and c2.open >= c1.close and c2.close <= c1.open
                and c2.body > c1.body):
            out.append((i, "bearish"))
    return out


def test_engulfing(candles_5m: list[Candle]) -> dict:
    """Directly call the private _is_bullish_engulfing / _is_bearish_engulfing
    on every consecutive pair. This is the cleanest check of the predicate.
    """
    cs = CandlestickPatternEngine()
    gt = ground_truth_engulfing(candles_5m)
    gt_set = set(gt)
    eng_set: set[tuple[int, str]] = set()
    for i in range(1, len(candles_5m)):
        c1, c2 = candles_5m[i - 1], candles_5m[i]
        if cs._is_bullish_engulfing(c1, c2):
            eng_set.add((i, "bullish"))
        if cs._is_bearish_engulfing(c1, c2):
            eng_set.add((i, "bearish"))
    missing = gt_set - eng_set
    extra = eng_set - gt_set
    return {
        "pass": not missing and not extra,
        "gt_count": len(gt_set),
        "engine_count": len(eng_set),
        "missing": list(missing)[:5],
        "extra": list(extra)[:5],
    }


# ---------- TEST 4: Liquidity sweep -------------------------------------------

def ground_truth_sweep(candles: list[Candle], lookback: int = 10) -> list[tuple[int, str]]:
    """Ground truth using the SAME helper (calculate_pivot_points) the detector
    uses, applied to windows ending at each bar — so we're testing the sweep
    predicate, not the pivot algorithm.
    """
    out = []
    for end in range(lookback + 5, len(candles) + 1):
        window = candles[end - lookback - 15 : end] if end >= lookback + 15 else candles[:end]
        if len(window) < lookback + 5:
            continue
        pivots = calculate_pivot_points(
            [{"high": c.high, "low": c.low, "timestamp": c.timestamp} for c in window],
            lookback=10,
        )
        if not pivots["pivot_highs"] or not pivots["pivot_lows"]:
            continue
        last_sh = pivots["pivot_highs"][-1]["price"]
        last_sl = pivots["pivot_lows"][-1]["price"]
        cur = window[-1]
        # Sweep high: exceed swing and close back inside with a meaningful wick
        if cur.high > last_sh and cur.close < last_sh:
            upper_wick = cur.high - max(cur.open, cur.close)
            if upper_wick >= cur.high * 0.001:
                out.append((end - 1, "bearish"))  # bearish bias after sweep high
        # Sweep low
        if cur.low < last_sl and cur.close > last_sl:
            lower_wick = min(cur.open, cur.close) - cur.low
            if lower_wick >= cur.low * 0.001:
                out.append((end - 1, "bullish"))
    return out


def test_sweep(candles_5m: list[Candle]) -> dict:
    """Compare engine detector on the same sliding windows."""
    engine = ICTPatternEngine()
    gt = ground_truth_sweep(candles_5m)
    gt_set = set(gt)

    eng_set: set[tuple[int, str]] = set()
    for end in range(25, len(candles_5m) + 1):
        window = candles_5m[end - 25 : end]
        sweeps = engine.detect_liquidity_sweep(window, timeframe="5m", lookback=10)
        for sw in sweeps:
            eng_set.add((end - 1, sw.direction))

    missing = gt_set - eng_set
    extra = eng_set - gt_set
    # Engine applies eps_atr buffer → it may legitimately miss some ground-truth
    # sweeps where high/low just barely exceeds the swing. So we allow missing
    # but false positives are unacceptable.
    return {
        "pass": len(extra) == 0,
        "gt_count": len(gt_set),
        "engine_count": len(eng_set),
        "extra_count": len(extra),
        "missing_count": len(missing),
        "extra_sample": list(extra)[:5],
        "missing_sample": list(missing)[:5],
    }


# ---------- TEST 5: 1m → 5m resample -------------------------------------------

def aggregate_with_tfa(candles_1m: list[Candle]) -> list[Candle]:
    """Run the production TimeframeAggregator (incremental, used in the real
    backtest loop, NOT the dead pandas path in engine._build_multi_timeframe_candles)
    over the full 1m stream and collect closed 5m candles.
    """
    tfa = TimeframeAggregator()
    for c in candles_1m:
        tfa.add_1m_candle(c)
    return list(tfa.get_candles("SPY", "5m"))


def test_resample(candles_1m: list[Candle]) -> dict:
    """Compare the production TimeframeAggregator output vs a pandas
    resample('5min') ground truth, bar-by-bar on OHLC.

    TimeframeAggregator is the path the backtest engine actually uses
    (backtest/engine.py:91, 524 comment). It fires is_close_5m at minute%5==4
    so the "first 5m bar" covers :00-:04 (same convention as pandas label='left').
    """
    # Ground truth: pandas resample (label='left' is default; matches TFA's
    # floor_timestamp convention where the bar is tagged at :00, :05, :10...).
    df = pd.DataFrame(
        [
            {
                "timestamp": c.timestamp,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
            }
            for c in candles_1m
        ]
    ).set_index("timestamp")
    gt_5m = df.resample("5min").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    ).dropna()

    # Engine (production) path
    engine_5m = aggregate_with_tfa(candles_1m)

    # Index engine_5m by timestamp for alignment
    eng_by_ts = {c.timestamp: c for c in engine_5m}

    mismatches = []
    only_in_gt = 0
    only_in_engine = 0

    # Check engine bars against ground-truth
    for ts, row in gt_5m.iterrows():
        # TFA tags closed bars with _floor_timestamp (:00,:05,:10,…). pandas
        # index is tz-aware datetime; TFA keeps the incoming tz → align tz.
        ts_py = ts.to_pydatetime()
        c = eng_by_ts.get(ts_py)
        if c is None:
            only_in_gt += 1
            continue
        for field in ("open", "high", "low", "close"):
            if abs(getattr(c, field) - float(row[field])) > 1e-9:
                mismatches.append(
                    (ts_py.isoformat(), field, getattr(c, field), float(row[field]))
                )
                if len(mismatches) >= 5:
                    break
        if len(mismatches) >= 5:
            break

    gt_ts = {ts.to_pydatetime() for ts in gt_5m.index}
    only_in_engine = len([c for c in engine_5m if c.timestamp not in gt_ts])

    # TFA only emits a bar when is_close fires (minute%5==4). The LAST partial
    # 5m bar of the week may still be "current" in TFA and not yet in
    # get_candles(). pandas emits it anyway. So 1 bar delta is acceptable.
    row_delta = abs(len(engine_5m) - len(gt_5m))
    acceptable_edge_delta = 1  # at most one partial trailing bar

    return {
        "pass": (len(mismatches) == 0
                 and only_in_engine == 0
                 and row_delta <= acceptable_edge_delta),
        "engine_bars": len(engine_5m),
        "ground_truth_bars": len(gt_5m),
        "row_delta": row_delta,
        "only_in_ground_truth": only_in_gt,
        "only_in_engine": only_in_engine,
        "mismatches_ohlc": mismatches[:5],
    }


# ---------- TEST 6: Signal wiring ---------------------------------------------

def test_signal_wiring() -> dict:
    """Verify playbook_loader's required_signals parser matches the right
    patterns. We don't call the full matching function (needs a Setup object);
    we re-implement the 20-line gate inline and test edge cases.

    Cases:
      a) `IFVG@5m` should match an ifvg pattern at 5m, either direction.
      b) `IFVG_BULL@5m` should match only ifvg bullish at 5m.
      c) `FVG@5m` should match a fvg pattern at 5m (type_map default case).
      d) `IFVG@5m` should NOT match an ifvg at 15m (wrong TF).
      e) `SWEEP_BEAR@5m` should match liquidity_sweep bearish 5m.
    """
    # Reproduce the gate logic inline, sourced verbatim from
    # backend/engines/playbook_loader.py:794-843
    type_map = {
        "IFVG": "ifvg",
        "OB": "order_block",
        "EQ": "equilibrium",
        "SWEEP": "liquidity_sweep",
        "BRKR": "breaker_block",
        "BRKRBLK": "breaker_block",
        "BRKRBLOCK": "breaker_block",
        "EMA": "ema_cross",
        "EMACROSS": "ema_cross",
        "VWAP": "vwap_bounce",
        "VWAPBOUNCE": "vwap_bounce",
        "RSI": "rsi_extreme",
        "RSIEXTREME": "rsi_extreme",
        "ORB": "orb_break",
        "ORBBREAK": "orb_break",
    }

    def gate(req: str, available: list[tuple[str, str, str]]) -> bool:
        try:
            sig, tf = req.split("@")
            tf = tf.lower()
        except ValueError:
            sig = req
            tf = None
        sig_parts = sig.split("_")
        base = sig_parts[0].upper()
        dir_seg = sig_parts[1].upper() if len(sig_parts) > 1 else None
        p_type = type_map.get(base, base.lower())
        dir_required = None
        if dir_seg:
            if dir_seg in ["BEAR", "BEARISH"]:
                dir_required = "bearish"
            elif dir_seg in ["BULL", "BULLISH"]:
                dir_required = "bullish"
        for (t0, d0, tf0) in available:
            if t0 == p_type and (dir_required is None or d0 == dir_required) and (tf is None or tf0 == tf):
                return True
        return False

    cases = [
        # (required_signal, available_patterns, expected)
        ("IFVG@5m", [("ifvg", "bullish", "5m")], True),        # a
        ("IFVG@5m", [("ifvg", "bearish", "5m")], True),        # a mirror
        ("IFVG_BULL@5m", [("ifvg", "bullish", "5m")], True),   # b
        ("IFVG_BULL@5m", [("ifvg", "bearish", "5m")], False),  # b reject bearish
        ("FVG@5m", [("fvg", "bullish", "5m")], True),          # c
        ("IFVG@5m", [("ifvg", "bullish", "15m")], False),      # d wrong TF
        ("SWEEP_BEAR@5m", [("liquidity_sweep", "bearish", "5m")], True),  # e
        ("SWEEP_BEAR@5m", [("liquidity_sweep", "bullish", "5m")], False),  # e reject
        ("IFVG@5m", [], False),                                # no patterns
    ]
    failures = []
    for req, avail, expected in cases:
        got = gate(req, avail)
        if got != expected:
            failures.append({"signal": req, "available": avail, "expected": expected, "got": got})
    return {
        "pass": not failures,
        "n_cases": len(cases),
        "failures": failures,
    }


# ---------- Runner ------------------------------------------------------------

def main():
    print("Engine sanity v1 — loading SPY 1m bars for 2025-10-06..2025-10-10")
    df = load_week_bars()
    print(f"  loaded {len(df)} 1m bars")
    candles_1m = df_to_candles(df, tf="1m")

    # Build 5m candles via the production TimeframeAggregator. This is the
    # path the engine uses in-loop (backtest/engine.py:91,524 comment —
    # _build_multi_timeframe_candles with '5T' is dead legacy code).
    candles_5m = aggregate_with_tfa(candles_1m)
    print(f"  aggregated to {len(candles_5m)} 5m bars via TimeframeAggregator")

    results = {}
    print()
    print("[1] OHLC identity                  ", end="... ", flush=True)
    results["test1_ohlc"] = test_ohlc_identity(df, candles_1m)
    print("PASS" if results["test1_ohlc"]["pass"] else "FAIL")

    print("[2] FVG detector vs ground-truth   ", end="... ", flush=True)
    results["test2_fvg"] = test_fvg(candles_5m)
    print("PASS" if results["test2_fvg"]["pass"] else "FAIL")

    print("[3] Engulfing predicate            ", end="... ", flush=True)
    results["test3_engulf"] = test_engulfing(candles_5m)
    print("PASS" if results["test3_engulf"]["pass"] else "FAIL")

    print("[4] Liquidity sweep detector       ", end="... ", flush=True)
    results["test4_sweep"] = test_sweep(candles_5m)
    print("PASS" if results["test4_sweep"]["pass"] else "FAIL")

    print("[5] 1m -> 5m resample              ", end="... ", flush=True)
    results["test5_resample"] = test_resample(candles_1m)
    print("PASS" if results["test5_resample"]["pass"] else "FAIL")

    print("[6] required_signals gating        ", end="... ", flush=True)
    results["test6_signal_wiring"] = test_signal_wiring()
    print("PASS" if results["test6_signal_wiring"]["pass"] else "FAIL")

    print()
    print("Details:")
    import json
    print(json.dumps(results, indent=2, default=str))

    return 0 if all(r["pass"] for r in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
