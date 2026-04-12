from __future__ import annotations

import pytest

from utils.lab_environment_snapshot import (
    build_lab_environment_for_manifest,
    compute_data_fingerprint_v0,
    snapshot_risk_lab_environment,
)


def test_snapshot_contains_risk_keys() -> None:
    s = snapshot_risk_lab_environment()
    assert "RISK_EVAL_ALLOW_ALL_PLAYBOOKS" in s
    assert isinstance(s["RISK_EVAL_ALLOW_ALL_PLAYBOOKS"], (str, type(None)))


def test_snapshot_sees_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RISK_EVAL_RELAX_CAPS", "true")
    s = snapshot_risk_lab_environment()
    assert s["RISK_EVAL_RELAX_CAPS"] == "true"


def test_data_fingerprint_v0_shape() -> None:
    fp = compute_data_fingerprint_v0(["SPY", "QQQ"])
    assert fp["schema_version"] == "DataFingerprintV0"
    assert fp["timeframe"] == "1m"
    assert len(fp["sha256"]) == 64
    assert "SPY" in fp["by_symbol"] and "QQQ" in fp["by_symbol"]
    assert "exists" in fp["by_symbol"]["SPY"]


def test_build_lab_environment_includes_fingerprint_by_default() -> None:
    le = build_lab_environment_for_manifest(["SPY"])
    assert "RISK_EVAL_ALLOW_ALL_PLAYBOOKS" in le
    assert "data_fingerprint_v0" in le
    assert le["data_fingerprint_v0"]["schema_version"] == "DataFingerprintV0"


def test_build_lab_environment_omit_fingerprint_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEXTERIO_OMIT_DATA_FINGERPRINT", "1")
    le = build_lab_environment_for_manifest(["SPY"])
    assert "data_fingerprint_v0" not in le
