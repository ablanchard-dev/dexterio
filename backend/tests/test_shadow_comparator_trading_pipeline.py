from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from models.market_data import Candle, MarketState
from models.setup import PatternDetection, PlaybookMatch, Setup


def _candle(symbol: str, timeframe: str, ts: datetime, px: float) -> Candle:
    return Candle(symbol=symbol, timeframe=timeframe, timestamp=ts, open=px, high=px, low=px, close=px, volume=1)


def _legacy_setup(symbol: str, ts: datetime) -> Setup:
    return Setup(
        id="legacy_setup_id",
        timestamp=ts,
        symbol=symbol,
        quality="A",
        final_score=0.9,
        trade_type="SCALP",
        direction="LONG",
        entry_price=100.0,
        stop_loss=99.0,
        take_profit_1=102.0,
        risk_reward=2.0,
        market_bias="bullish",
        session="ny",
        confluences_count=2,
        playbook_matches=[],
        notes="legacy",
    )


def _v2_setup_blocked(symbol: str, ts: datetime) -> Setup:
    return Setup(
        id="v2_setup_id",
        timestamp=ts,
        symbol=symbol,
        quality="A",
        final_score=0.95,
        trade_type="SCALP",
        direction="LONG",
        entry_price=100.0,
        stop_loss=99.0,
        take_profit_1=102.0,
        risk_reward=2.0,
        market_bias="bullish",
        session="ny",
        confluences_count=2,
        playbook_matches=[PlaybookMatch(playbook_name="London_Sweep")],  # not in allowlist
        notes="v2",
    )


