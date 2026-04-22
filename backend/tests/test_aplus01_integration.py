"""Integration tests for Aplus_01 Family A — YAML loading + driver E2E.

These tests validate the wire-up between:
  - aplus01_full_v1.yml (playbook definition)
  - PlaybookLoader (parses required_signals=[APLUS01@1m] + tp_logic)
  - Aplus01Driver (5m feed + 1m emit)
  - PlaybookEvaluator gate (matches synthetic ICTPattern via type_map)

They do NOT test the full backtest pipeline (handled by S1.3 smoke).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from engines.aplus01_driver import Aplus01Driver
from engines.playbook_loader import PlaybookLoader
from models.market_data import Candle
from models.setup import ICTPattern


REPO_ROOT = Path(__file__).resolve().parents[1]
YAML_PATH = REPO_ROOT / "knowledge" / "campaigns" / "aplus01_full_v1.yml"


def _ts(year=2025, month=11, day=17, hour=14, minute=30, second=0) -> datetime:
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


def _candle_5m(ts: datetime, o: float, h: float, l: float, c: float) -> Candle:
    return Candle(symbol="SPY", timeframe="5m", timestamp=ts,
                  open=o, high=h, low=l, close=c, volume=1000)


def _candle_1m(ts: datetime, o: float, h: float, l: float, c: float) -> Candle:
    return Candle(symbol="SPY", timeframe="1m", timestamp=ts,
                  open=o, high=h, low=l, close=c, volume=200)


# --------------------------------------------------------------------------
# 1. YAML loading
# --------------------------------------------------------------------------

def test_yaml_loads_via_playbook_loader():
    loader = PlaybookLoader(playbooks_path=YAML_PATH)
    assert len(loader.playbooks) == 1
    pb = loader.playbooks[0]
    assert pb.name == "Aplus_01_full_v1"
    assert pb.required_signals == ["APLUS01@1m"]
    assert pb.setup_tf == "1m"


def test_yaml_tp_logic_alpha_pp_schema():
    loader = PlaybookLoader(playbooks_path=YAML_PATH)
    pb = loader.playbooks[0]
    assert getattr(pb, "tp_logic", None) == "liquidity_draw"
    params = getattr(pb, "tp_logic_params", {}) or {}
    assert params.get("draw_type") == "swing_k3"
    assert params.get("pool_selection") == "significant"
    assert params.get("max_rr_ceiling") == 3.0
    assert params.get("min_rr_floor") == 0.5
    assert params.get("reject_on_fallback") is False
    assert params.get("lookback_bars") == 60


def test_yaml_required_signal_resolves_to_aplus01_sequence():
    """Static check: APLUS01@1m must be in playbook_loader's type_map."""
    import inspect
    from engines import playbook_loader as plm
    src = inspect.getsource(plm)
    assert "'APLUS01': 'aplus01_sequence'" in src, \
        "type_map must map APLUS01 → aplus01_sequence (Sprint 1 wire-up)"


# --------------------------------------------------------------------------
# 2. Driver E2E (synthetic 5m + 1m bars → emit)
# --------------------------------------------------------------------------

def _build_sweep_pattern(extreme: float, react_dir: str) -> ICTPattern:
    return ICTPattern(symbol="SPY", timeframe="5m",
                      pattern_type="liquidity_sweep",
                      direction=react_dir,
                      price_level=extreme,
                      details={"sweep_extreme_price": extreme},
                      strength=0.8, confidence=0.8)


def _build_bos_pattern(direction: str) -> ICTPattern:
    return ICTPattern(symbol="SPY", timeframe="5m",
                      pattern_type="bos",
                      direction=direction,
                      price_level=100.0,
                      details={},
                      strength=0.7, confidence=0.7)


def _build_fvg_zone(low: float, high: float, direction: str = "bullish") -> ICTPattern:
    return ICTPattern(symbol="SPY", timeframe="5m",
                      pattern_type="fvg",
                      direction=direction,
                      price_level=(low + high) / 2,
                      details={"zone_low": low, "zone_high": high, "bottom": low, "top": high},
                      strength=0.6, confidence=0.6)


