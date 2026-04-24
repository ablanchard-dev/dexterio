"""Tests for F6 forward_factor pure logic (skeleton before data arrives)."""
from __future__ import annotations

import pytest

from engines.options.forward_factor import (
    classify_signal,
    compute_forward_factor,
    data_gate_status,
)


def test_compute_ff_basic():
    # FF = (front - forward) / forward
    # iv_front=0.24, iv_forward=0.20 → FF = 0.04/0.20 = 0.20
    assert compute_forward_factor(0.24, 0.20) == pytest.approx(0.20)


def test_compute_ff_negative_contango():
    # backwardation : front < forward → negative FF
    assert compute_forward_factor(0.15, 0.20) == pytest.approx(-0.25)


def test_compute_ff_handles_zero_forward():
    assert compute_forward_factor(0.24, 0.0) == 0.0
    assert compute_forward_factor(0.24, -0.01) == 0.0


def test_classify_signal_threshold():
    assert classify_signal(0.25) == "long_calendar"  # > 0.20
    assert classify_signal(0.20) == "long_calendar"  # exact threshold
    assert classify_signal(0.19) == "skip"           # below
    assert classify_signal(-0.05) == "skip"           # backwardation


def test_classify_custom_threshold():
    assert classify_signal(0.15, threshold=0.10) == "long_calendar"
    assert classify_signal(0.15, threshold=0.25) == "skip"


def test_data_gate_status_returns_blocked():
    status = data_gate_status()
    assert status["data_available"] is False
    assert status["can_backtest"] is False
    assert "§0.3 point 5" in status["escalation"]
    assert "options chain" in status["reason"]
