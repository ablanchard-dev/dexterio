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
    out_path = Path(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "reference_phase_b_nov2025_tp1_1r": _reference_nov2025_1r(),
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
