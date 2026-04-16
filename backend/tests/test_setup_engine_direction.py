"""
Tests for SetupEngine._determine_direction and calculate_playbook_score.

Context: D1+D2 fix — PlaybookMatch had no match_score / direction fields; both
functions crashed (AttributeError) when playbook_matches was non-empty.

These tests confirm:
  - calculate_playbook_score uses confidence (not the non-existent match_score)
  - _determine_direction no longer crashes when playbook_matches is non-empty
  - direction source of truth is ICT BOS, then candlestick (playbook has no direction field)
"""

from datetime import datetime, timezone

import pytest

from models.setup import ICTPattern, PatternDetection, PlaybookMatch
from engines.setup_engine import SetupEngine, calculate_playbook_score

NOW = datetime.now(timezone.utc)


def _bos(direction: str, confidence: float = 0.9) -> ICTPattern:
    return ICTPattern(
        pattern_type="bos",
        direction=direction,
        confidence=confidence,
        timeframe="5m",
        symbol="SPY",
        timestamp=NOW,
    )


def _candle(pattern_type: str, score: float = 0.7) -> PatternDetection:
    return PatternDetection(
        pattern_type=pattern_type,
        pattern_name=pattern_type,
        pattern_score=score,
        strength="medium",
        timeframe="5m",
        symbol="SPY",
        timestamp=NOW,
    )


def _pm(name: str, confidence: float = 0.7) -> PlaybookMatch:
    return PlaybookMatch(playbook_name=name, confidence=confidence)


# ---------------------------------------------------------------------------
# calculate_playbook_score
# ---------------------------------------------------------------------------

class TestCalculatePlaybookScore:
    def test_empty_returns_zero(self):
        assert calculate_playbook_score([]) == 0.0

    def test_single_match_returns_confidence(self):
        assert calculate_playbook_score([_pm("NY_Open_Reversal", 0.65)]) == 0.65

    def test_returns_best_confidence(self):
        pms = [_pm("London_Sweep", 0.4), _pm("NY_Open_Reversal", 0.8)]
        assert calculate_playbook_score(pms) == 0.8

    def test_all_zero_confidence(self):
        pms = [_pm("X", 0.0), _pm("Y", 0.0)]
        assert calculate_playbook_score(pms) == 0.0


# ---------------------------------------------------------------------------
# SetupEngine._determine_direction — D2 fix
# ---------------------------------------------------------------------------

class TestDetermineDirection:
    def setup_method(self):
        self.eng = SetupEngine()

    # --- no crash when playbook_matches present ---

    def test_no_crash_with_playbook_matches_and_bos_bullish(self):
        pms = [_pm("NY_Open_Reversal", 0.8)]
        d = self.eng._determine_direction([_bos("bullish")], [], pms)
        assert d == "LONG"

    def test_no_crash_with_playbook_matches_and_bos_bearish(self):
        pms = [_pm("NY_Open_Reversal", 0.8)]
        d = self.eng._determine_direction([_bos("bearish")], [], pms)
        assert d == "SHORT"

    def test_no_crash_with_playbook_matches_only_no_bos(self):
        # Playbook present but no BOS, no candlestick → no direction source → None
        pms = [_pm("NY_Open_Reversal", 0.8)]
        d = self.eng._determine_direction([], [], pms)
        assert d is None

    # --- direction source priority ---

    def test_bos_bullish_no_playbooks(self):
        d = self.eng._determine_direction([_bos("bullish")], [], [])
        assert d == "LONG"

    def test_bos_bearish_no_playbooks(self):
        d = self.eng._determine_direction([_bos("bearish")], [], [])
        assert d == "SHORT"

    def test_candlestick_bullish_fallback(self):
        d = self.eng._determine_direction([], [_candle("bullish_engulfing")], [])
        assert d == "LONG"

    def test_candlestick_bearish_fallback(self):
        d = self.eng._determine_direction([], [_candle("bearish_engulfing")], [])
        assert d == "SHORT"

    def test_no_signal_returns_none(self):
        d = self.eng._determine_direction([], [], [])
        assert d is None

    def test_bos_takes_priority_over_candlestick(self):
        # BOS says bearish, candlestick says bullish → BOS wins
        d = self.eng._determine_direction(
            [_bos("bearish")],
            [_candle("bullish_engulfing")],
            [],
        )
        assert d == "SHORT"

    def test_multiple_playbook_matches_no_crash(self):
        pms = [
            _pm("NY_Open_Reversal", 0.9),
            _pm("London_Sweep", 0.6),
            _pm("ICT_Manipulation_Reversal", 0.3),
        ]
        # Direction must still come from BOS
        d = self.eng._determine_direction([_bos("bullish")], [], pms)
        assert d == "LONG"
