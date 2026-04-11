"""CampaignManifestV0 — `run_manifest.json` émis par run_mini_lab_week."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class CampaignManifestV0(BaseModel):
    model_config = ConfigDict(extra="ignore")

    schema_version: str
    contract_version: str
    run_id: str
    runner: str
    argv: List[str]
    cwd: str
    git_sha: str
    run_started_at_utc: str
    symbols: List[str]
    start_date: str
    end_date: str
    label: str
    output_parent: Optional[str] = None
    respect_allowlists: bool
    bypass_lss_quarantine: bool


def parse_campaign_manifest_v0(data: Dict[str, Any]) -> CampaignManifestV0:
    return CampaignManifestV0.model_validate(data)
