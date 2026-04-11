"""Wave 2 W2-1 — FVG_Fill_Scalp : contexte range autorisé (YAML seul)."""
from __future__ import annotations

from pathlib import Path

from engines.playbook_loader import PLAYBOOKS_PATH, PlaybookLoader


def test_fvg_fill_scalp_allows_range_day_and_structure() -> None:
    loader = PlaybookLoader(playbooks_path=Path(PLAYBOOKS_PATH))
    fvg = loader.get_playbook_by_name("FVG_Fill_Scalp")
    assert fvg is not None
    assert "range" in fvg.day_type_allowed
    assert "range" in fvg.structure_htf
    assert "trend" in fvg.day_type_allowed
