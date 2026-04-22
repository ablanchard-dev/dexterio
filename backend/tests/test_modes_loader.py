"""Phase W.4 — modes_loader contract.

The loader sources playbook-mode lists from `backend/knowledge/modes.yml`
with hardcoded fallbacks. These tests lock three invariants:

1. YAML values == post-W.4 module-level constants (risk_engine + phase3b).
2. Missing / malformed YAML does not crash boot (fallback kicks in).
3. Post-W.4 module constants still contain the exact playbooks that
   pre-W.4 literals did — a regression guard.
"""
from __future__ import annotations

import sys
from pathlib import Path


def _backend_dir() -> Path:
    return Path(__file__).parent.parent


sys.path.insert(0, str(_backend_dir()))


# --- Expected values frozen from the pre-W.4 literal definitions.  ---

EXPECTED_ALLOWLIST = [
    "FVG_Fill_V065",
    "Range_FVG_V054",
    "Asia_Sweep_V051",
    "Engulfing_Bar_V056",
    "London_Fakeout_V066",
    "OB_Retest_V004",
    "FVG_Scalp_1m",
    "BOS_Scalp_1m",
    "EMA_Cross_5m",
    "VWAP_Bounce_5m",
    "RSI_MeanRev_5m",
    "News_Fade",
]

EXPECTED_DENYLIST = [
    "London_Sweep_NY_Continuation",
    "BOS_Momentum_Scalp",
    "Power_Hour_Expansion",
    "Lunch_Range_Scalp",
    "Trend_Continuation_FVG_Retest",
    "DAY_Aplus_1_Liquidity_Sweep_OB_Retest",
    "SCALP_Aplus_1_Mini_FVG_Retest_NY_Open",
    "NY_Open_Reversal",
    "ORB_Breakout_5m",
    "Liquidity_Raid_V056",
    "FVG_Fill_Scalp",
    "Session_Open_Scalp",
    "IFVG_5m_Sweep",
    "HTF_Bias_15m_BOS",
    "Morning_Trap_Reversal",
    "Liquidity_Sweep_Scalp",
]

EXPECTED_PHASE3B = {"NY_Open_Reversal", "News_Fade", "Liquidity_Sweep_Scalp", "BOS_Scalp_1m"}


def test_loader_returns_yaml_values():
    from engines import modes_loader

    modes_loader.reset_cache()
    assert modes_loader.get_aggressive_allowlist() == EXPECTED_ALLOWLIST
    assert modes_loader.get_aggressive_denylist() == EXPECTED_DENYLIST
    assert set(modes_loader.get_phase3b_playbooks()) == EXPECTED_PHASE3B


def test_risk_engine_constants_match_expected():
    from engines.risk_engine import AGGRESSIVE_ALLOWLIST, AGGRESSIVE_DENYLIST

    assert AGGRESSIVE_ALLOWLIST == EXPECTED_ALLOWLIST
    assert AGGRESSIVE_DENYLIST == EXPECTED_DENYLIST


def test_phase3b_constant_matches_expected():
    from engines.execution.phase3b_execution import PHASE3B_PLAYBOOKS

    assert isinstance(PHASE3B_PLAYBOOKS, frozenset)
    assert PHASE3B_PLAYBOOKS == frozenset(EXPECTED_PHASE3B)


def test_loader_fallback_when_yaml_missing(monkeypatch, tmp_path):
    """If the YAML path is missing, loader returns fallbacks — no crash."""
    from engines import modes_loader

    fake_path = tmp_path / "does_not_exist.yml"
    monkeypatch.setattr(modes_loader, "_YAML_PATH", fake_path)
    modes_loader.reset_cache()

    # Fallback lists must contain the same playbooks as expected values.
    assert modes_loader.get_aggressive_allowlist() == EXPECTED_ALLOWLIST
    assert modes_loader.get_aggressive_denylist() == EXPECTED_DENYLIST
    assert set(modes_loader.get_phase3b_playbooks()) == EXPECTED_PHASE3B

    modes_loader.reset_cache()  # restore cache for other tests


def test_loader_fallback_when_yaml_malformed(monkeypatch, tmp_path):
    """Malformed YAML (wrong key types) must fall back per-key without crashing."""
    from engines import modes_loader

    bad = tmp_path / "bad.yml"
    # Two keys valid, one malformed (dict instead of list).
    bad.write_text(
        "aggressive_allowlist:\n  - OnlyOne\n"
        "aggressive_denylist: not_a_list\n"
        "phase3b_playbooks:\n  - NY_Open_Reversal\n"
    )
    monkeypatch.setattr(modes_loader, "_YAML_PATH", bad)
    modes_loader.reset_cache()

    # Valid keys parse; the malformed key falls back to default.
    assert modes_loader.get_aggressive_allowlist() == ["OnlyOne"]
    assert modes_loader.get_aggressive_denylist() == EXPECTED_DENYLIST  # fallback
    assert modes_loader.get_phase3b_playbooks() == ["NY_Open_Reversal"]

    modes_loader.reset_cache()
