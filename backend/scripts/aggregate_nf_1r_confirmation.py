#!/usr/bin/env python3
"""
Agrège les campagnes `nf1r_confirm_*` (YAML canonique NF 1.0R) : métriques News_Fade par fenêtre,
funnel NY/LSS, comparaison avec la référence nov2025 @ 1.0R (PHASE B).

Usage (depuis backend/) :
  .venv/bin/python scripts/aggregate_nf_1r_confirmation.py
  .venv/bin/python scripts/aggregate_nf_1r_confirmation.py --out-md docs/PHASE_1_NF_1R_CONFIRMATION_TABLE.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

MINI_WEEK = backend_dir / "results" / "labs" / "mini_week"
PHASE_B_AGG = MINI_WEEK / "_phase_b_nf_tp1_aggregate.json"
CAMPAIGN_GLOB = "nf1r_confirm_*"


def _nf_trade_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    nf = df[df["playbook"] == "News_Fade"].copy()
    n = int(len(nf))
    if n == 0:
        return {
            "trades": 0,
            "winrate_pct": 0.0,
            "sum_r": 0.0,
            "expectancy_r": 0.0,
            "pct_session_end": 0.0,
            "pct_tp": 0.0,
            "pct_sl": 0.0,
            "median_duration_min": None,
            "exit_reason_counts": {},
        }
    wins = (nf["outcome"] == "win").sum()
    reasons = nf["exit_reason"].fillna("").astype(str)
    return {
        "trades": n,
        "winrate_pct": float(wins / n * 100.0),
        "sum_r": float(nf["r_multiple"].sum()),
        "expectancy_r": float(nf["r_multiple"].mean()),
        "pct_session_end": float((reasons == "session_end").mean() * 100.0),
        "pct_tp": float(reasons.isin(["TP1", "TP2"]).mean() * 100.0),
        "pct_sl": float((reasons == "SL").mean() * 100.0),
        "median_duration_min": float(nf["duration_minutes"].median()),
        "exit_reason_counts": {str(k): int(v) for k, v in reasons.value_counts().items()},
    }


def _load_summary(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _discover_campaign_weeks() -> List[Tuple[str, Path, str]]:
    """(campaign_name, week_dir_path, label)."""
    out: List[Tuple[str, Path, str]] = []
    if not MINI_WEEK.is_dir():
        return out
    for camp in sorted(MINI_WEEK.glob(CAMPAIGN_GLOB)):
        if not camp.is_dir():
            continue
        for week_dir in sorted(camp.iterdir()):
            if not week_dir.is_dir():
                continue
            label = week_dir.name
            sp = week_dir / f"mini_lab_summary_{label}.json"
            if sp.is_file():
                out.append((camp.name, week_dir, label))
    return out


def _trades_parquet(campaign: str, week_dir: Path, label: str) -> Optional[Path]:
    run_id = f"miniweek_{campaign}_{label}"
    p = week_dir / f"trades_{run_id}_AGGRESSIVE_DAILY_SCALP.parquet"
    return p if p.is_file() else None


def _reference_nov2025_1r() -> Optional[Dict[str, Any]]:
    if not PHASE_B_AGG.is_file():
        return None
    data = json.loads(PHASE_B_AGG.read_text(encoding="utf-8"))
    for row in data.get("nf_by_tp1_rr") or []:
        if abs(float(row.get("tp1_rr", 0)) - 1.0) < 1e-9:
            return row
    return None


def _build_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    ref = _reference_nov2025_1r()
    if ref:
        rows.append(
            {
                "campaign": "PHASE_B_REFERENCE",
                "label": "nov2025_agg_4w",
                "month": "2025-11",
                "note": "Agrégat 4 semaines sweep tp1=1.0 (phase_b_nf_tp1rr_1p00)",
                "trades": ref["trades"],
                "winrate_pct": ref["winrate_pct"],
                "sum_r": ref["sum_r"],
                "expectancy_r": ref["expectancy_r"],
                "pct_session_end": ref["pct_session_end"],
                "pct_tp": ref["pct_tp"],
                "pct_sl": ref["pct_sl"],
                "median_duration_min": ref.get("median_duration_min"),
                "exit_reason_counts": ref.get("exit_reason_counts", {}),
                "funnel_NY": None,
                "funnel_LSS": None,
            }
        )

    for campaign, week_dir, label in _discover_campaign_weeks():
        tp = _trades_parquet(campaign, week_dir, label)
        summary = _load_summary(week_dir / f"mini_lab_summary_{label}.json")
        funnel = summary.get("funnel") or {}
        ny = funnel.get("NY_Open_Reversal")
        lss = funnel.get("Liquidity_Sweep_Scalp")
        month = label
        if len(label) >= 6 and label[:6].isdigit():
            month = f"{label[:4]}-{label[4:6]}"
        if tp is not None:
            df = pd.read_parquet(tp)
            m = _nf_trade_metrics(df)
        else:
            m = _nf_trade_metrics(pd.DataFrame())
            m["note"] = "missing trades parquet"
        rows.append(
            {
                "campaign": campaign,
                "label": label,
                "month": month,
                "funnel_NY": ny,
                "funnel_LSS": lss,
                **m,
            }
        )
    return rows


def _campaign_rollups(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    from collections import defaultdict

    agg: dict[str, dict[str, float]] = defaultdict(
        lambda: {"nf_trades": 0.0, "sum_r": 0.0, "weeks": 0.0, "sum_tp_pct": 0.0, "sum_se_pct": 0.0}
    )
    for r in rows:
        camp = str(r.get("campaign") or "")
        if camp == "PHASE_B_REFERENCE" or not camp.startswith("nf1r_confirm_"):
            continue
        a = agg[camp]
        a["nf_trades"] += float(r.get("trades") or 0)
        a["sum_r"] += float(r.get("sum_r") or 0.0)
        a["weeks"] += 1.0
        a["sum_tp_pct"] += float(r.get("pct_tp") or 0.0)
        a["sum_se_pct"] += float(r.get("pct_session_end") or 0.0)
    out: List[Dict[str, Any]] = []
    for camp in sorted(agg.keys()):
        a = agg[camp]
        n = int(a["nf_trades"])
        w = int(a["weeks"])
        e = (a["sum_r"] / n) if n else None
        out.append(
            {
                "campaign": camp,
                "weeks_completed": w,
                "nf_trades_total": n,
                "sum_r_nf_total": round(a["sum_r"], 4),
                "expectancy_r_nf": round(e, 6) if e is not None else None,
                "mean_pct_tp": round(a["sum_tp_pct"] / w, 2) if w else None,
                "mean_pct_session_end": round(a["sum_se_pct"] / w, 2) if w else None,
            }
        )
    return out


def _gate_decision(
    *,
    ref: Optional[Dict[str, Any]],
    week_rows: List[Dict[str, Any]],
    _rollups: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Heuristique documentée ; révision humaine si proche des seuils."""
    n_weeks = len(week_rows)
    total_trades = sum(int(r.get("trades") or 0) for r in week_rows)
    total_sr = sum(float(r.get("sum_r") or 0.0) for r in week_rows)
    e = (total_sr / total_trades) if total_trades else None
    ref_e = float(ref["expectancy_r"]) if ref and ref.get("expectancy_r") is not None else None

    if n_weeks < 10:
        return {
            "gate": "KEEP_1R_PROVISIONAL",
            "reason": f"fenêtres nf1r_confirm complétées={n_weeks} (<10 requis pour gate ferme)",
            "nf_trades_total": total_trades,
            "expectancy_r_nf": e,
        }
    if ref is None or ref_e is None:
        return {
            "gate": "KEEP_1R_PROVISIONAL",
            "reason": "référence PHASE B (_phase_b_nf_tp1_aggregate.json) absente ou incomplète",
            "nf_trades_total": total_trades,
            "expectancy_r_nf": e,
        }
    if total_trades == 0 or e is None:
        return {
            "gate": "KEEP_1R_PROVISIONAL",
            "reason": "aucun trade NF agrégé sur les fenêtres nf1r_confirm",
            "nf_trades_total": total_trades,
            "expectancy_r_nf": e,
        }
    # Divergence nette vs ref nov2025 @1R (expectancy positive) sur volume suffisant
    if total_trades >= 40 and e < 0 and ref_e > 0.02:
        return {
            "gate": "REOPEN_1R_VS_1P5R",
            "reason": (
                f"expectancy NF agrégée négative ({e:.4f}R) vs ref PHASE B positive ({ref_e:.4f}R), "
                f"n={total_trades} — rouvrir arbitrage 1.0R vs 1.5R sur mêmes fenêtres"
            ),
            "nf_trades_total": total_trades,
            "expectancy_r_nf": e,
        }
    if total_trades >= 25 and e < ref_e - 0.12:
        return {
            "gate": "REOPEN_1R_VS_1P5R",
            "reason": f"expectancy NF {e:.4f} << ref nov {ref_e:.4f} sur n={total_trades}",
            "nf_trades_total": total_trades,
            "expectancy_r_nf": e,
        }
    if total_trades >= 45 and e >= ref_e - 0.06:
        return {
            "gate": "PROMOTE_1R_TO_PAPER_CANDIDATE",
            "reason": f"expectancy alignée ref (Δ≤0.06) et volume n={total_trades}",
            "nf_trades_total": total_trades,
            "expectancy_r_nf": e,
        }
    return {
        "gate": "KEEP_1R_PROVISIONAL",
        "reason": "volume ou expectancy dans zone intermédiaire — révision manuelle",
        "nf_trades_total": total_trades,
        "expectancy_r_nf": e,
    }


