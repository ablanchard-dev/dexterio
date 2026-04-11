"""
RunSummaryV0 — sous-ensemble validé des `mini_lab_summary_*.json`.

Les champs optionnels couvrent les résumés historiques avant durcissement paper.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FunnelStepV0(BaseModel):
    model_config = ConfigDict(extra="forbid")

    matches: int = Field(ge=0)
    setups_created: int = Field(ge=0)
    after_risk: int = Field(ge=0)
    trades: int = Field(ge=0)


class RunSummaryV0(BaseModel):
    """Contrat minimal pour agrégation / futur front."""

    model_config = ConfigDict(extra="ignore")

    protocol: str
    runner: str
    git_sha: str
    run_id: str
    start_date: str
    end_date: str
    symbols: list
    respect_allowlists: bool
    bypass_lss_quarantine: bool
    total_trades: int = Field(ge=0)
    final_capital: str
    playbooks_registered_count: Optional[int] = None
    funnel: Dict[str, FunnelStepV0]
    output_parent: Optional[str] = None
    playbooks_yaml: Optional[str] = None
    nf_tp1_rr_meta: Optional[float] = None
    contract_version: Optional[str] = None
    run_started_at_utc: Optional[str] = None

    @field_validator("funnel", mode="before")
    @classmethod
    def _coerce_funnel(cls, v: Any) -> Any:
        if not isinstance(v, dict):
            return v
        out: Dict[str, Any] = {}
        for k, step in v.items():
            if isinstance(step, dict):
                out[k] = {sk: int(sv) for sk, sv in step.items()}
        return out


def parse_run_summary_v0(data: Dict[str, Any]) -> RunSummaryV0:
    return RunSummaryV0.model_validate(data)
