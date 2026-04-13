"""PHASE B — YAML dérivé News_Fade : NY_Open_Reversal inchangé."""
from __future__ import annotations

from pathlib import Path

from utils.phase_b_nf_tp1_yaml import (
    CANONICAL_PLAYBOOKS,
    assert_ny_unchanged_after_sweep,
    write_nf_tp1_sweep_yaml,
)


def test_sweep_yaml_preserves_ny_open_reversal(tmp_path: Path) -> None:
    dest = tmp_path / "playbooks_sweep.yml"
    write_nf_tp1_sweep_yaml(
        canonical_path=CANONICAL_PLAYBOOKS,
        dest_path=dest,
        tp1_rr=1.25,
    )
    assert dest.is_file()
    assert_ny_unchanged_after_sweep(canonical_path=CANONICAL_PLAYBOOKS, derived_path=dest)


def test_news_fade_tp1_updated(tmp_path: Path) -> None:
    import yaml

    dest = tmp_path / "p.yml"
    write_nf_tp1_sweep_yaml(canonical_path=CANONICAL_PLAYBOOKS, dest_path=dest, tp1_rr=2.0)
    with open(dest, encoding="utf-8") as f:
        docs = yaml.safe_load(f)
    nf = next(d for d in docs if d.get("playbook_name") == "News_Fade")
    assert nf["take_profit_logic"]["tp1_rr"] == 2.0
    assert nf["take_profit_logic"]["min_rr"] == 2.0
