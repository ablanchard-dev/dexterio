"""Agrégation légère des `mini_lab_summary` d'une campagne (nested/flat, hors moteur)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.campaign_output_audit import campaign_run_directories


def _load_summary(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def rollup_summaries_under_base(base: Path, *, logical_name: str) -> Dict[str, Any]:
    """
    Lit chaque `mini_lab_summary*.json` par dossier de run et agrège des totaux.

    `expectancy_r_weighted_by_trades` = moyenne des `expectancy_r` (ou `mean_r_multiple`)
    pondérée par `total_trades` **par run** — approximation si les fenêtres diffèrent ;
    l’agrégat exact requiert l’union des parquets trades.
    """
    layout, dirs = campaign_run_directories(base)
    per_run: List[Dict[str, Any]] = []
    total_trades_sum = 0
    sum_pnl = 0.0
    n_pnl = 0
    weighted_r_num = 0.0
    weighted_r_den = 0
    all_dc = True

    for d in dirs:
        summaries = sorted(d.glob("mini_lab_summary*.json"))
        if not summaries:
            continue
        data = _load_summary(summaries[0])
        if not data:
            continue

        tt_raw = data.get("total_trades")
        try:
            tt = int(tt_raw) if tt_raw is not None else 0
        except (TypeError, ValueError):
            tt = 0

        dc_ok = data.get("data_coverage_ok")
        if dc_ok is not True:
            all_dc = False

        tm = data.get("trade_metrics_parquet")
        tm = tm if isinstance(tm, dict) else {}
        pnl = tm.get("sum_pnl_dollars")
        ex = tm.get("expectancy_r")
        if ex is None:
            ex = tm.get("mean_r_multiple")

        if pnl is not None:
            try:
                sum_pnl += float(pnl)
                n_pnl += 1
            except (TypeError, ValueError):
                pass

        if ex is not None and tt > 0:
            try:
                weighted_r_num += float(ex) * tt
                weighted_r_den += tt
            except (TypeError, ValueError):
                pass

        total_trades_sum += tt

        per_run.append(
            {
                "label": d.name,
                "start_date": data.get("start_date"),
                "end_date": data.get("end_date"),
                "run_id": data.get("run_id"),
                "total_trades": tt_raw,
                "data_coverage_ok": dc_ok,
                "sum_pnl_dollars": float(pnl) if pnl is not None and isinstance(pnl, (int, float)) else pnl,
                "expectancy_r": float(ex) if ex is not None and isinstance(ex, (int, float)) else ex,
            }
        )

    return {
        "schema_version": "CampaignRollupV0",
        "layout": layout,
        "logical_name": logical_name,
        "base_path": str(base.resolve()) if base.is_dir() else str(base),
        "base_exists": base.is_dir(),
        "run_count": len(per_run),
        "runs": per_run,
        "total_trades_sum": total_trades_sum,
        "all_data_coverage_ok": all_dc if per_run else False,
        "sum_pnl_dollars_tracked": sum_pnl if n_pnl else None,
        "runs_with_pnl_metrics": n_pnl,
        "expectancy_r_weighted_by_trades": (weighted_r_num / weighted_r_den) if weighted_r_den > 0 else None,
        "note": "Pondération par total_trades par run ; pour ΣR / E[R] sur l’union des trades, agréger les parquets.",
    }


def rollup_output_parent(output_parent: str, *, results_base: Optional[Path] = None) -> Dict[str, Any]:
    if results_base is None:
        from utils.path_resolver import results_path

        base = results_path("labs", "mini_week", output_parent)
    else:
        base = results_base / "labs" / "mini_week" / output_parent

    return rollup_summaries_under_base(base, logical_name=output_parent)
