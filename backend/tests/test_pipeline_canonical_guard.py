"""
Test P0 — Canonical ALLOWLIST/DENYLIST guard in TradingPipeline.run_full_analysis.

Validates that the guard added at step 8b of run_full_analysis correctly blocks
setups whose playbook_matches contain playbook names that are not in the canonical
AGGRESSIVE_ALLOWLIST (or are explicitly in AGGRESSIVE_DENYLIST).

Does NOT instantiate TradingPipeline (which requires live DataFeedEngine/yfinance).
Tests the guard logic directly using RiskEngine and mock Setup objects.
"""
import pytest
from unittest.mock import MagicMock
from models.setup import Setup, PlaybookMatch
from engines.risk_engine import RiskEngine, AGGRESSIVE_ALLOWLIST, AGGRESSIVE_DENYLIST


def _make_setup(playbook_names: list[str]) -> Setup:
    """Create a minimal Setup with the given playbook_matches."""
    matches = [PlaybookMatch(playbook_name=n) for n in playbook_names]
    return Setup(
        symbol="SPY",
        quality="A",
        final_score=0.8,
        trade_type="SCALP",
        direction="LONG",
        entry_price=500.0,
        stop_loss=497.5,
        take_profit_1=505.0,
        risk_reward=2.0,
        market_bias="bullish",
        session="ny",
        playbook_matches=matches,
    )


def _apply_canonical_guard(setups: list[Setup], risk_engine: RiskEngine, symbol: str = "SPY") -> tuple[list[Setup], list[str]]:
    """
    Reproduce the canonical guard added to pipeline.py step 8b.
    Returns (accepted_setups, blocked_reasons).
    """
    accepted = []
    blocked_reasons = []
    for s in setups:
        rejected = False
        for m in s.playbook_matches:
            allowed, reason = risk_engine.is_playbook_allowed(m.playbook_name)
            if not allowed:
                blocked_reasons.append(f"{m.playbook_name}: {reason}")
                rejected = True
                break
        if not rejected:
            accepted.append(s)
    return accepted, blocked_reasons


@pytest.fixture
def risk_engine_aggressive():
    """RiskEngine in AGGRESSIVE mode (default initial_capital)."""
    engine = RiskEngine(initial_capital=50000.0)
    # Ensure AGGRESSIVE mode
    engine.state.trading_mode = "AGGRESSIVE"
    return engine


class TestCanonicalGuardDenylist:
    """Guard blocks setups with explicitly DENYLIST playbooks."""

    def test_london_sweep_ny_continuation_blocked(self, risk_engine_aggressive):
        """London_Sweep_NY_Continuation (-326R) must be blocked."""
        assert "London_Sweep_NY_Continuation" in AGGRESSIVE_DENYLIST
        setup = _make_setup(["London_Sweep_NY_Continuation"])
        accepted, blocked = _apply_canonical_guard([setup], risk_engine_aggressive)
        assert len(accepted) == 0
        assert any("London_Sweep_NY_Continuation" in r for r in blocked)

    def test_bos_momentum_scalp_blocked(self, risk_engine_aggressive):
        """BOS_Momentum_Scalp (-142R) must be blocked."""
        assert "BOS_Momentum_Scalp" in AGGRESSIVE_DENYLIST
        setup = _make_setup(["BOS_Momentum_Scalp"])
        accepted, blocked = _apply_canonical_guard([setup], risk_engine_aggressive)
        assert len(accepted) == 0

    def test_trend_continuation_fvg_retest_blocked(self, risk_engine_aggressive):
        """Trend_Continuation_FVG_Retest (-22R) must be blocked."""
        assert "Trend_Continuation_FVG_Retest" in AGGRESSIVE_DENYLIST
        setup = _make_setup(["Trend_Continuation_FVG_Retest"])
        accepted, blocked = _apply_canonical_guard([setup], risk_engine_aggressive)
        assert len(accepted) == 0


