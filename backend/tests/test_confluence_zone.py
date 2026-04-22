"""Unit tests for confluence_zone — pure geometric helper."""
from __future__ import annotations

from engines.features.confluence_zone import (
    bar_touches_any_zone,
    bar_touches_zone,
)


def test_bar_inside_zone_touches():
    assert bar_touches_zone(99.5, 100.5, 99.0, 101.0) is True


def test_bar_above_zone_does_not_touch():
    assert bar_touches_zone(101.5, 102.0, 99.0, 101.0) is False


def test_bar_below_zone_does_not_touch():
    assert bar_touches_zone(97.0, 98.5, 99.0, 101.0) is False


def test_edge_touch_counts():
    # Bar high == zone low — closed-interval overlap.
    assert bar_touches_zone(98.0, 99.0, 99.0, 101.0) is True
    # Bar low == zone high — closed-interval overlap.
    assert bar_touches_zone(101.0, 102.0, 99.0, 101.0) is True


def test_zone_partial_overlap_top():
    assert bar_touches_zone(100.5, 101.5, 99.0, 101.0) is True


def test_first_matching_zone_wins():
    zones = [
        {"type": "fvg", "low": 100.0, "high": 101.0, "id": "fvg-1"},
        {"type": "breaker", "low": 100.0, "high": 101.0, "id": "br-1"},
    ]
    touched, zone_type, zone_id = bar_touches_any_zone(100.4, 100.6, zones)
    assert touched is True
    assert zone_type == "fvg"
    assert zone_id == "fvg-1"


def test_no_zones_no_touch():
    touched, zone_type, zone_id = bar_touches_any_zone(99.5, 100.5, [])
    assert touched is False
    assert zone_type is None
    assert zone_id is None


def test_inverted_zone_low_high_normalized():
    zones = [{"type": "fvg", "low": 101.0, "high": 99.0, "id": "z"}]
    touched, _, _ = bar_touches_any_zone(99.5, 100.5, zones)
    assert touched is True


def test_multi_zones_pick_first_match_only():
    zones = [
        {"type": "fvg", "low": 90.0, "high": 91.0, "id": "fvg-far"},
        {"type": "ob", "low": 100.0, "high": 101.0, "id": "ob-near"},
    ]
    _, zone_type, zone_id = bar_touches_any_zone(100.4, 100.6, zones)
    assert zone_type == "ob"
    assert zone_id == "ob-near"
