from __future__ import annotations

import pytest

from utils.lab_environment_snapshot import snapshot_risk_lab_environment


def test_snapshot_contains_risk_keys() -> None:
    s = snapshot_risk_lab_environment()
    assert "RISK_EVAL_ALLOW_ALL_PLAYBOOKS" in s
    assert isinstance(s["RISK_EVAL_ALLOW_ALL_PLAYBOOKS"], (str, type(None)))


def test_snapshot_sees_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RISK_EVAL_RELAX_CAPS", "true")
    s = snapshot_risk_lab_environment()
    assert s["RISK_EVAL_RELAX_CAPS"] == "true"
