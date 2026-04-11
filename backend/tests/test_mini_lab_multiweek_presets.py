"""Présence et cohérence des presets multi-semaines (labs, sans run moteur)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "run_mini_lab_multiweek",
    _backend / "scripts" / "run_mini_lab_multiweek.py",
)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
PRESETS = _mod.PRESETS


def test_presets_contain_expected_months() -> None:
    assert "nov2025" in PRESETS
    assert "sep2025" in PRESETS
    assert "oct2025" in PRESETS
    assert "aug2025" in PRESETS


def test_each_preset_has_four_windows() -> None:
    for name, windows in PRESETS.items():
        assert len(windows) == 4, name
        for start, end, label in windows:
            assert start <= end
            assert len(label) >= 8
