"""Agrégation légère des `mini_lab_summary` d'une campagne (nested/flat, hors moteur)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from backtest.metrics import profit_factor_from_gross_profit_loss
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
    sum_gross_profit_r = 0.0
    sum_gross_loss_r = 0.0
    n_pf = 0
    max_drawdown_r_max = None
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
        pf = tm.get("profit_factor")
        gp = tm.get("gross_profit_r")
        gl = tm.get("gross_loss_r")
        mdd = tm.get("max_drawdown_r")

        if pnl is not None:
            try:
                sum_pnl += float(pnl)
                n_pnl += 1
            except (TypeError, ValueError):
                pass
        if gp is not None and gl is not None:
            try:
                sum_gross_profit_r += float(gp)
                sum_gross_loss_r += float(gl)
                n_pf += 1
            except (TypeError, ValueError):
                pass
        if mdd is not None:
            try:
                v = float(mdd)
                max_drawdown_r_max = v if max_drawdown_r_max is None else max(max_drawdown_r_max, v)
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
                "profit_factor": float(pf) if pf is not None and isinstance(pf, (int, float)) else pf,
                "max_drawdown_r": float(mdd) if mdd is not None and isinstance(mdd, (int, float)) else mdd,
                "gross_profit_r": float(gp) if gp is not None and isinstance(gp, (int, float)) else gp,
                "gross_loss_r": float(gl) if gl is not None and isinstance(gl, (int, float)) else gl,
            }
        )

    profit_factor_from_sum_r = None
    if n_pf:
        try:
            profit_factor_from_sum_r = profit_factor_from_gross_profit_loss(
                float(sum_gross_profit_r), float(sum_gross_loss_r)
            )
        except Exception:
            profit_factor_from_sum_r = None

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
        "gross_profit_r_sum_tracked": sum_gross_profit_r if n_pf else None,
        "gross_loss_r_sum_tracked": sum_gross_loss_r if n_pf else None,
        "runs_with_pf_metrics": n_pf,
        "max_drawdown_r_max": max_drawdown_r_max,
        "profit_factor_from_sum_r": profit_factor_from_sum_r,
        "expectancy_r_weighted_by_trades": (weighted_r_num / weighted_r_den) if weighted_r_den > 0 else None,
        "note": "E[R] pondéré par total_trades (exact si expectancy_r = mean(r_multiple)). PF calculé via Σ gross_profit_r / |Σ gross_loss_r| quand disponible. max_drawdown_r_max = max des MaxDD par run (l’agrégat exact d’une campagne requiert l’union des parquets trades).",
    }


def rollup_output_parent(output_parent: str, *, results_base: Optional[Path] = None) -> Dict[str, Any]:
    if results_base is None:
        from utils.path_resolver import results_path

        base = results_path("labs", "mini_week", output_parent)
    else:
        base = results_base / "labs" / "mini_week" / output_parent

    return rollup_summaries_under_base(base, logical_name=output_parent)
