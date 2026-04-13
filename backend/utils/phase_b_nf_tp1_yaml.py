"""
PHASE B — Génère un `playbooks.yml` dérivé pour sweep `tp1_rr` / `min_rr` sur News_Fade uniquement.

Le fichier canonique `knowledge/playbooks.yml` n'est pas modifié ; les autres playbooks
restent identiques (à structure YAML près après round-trip dump).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml

CANONICAL_PLAYBOOKS = Path(__file__).resolve().parent.parent / "knowledge" / "playbooks.yml"


def nf_tp1_rr_tag(tp1_rr: float) -> str:
    """Ex. 1.0 -> 1p00, 1.25 -> 1p25, 2.0 -> 2p00."""
    return f"{tp1_rr:.2f}".replace(".", "p")


def _load_playbooks_list(path: Path) -> List[Dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, list):
        raise ValueError(f"playbooks.yml attendu comme liste de documents: {path}")
    return data


def ny_open_reversal_block(docs: List[Dict[str, Any]]) -> Dict[str, Any]:
    for doc in docs:
        if isinstance(doc, dict) and doc.get("playbook_name") == "NY_Open_Reversal":
            return doc
    raise ValueError("NY_Open_Reversal introuvable")


def write_nf_tp1_sweep_yaml(
    *,
    canonical_path: Path,
    dest_path: Path,
    tp1_rr: float,
) -> None:
    """Écrit une copie YAML où seul News_Fade.take_profit_logic.min_rr et tp1_rr changent."""
    docs = _load_playbooks_list(canonical_path)
    found = False
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        if doc.get("playbook_name") != "News_Fade":
            continue
        tpl = doc.setdefault("take_profit_logic", {})
        rr = float(tp1_rr)
        tpl["min_rr"] = rr
        tpl["tp1_rr"] = rr
        found = True
        break
    if not found:
        raise ValueError("News_Fade introuvable dans le YAML")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dest_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            docs,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )


def assert_ny_unchanged_after_sweep(*, canonical_path: Path, derived_path: Path) -> None:
    """Vérifie que le bloc NY_Open_Reversal est identique (dict) entre canonique et dérivé."""
    c_docs = _load_playbooks_list(canonical_path)
    d_docs = _load_playbooks_list(derived_path)
    assert ny_open_reversal_block(c_docs) == ny_open_reversal_block(d_docs)
