"""Validation CampaignManifestV0 sur run_manifest.json réel."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from contracts.campaign_manifest_v0 import CampaignManifestV0, parse_campaign_manifest_v0

_BACKEND = Path(__file__).resolve().parent.parent
_MANIFEST = (
    _BACKEND
    / "results"
    / "labs"
    / "mini_week"
    / "wave2_fvg_w21_validate"
    / "202509_w01"
    / "run_manifest.json"
)


@pytest.mark.skipif(not _MANIFEST.is_file(), reason="run_manifest artefact absent")
def test_parse_wave2_fvg_validate_run_manifest() -> None:
    data = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    m = parse_campaign_manifest_v0(data)
    assert isinstance(m, CampaignManifestV0)
    assert m.schema_version == "CampaignManifestV0"
    assert m.contract_version == "RunSummaryV0"
    assert "wave2_fvg_w21_validate" in (m.output_parent or "")