def _md_table(rows: List[Dict[str, Any]]) -> str:
    lines = [
        "# PHASE 1 — Tableau confirmation News_Fade 1.0R",
        "",
        "| campaign | label | trades | WR% | ΣR | E[R] | %TP | %SL | %session_end | durée méd min |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        dur = r.get("median_duration_min")
        dur_s = f"{dur:.1f}" if dur is not None else "n/a"
        lines.append(
            f"| {r.get('campaign')} | {r.get('label')} | {r.get('trades')} | "
            f"{r.get('winrate_pct', 0):.1f} | {r.get('sum_r', 0):.2f} | {r.get('expectancy_r', 0):.3f} | "
            f"{r.get('pct_tp', 0):.1f} | {r.get('pct_sl', 0):.1f} | {r.get('pct_session_end', 0):.1f} | {dur_s} |"
        )
    lines.append("")
    lines.append("## exit_reason (détail)")
    for r in rows:
        lines.append(f"- **{r.get('campaign')} / {r.get('label')}** : `{r.get('exit_reason_counts', {})}`")
    lines.append("")
    lines.append("## Agrégats par campagne")
    lines.append("")
    lines.append("| campaign | semaines | NF trades | ΣR NF | E[R] NF | mean %TP | mean %session_end |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    # rollups passed via closure — regenerate from rows
    for u in _campaign_rollups(rows):
        e = u.get("expectancy_r_nf")
        es = f"{e:.4f}" if e is not None else "n/a"
        lines.append(
            f"| {u['campaign']} | {u['weeks_completed']} | {u['nf_trades_total']} | "
            f"{u['sum_r_nf_total']:.2f} | {es} | {u.get('mean_pct_tp')} | {u.get('mean_pct_session_end')} |"
        )
    lines.append("")
    lines.append("## Gate (heuristique)")
    gate = _gate_decision(
        ref=_reference_nov2025_1r(),
        week_rows=[r for r in rows if str(r.get("campaign") or "").startswith("nf1r_confirm_")],
        rollups=_campaign_rollups(rows),
    )
    lines.append(f"- **{gate['gate']}** — {gate['reason']}")
    lines.append("")
    lines.append("## Funnel NY / LSS (extraits summary)")
    for r in rows:
        if r.get("funnel_NY") is not None:
            lines.append(f"- **{r['campaign']} / {r['label']}** NY={r['funnel_NY']} LSS={r.get('funnel_LSS')}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out-json",
        type=str,
        default=str(MINI_WEEK / "_nf_1r_confirmation_aggregate.json"),
    )
    parser.add_argument("--out-md", type=str, default="")
    args = parser.parse_args()

    rows = _build_rows()
    ref = _reference_nov2025_1r()
    rollups = _campaign_rollups(rows)
    week_rows = [r for r in rows if str(r.get("campaign") or "").startswith("nf1r_confirm_")]
    gate = _gate_decision(ref=ref, week_rows=week_rows, rollups=rollups)
    out_path = Path(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "reference_phase_b_nov2025_tp1_1r": ref,
        "campaign_rollups": rollups,
        "gate_nf_1r": gate,
        "windows": rows,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[nf_confirm] wrote {out_path} ({len(rows)} rows)", flush=True)

    if args.out_md:
        md_path = Path(args.out_md)
        if not md_path.is_absolute():
            md_path = backend_dir / md_path
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(_md_table(rows), encoding="utf-8")
        print(f"[nf_confirm] wrote {md_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