def test_driver_emits_synthetic_pattern_on_full_cascade():
    """Full happy path : 5m sweep_high → 5m bos_bear → 5m bar touches FVG →
    1m bear pressure (BOS break) → driver emits synthetic ICTPattern."""
    drv = Aplus01Driver()

    # Step 1 — 5m sweep_high (react bearish → tracker arms bearish).
    sweep = _build_sweep_pattern(extreme=101.0, react_dir="bearish")
    last_5m_a = _candle_5m(_ts(), 100.5, 101.0, 100.4, 100.6)
    drv.on_5m_close("SPY", _ts(), [last_5m_a],
                    {"liquidity_sweep": [sweep], "bos": [], "fvg": [], "order_block": [],
                     "breaker_block": []})

    # Step 2 — 5m BOS bearish (counter to sweep_dir bullish, advances ARMED→BOS).
    bos = _build_bos_pattern("bearish")
    last_5m_b = _candle_5m(_ts(minute=35), 100.6, 100.7, 100.4, 100.5)
    drv.on_5m_close("SPY", _ts(minute=35), [last_5m_b],
                    {"liquidity_sweep": [], "bos": [bos], "fvg": [], "order_block": [],
                     "breaker_block": []})

    # Step 3 — 5m bar touches FVG zone (advances BOS→TOUCHED).
    fvg = _build_fvg_zone(low=100.4, high=100.8, direction="bearish")
    last_5m_c = _candle_5m(_ts(minute=40), 100.5, 100.6, 100.3, 100.4)
    drv.on_5m_close("SPY", _ts(minute=40), [last_5m_c],
                    {"liquidity_sweep": [], "bos": [], "fvg": [fvg], "order_block": [],
                     "breaker_block": []})

    # Step 4 — 1m bars build bearish pressure: 5 flat then 1 break-down.
    base = 100.0
    flat = [_candle_1m(_ts(minute=41, second=i*10),
                       base, base + 0.05, base - 0.05, base) for i in range(5)]
    break_bar = _candle_1m(_ts(minute=42), 100.0, 100.05, 99.4, 99.5)
    bars_1m = flat + [break_bar]

    emit = None
    for i, b in enumerate(bars_1m):
        emit = drv.on_1m_bar("SPY", b.timestamp, bars_1m[: i + 1])
        if emit is not None:
            break

    assert emit is not None, "driver should emit on bearish pressure post-touch"
    assert isinstance(emit, ICTPattern)
    assert emit.pattern_type == "aplus01_sequence"
    assert emit.direction == "bearish"
    assert emit.timeframe == "1m"
    # price_level must carry the sweep extreme (structural SL anchor).
    assert emit.price_level == 101.0
    # strength=1.0 ensures synthetic dominates other directional ICT signals.
    assert emit.strength == 1.0
    # state_machine_trace + key timestamps populated.
    assert "state_machine_trace" in emit.details
    assert emit.details.get("touched_zone_type") == "fvg"
    assert emit.details.get("entry_price_at_confirm") == 99.5


def test_driver_no_emit_without_full_cascade():
    """Sweep alone (no BOS, no touch, no 1m pressure) → never emits."""
    drv = Aplus01Driver()
    sweep = _build_sweep_pattern(extreme=101.0, react_dir="bearish")
    drv.on_5m_close("SPY", _ts(), [_candle_5m(_ts(), 100.5, 101.0, 100.4, 100.6)],
                    {"liquidity_sweep": [sweep]})

    # 6 flat 1m bars — no pressure, state still ARMED, on_1m_bar inert.
    base = 100.0
    bars_1m = [_candle_1m(_ts(minute=31, second=i*10),
                          base, base + 0.05, base - 0.05, base) for i in range(6)]
    for i in range(6):
        emit = drv.on_1m_bar("SPY", bars_1m[i].timestamp, bars_1m[: i + 1])
        assert emit is None


def test_driver_sweep_direction_inverted_correctly():
    """ICT engine sweep direction is REACTION dir; driver must invert to SWEEP dir."""
    drv = Aplus01Driver()
    # React BULLISH → low was swept → tracker should arm BULLISH (counter-sweep dir).
    sweep = _build_sweep_pattern(extreme=99.0, react_dir="bullish")
    drv.on_5m_close("SPY", _ts(), [_candle_5m(_ts(), 99.5, 100.0, 99.0, 99.6)],
                    {"liquidity_sweep": [sweep]})
    # Tracker armed_direction is "bullish" — feed bullish BOS to advance.
    bos = _build_bos_pattern("bullish")
    drv.on_5m_close("SPY", _ts(minute=35), [_candle_5m(_ts(minute=35), 99.6, 99.8, 99.5, 99.7)],
                    {"bos": [bos]})
    # If inversion was wrong, BOS would not advance; check internal state.
    from engines.features.aplus01_tracker import STATE_BOS
    assert drv.tracker.get_state("SPY") == STATE_BOS
