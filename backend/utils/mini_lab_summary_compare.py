"""Comparaison structurée de deux `mini_lab_summary_*.json` (hors hot path)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from utils.mini_lab_funnel_playbooks import MINI_LAB_FUNNEL_PLAYBOOKS


def load_mini_lab_summary(path: Path | str) -> Dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(p)
    return json.loads(p.read_text(encoding="utf-8"))


def _funnel_keys() -> Tuple[str, ...]:
    return ("matches", "setups_created", "after_risk", "trades")


def _to_float_capital(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def compare_mini_lab_summaries(
    a: Dict[str, Any], b: Dict[str, Any], *, path_a: str = "", path_b: str = ""
) -> Dict[str, Any]:
    """
    Retourne un dict JSON-sérialisable : écarts funnel par playbook, totaux, capital.
    `expectancy` / PnL agrégé : absents du schéma summary actuel → null + note.
    """
    funnel_a = a.get("funnel") or {}
    funnel_b = b.get("funnel") or {}
    per_pb: Dict[str, Any] = {}
    for pb in MINI_LAB_FUNNEL_PLAYBOOKS:
        fa = funnel_a.get(pb) or {}
        fb = funnel_b.get(pb) or {}
        row: Dict[str, Any] = {"playbook": pb}
        for k in _funnel_keys():
            va = fa.get(k)
            vb = fb.get(k)
            ia = int(va) if va is not None else None
            ib = int(vb) if vb is not None else None
            row[k] = {"a": ia, "b": ib, "delta": (ib - ia) if ia is not None and ib is not None else None}
        per_pb[pb] = row

    tt_a = a.get("total_trades")
    tt_b = b.get("total_trades")
    try:
        tt_d = int(tt_b) - int(tt_a) if tt_a is not None and tt_b is not None else None
    except (TypeError, ValueError):
        tt_d = None

    fc_a = _to_float_capital(a.get("final_capital"))
    fc_b = _to_float_capital(b.get("final_capital"))
    fc_delta = (fc_b - fc_a) if fc_a is not None and fc_b is not None else None

    return {
        "schema_version": "MiniLabSummaryCompareV0",
        "path_a": path_a or None,
        "path_b": path_b or None,
        "run_id": {"a": a.get("run_id"), "b": b.get("run_id")},
        "window": {
            "a": {"start_date": a.get("start_date"), "end_date": a.get("end_date")},
            "b": {"start_date": b.get("start_date"), "end_date": b.get("end_date")},
        },
        "total_trades": {"a": tt_a, "b": tt_b, "delta": tt_d},
        "final_capital": {"a": fc_a, "b": fc_b, "delta": fc_delta},
        "expectancy_r": {
            "a": None,
            "b": None,
            "delta": None,
            "note": "non présent dans mini_lab_summary RunSummaryV0 — utiliser parquet trades / analyzers",
        },
        "funnel_by_playbook": per_pb,
    }


def compare_mini_lab_summary_files(path_a: Path | str, path_b: Path | str) -> Dict[str, Any]:
    pa, pb = Path(path_a), Path(path_b)
    da = load_mini_lab_summary(pa)
    db = load_mini_lab_summary(pb)
    return compare_mini_lab_summaries(da, db, path_a=str(pa.resolve()), path_b=str(pb.resolve()))