class TestCanonicalGuardNotInAllowlist:
    """Guard blocks legacy playbook names not present in AGGRESSIVE_ALLOWLIST."""

    def test_london_sweep_legacy_name_blocked(self, risk_engine_aggressive):
        """
        Legacy PlaybookEngine uses 'London_Sweep' (not 'London_Sweep_NY_Continuation').
        'London_Sweep' is NOT in AGGRESSIVE_ALLOWLIST → must be blocked.
        This proves the guard catches the legacy name even if DENYLIST name differs.
        """
        assert "London_Sweep" not in AGGRESSIVE_ALLOWLIST
        assert "London_Sweep" not in AGGRESSIVE_DENYLIST  # not explicitly denied...
        # ...but still blocked by ALLOWLIST enforcement
        setup = _make_setup(["London_Sweep"])
        accepted, blocked = _apply_canonical_guard([setup], risk_engine_aggressive)
        assert len(accepted) == 0, (
            "London_Sweep (legacy name) must be blocked — not in AGGRESSIVE_ALLOWLIST"
        )

    def test_trend_continuation_pullback_legacy_blocked(self, risk_engine_aggressive):
        """Legacy PlaybookEngine 'Trend_Continuation_Pullback' not in ALLOWLIST → blocked."""
        assert "Trend_Continuation_Pullback" not in AGGRESSIVE_ALLOWLIST
        setup = _make_setup(["Trend_Continuation_Pullback"])
        accepted, blocked = _apply_canonical_guard([setup], risk_engine_aggressive)
        assert len(accepted) == 0

    def test_ict_manipulation_reversal_blocked(self, risk_engine_aggressive):
        """Legacy PlaybookEngine 'ICT_Manipulation_Reversal' not in ALLOWLIST → blocked."""
        assert "ICT_Manipulation_Reversal" not in AGGRESSIVE_ALLOWLIST
        setup = _make_setup(["ICT_Manipulation_Reversal"])
        accepted, blocked = _apply_canonical_guard([setup], risk_engine_aggressive)
        assert len(accepted) == 0


class TestCanonicalGuardAllowlist:
    """Guard passes setups whose playbook is in AGGRESSIVE_ALLOWLIST."""

    def test_ny_open_reversal_passes(self, risk_engine_aggressive):
        """NY_Open_Reversal is in ALLOWLIST → must NOT be blocked."""
        assert "NY_Open_Reversal" in AGGRESSIVE_ALLOWLIST
        setup = _make_setup(["NY_Open_Reversal"])
        accepted, blocked = _apply_canonical_guard([setup], risk_engine_aggressive)
        assert len(accepted) == 1
        assert len(blocked) == 0

    def test_fvg_fill_v065_passes(self, risk_engine_aggressive):
        """FVG_Fill_V065 (faithful MASTER) is in ALLOWLIST → must NOT be blocked."""
        assert "FVG_Fill_V065" in AGGRESSIVE_ALLOWLIST
        setup = _make_setup(["FVG_Fill_V065"])
        accepted, blocked = _apply_canonical_guard([setup], risk_engine_aggressive)
        assert len(accepted) == 1
        assert len(blocked) == 0

    def test_no_playbook_matches_passes(self, risk_engine_aggressive):
        """Setup with no playbook_matches has no policy constraint → passes."""
        setup = _make_setup([])
        accepted, blocked = _apply_canonical_guard([setup], risk_engine_aggressive)
        assert len(accepted) == 1
        assert len(blocked) == 0


class TestCanonicalGuardMixed:
    """Guard behavior on mixed/multiple setups."""

    def test_mixed_batch_filters_correctly(self, risk_engine_aggressive):
        """Batch: NY_Open (pass) + London_Sweep (block) → only NY_Open survives."""
        setups = [
            _make_setup(["NY_Open_Reversal"]),
            _make_setup(["London_Sweep"]),
            _make_setup(["London_Sweep_NY_Continuation"]),
        ]
        accepted, blocked = _apply_canonical_guard(setups, risk_engine_aggressive)
        assert len(accepted) == 1
        assert accepted[0].playbook_matches[0].playbook_name == "NY_Open_Reversal"
        assert len(blocked) == 2

    def test_setup_with_blocked_match_among_multiple(self, risk_engine_aggressive):
        """Setup with one allowed + one blocked match → blocked (ANY disallowed = reject)."""
        setup = _make_setup(["NY_Open_Reversal", "London_Sweep_NY_Continuation"])
        accepted, blocked = _apply_canonical_guard([setup], risk_engine_aggressive)
        assert len(accepted) == 0, (
            "Setup with any blocked match must be rejected regardless of other matches"
        )