def test_shadow_mode_does_not_change_legacy_output_and_writes_artefact(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Proof:
    - Enabling `use_v2_shadow` does not change the setups returned by TradingPipeline.
    - A comparison artefact is written (under a patched results_path).
    """
    from engines.pipeline import TradingPipeline
    import engines.pipeline as pipeline_mod
    import utils.shadow_comparator as shadow_mod
    from config.settings import settings

    # Ensure the legacy filtering path is deterministic.
    monkeypatch.setattr(settings, "TRADING_MODE", "AGGRESSIVE", raising=False)

    # Redirect comparison artefacts to tmp.
    def fake_results_path(*parts: str) -> Path:
        p = tmp_path / "results" / Path(*parts)
        return p

    monkeypatch.setattr(shadow_mod, "results_path", fake_results_path)

    # Disable pattern detection complexity.
    monkeypatch.setattr(pipeline_mod, "detect_custom_patterns", lambda candles, tf: {})
    monkeypatch.setattr(pipeline_mod, "detect_smt_pattern", lambda spy_h1, qqq_h1: [])
    monkeypatch.setattr(pipeline_mod, "detect_choch_pattern", lambda recent_5m, sweep: [])

    pipe = TradingPipeline()

    ts = datetime(2025, 11, 3, 14, 30, tzinfo=timezone.utc)

    # Stub engines to avoid touching live data.
    pipe.data_feed.get_multi_timeframe_data = lambda symbol: {
        "5m": [_candle(symbol, "5m", ts, 100.0), _candle(symbol, "5m", ts, 100.0)],
        "15m": [_candle(symbol, "15m", ts, 100.0), _candle(symbol, "15m", ts, 100.0)],
    }
    pipe.data_feed.get_latest_price = lambda symbol: 100.0
    pipe.market_state_engine.create_market_state = lambda symbol, multi_tf_data, session_ctx: MarketState(
        symbol=symbol,
        bias="bullish",
        session_profile=1,
        current_session="ny",
    )
    pipe.liquidity_engine.identify_liquidity_levels = lambda symbol, multi_tf_data, htf_levels: []
    pipe.liquidity_engine.detect_sweep = lambda symbol, last, prev: []
    pipe.candlestick_engine.detect_patterns = lambda candles, timeframe, sr_levels=None: [
        PatternDetection(
            symbol="SPY",
            timeframe=timeframe,
            pattern_name="engulfing",
            pattern_type="bullish_reversal",
            strength="strong",
            pattern_score=0.9,
        )
    ]
    pipe.playbook_engine.check_all_playbooks = lambda market_state, liquidity_engine, ict_patterns, current_time: []
    pipe.setup_engine.score_setup = lambda *args, **kwargs: _legacy_setup("SPY", ts)
    pipe.setup_engine_v2.generate_setups = lambda *args, **kwargs: [_v2_setup_blocked("SPY", ts)]

    out_no_shadow = pipe.run_full_analysis(symbols=["SPY"], use_v2_shadow=False)
    out_shadow = pipe.run_full_analysis(symbols=["SPY"], use_v2_shadow=True, v2_shadow_label="smoke")

    assert len(out_shadow["SPY"]) == len(out_no_shadow["SPY"]) == 1
    a = out_shadow["SPY"][0].model_dump()
    b = out_no_shadow["SPY"][0].model_dump()
    a.pop("id", None)
    b.pop("id", None)
    assert a == b

    # Artefact written
    debug_dir = fake_results_path("debug", "shadow_compare")
    snapshots = list(debug_dir.glob("shadow_input_snapshot_SPY_*.json"))
    assert snapshots, "expected a shadow input snapshot file"
    files = list(debug_dir.glob("shadow_compare_SPY_*.json"))
    assert files, "expected a shadow comparison artefact file"
    payload = json.loads(files[0].read_text(encoding="utf-8"))
    assert payload["schema_version"] == "ShadowComparatorV0"
    assert payload["symbol"] == "SPY"
    assert payload.get("input_snapshot", {}).get("path")
    assert payload.get("input_snapshot", {}).get("fingerprint_sha256")
    assert payload["legacy"]["best_final"] is not None
    # v2 produced a setup but it should be blocked by canonical policy (allowlist).
    assert payload["v2_shadow"]["best_raw"] is not None
    assert payload["v2_shadow"]["best_final"] is None
    assert payload["v2_shadow"]["policy_best_raw"]["allowed"] is False


def test_shadow_mode_is_non_blocking_when_v2_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Shadow failure must not crash analysis nor change legacy output."""
    from engines.pipeline import TradingPipeline
    import engines.pipeline as pipeline_mod
    import utils.shadow_comparator as shadow_mod
    from config.settings import settings

    monkeypatch.setattr(settings, "TRADING_MODE", "AGGRESSIVE", raising=False)

    def fake_results_path(*parts: str) -> Path:
        p = tmp_path / "results" / Path(*parts)
        return p

    monkeypatch.setattr(shadow_mod, "results_path", fake_results_path)

    monkeypatch.setattr(pipeline_mod, "detect_custom_patterns", lambda candles, tf: {})
    monkeypatch.setattr(pipeline_mod, "detect_smt_pattern", lambda spy_h1, qqq_h1: [])
    monkeypatch.setattr(pipeline_mod, "detect_choch_pattern", lambda recent_5m, sweep: [])

    pipe = TradingPipeline()
    ts = datetime(2025, 11, 3, 14, 30, tzinfo=timezone.utc)

    pipe.data_feed.get_multi_timeframe_data = lambda symbol: {
        "5m": [_candle(symbol, "5m", ts, 100.0), _candle(symbol, "5m", ts, 100.0)],
        "15m": [_candle(symbol, "15m", ts, 100.0), _candle(symbol, "15m", ts, 100.0)],
    }
    pipe.data_feed.get_latest_price = lambda symbol: 100.0
    pipe.market_state_engine.create_market_state = lambda symbol, multi_tf_data, session_ctx: MarketState(
        symbol=symbol,
        bias="bullish",
        session_profile=1,
        current_session="ny",
    )
    pipe.liquidity_engine.identify_liquidity_levels = lambda symbol, multi_tf_data, htf_levels: []
    pipe.liquidity_engine.detect_sweep = lambda symbol, last, prev: []
    pipe.candlestick_engine.detect_patterns = lambda candles, timeframe, sr_levels=None: [
        PatternDetection(
            symbol="SPY",
            timeframe=timeframe,
            pattern_name="engulfing",
            pattern_type="bullish_reversal",
            strength="strong",
            pattern_score=0.9,
        )
    ]
    pipe.playbook_engine.check_all_playbooks = lambda market_state, liquidity_engine, ict_patterns, current_time: []
    pipe.setup_engine.score_setup = lambda *args, **kwargs: _legacy_setup("SPY", ts)

    def boom(*args, **kwargs):
        raise RuntimeError("v2 boom")

    pipe.setup_engine_v2.generate_setups = boom

    out_shadow = pipe.run_full_analysis(symbols=["SPY"], use_v2_shadow=True, v2_shadow_label="boom")
    assert len(out_shadow["SPY"]) == 1

    debug_dir = fake_results_path("debug", "shadow_compare")
    snapshots = list(debug_dir.glob("shadow_input_snapshot_SPY_*.json"))
    assert snapshots, "expected a shadow input snapshot file"
    files = list(debug_dir.glob("shadow_compare_SPY_*.json"))
    assert files, "expected an artefact even if V2 failed"
    payload = json.loads(files[0].read_text(encoding="utf-8"))
    assert payload["v2_shadow"]["error"] is not None


def test_shadow_snapshot_replay_reproduces_comparison(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Proof:
    - Snapshot enables replay without live data/yfinance.
    - Replay produces the same semantic comparison payload (ignoring volatile fields).
    """
    from engines.pipeline import TradingPipeline
    import engines.pipeline as pipeline_mod
    import utils.shadow_comparator as shadow_mod
    from config.settings import settings

    monkeypatch.setattr(settings, "TRADING_MODE", "AGGRESSIVE", raising=False)

    def fake_results_path(*parts: str) -> Path:
        return tmp_path / "results" / Path(*parts)

    monkeypatch.setattr(shadow_mod, "results_path", fake_results_path)

    monkeypatch.setattr(pipeline_mod, "detect_custom_patterns", lambda candles, tf: {})
    monkeypatch.setattr(pipeline_mod, "detect_smt_pattern", lambda spy_h1, qqq_h1: [])
    monkeypatch.setattr(pipeline_mod, "detect_choch_pattern", lambda recent_5m, sweep: [])

    pipe = TradingPipeline()
    ts = datetime(2025, 11, 3, 14, 30, tzinfo=timezone.utc)

    pipe.data_feed.get_multi_timeframe_data = lambda symbol: {
        "5m": [_candle(symbol, "5m", ts, 100.0), _candle(symbol, "5m", ts, 100.0)],
        "15m": [_candle(symbol, "15m", ts, 100.0), _candle(symbol, "15m", ts, 100.0)],
    }
    pipe.data_feed.get_latest_price = lambda symbol: 100.0
    pipe.market_state_engine.create_market_state = lambda symbol, multi_tf_data, session_ctx: MarketState(
        symbol=symbol,
        bias="bullish",
        session_profile=1,
        current_session="ny",
    )
    pipe.liquidity_engine.identify_liquidity_levels = lambda symbol, multi_tf_data, htf_levels: []
    pipe.liquidity_engine.detect_sweep = lambda symbol, last, prev: []
    pipe.candlestick_engine.detect_patterns = lambda candles, timeframe, sr_levels=None: [
        PatternDetection(
            symbol="SPY",
            timeframe=timeframe,
            pattern_name="engulfing",
            pattern_type="bullish_reversal",
            strength="strong",
            pattern_score=0.9,
        )
    ]
    pipe.playbook_engine.check_all_playbooks = lambda market_state, liquidity_engine, ict_patterns, current_time: []

    # Deterministic stubs used both for capture and replay.
    legacy_fn = lambda *args, **kwargs: _legacy_setup("SPY", ts)
    v2_fn = lambda *args, **kwargs: [_v2_setup_blocked("SPY", ts)]
    pipe.setup_engine.score_setup = legacy_fn
    pipe.setup_engine_v2.generate_setups = v2_fn

    _out_shadow = pipe.run_full_analysis(symbols=["SPY"], use_v2_shadow=True, v2_shadow_label="snap")

    debug_dir = fake_results_path("debug", "shadow_compare")
    snapshot_files = sorted(debug_dir.glob("shadow_input_snapshot_SPY_*.json"))
    compare_files = sorted(debug_dir.glob("shadow_compare_SPY_*.json"))
    assert snapshot_files
    assert compare_files

    snapshot = json.loads(snapshot_files[-1].read_text(encoding="utf-8"))
    baseline = json.loads(compare_files[-1].read_text(encoding="utf-8"))

    replay_wr = shadow_mod.replay_shadow_comparison_from_snapshot(
        snapshot,
        legacy_score_setup=legacy_fn,
        v2_generate_setups=v2_fn,
        snapshot_path=snapshot_files[-1],
        label="replay",
        base_dir=debug_dir,
    )

    def normalize(payload: dict) -> dict:
        p = json.loads(json.dumps(payload))
        p.pop("created_at_utc", None)
        p.pop("git_sha", None)
        # Remove volatile ids in summarized setups.
        for side in ("legacy", "v2_shadow"):
            blk = p.get(side, {})
            for key in ("raw", "best_raw", "best_final"):
                if isinstance(blk.get(key), dict):
                    blk[key].pop("id", None)
            for key in ("final_setups", "raw_setups"):
                if isinstance(blk.get(key), list):
                    for row in blk[key]:
                        if isinstance(row, dict):
                            row.pop("id", None)
        return p

    assert normalize(baseline) == normalize(replay_wr.payload)
