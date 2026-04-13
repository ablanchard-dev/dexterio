#!/usr/bin/env python3
"""
PHASE B — Agrège les runs `phase_b_nf_tp1rr_*` (parquets + mini_lab_summary) et sort un JSON + MD.

Usage (depuis backend/) :
  .venv/bin/python scripts/aggregate_phase_b_nf_tp1_sweep.py
  .venv/bin/python scripts/aggregate_phase_b_nf_tp1_sweep.py --out-md docs/PHASE_B_NF_TP1_RR_SWEEP.md
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

from utils.phase_b_nf_tp1_yaml import CANONICAL_PLAYBOOKS, nf_tp1_rr_tag

TP1_VALUES = (1.0, 1.25, 1.5, 2.0)
BASELINE_PARENT = None  # dossiers directs mini_week/<label>/
WEEKS = ("202511_w01", "202511_w02", "202511_w03", "202511_w04")


def _mini_week_root() -> Path:
    return backend_dir / "results" / "labs" / "mini_week"


def _load_summary(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _variant_parent(tp1: float) -> str:
    return f"phase_b_nf_tp1rr_{nf_tp1_rr_tag(tp1)}"


def _collect_nf_parquet_frames(tp1: float) -> pd.DataFrame:
    """Les mini-labs écrivent `trades_<run_id>_AGGRESSIVE_DAILY_SCALP.parquet` (journal désactivé)."""
    parent = _variant_parent(tp1)
    frames: List[pd.DataFrame] = []
    root = _mini_week_root()
    for w in WEEKS:
        run_id = f"miniweek_{parent}_{w}"
        p = root / parent / w / f"trades_{run_id}_AGGRESSIVE_DAILY_SCALP.parquet"
        if not p.is_file():
            continue
        frames.append(pd.read_parquet(p))
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _nf_metrics(df: pd.DataFrame, tp1_rr: float) -> Dict[str, Any]:
    nf = df[df["playbook"] == "News_Fade"].copy()
    n = int(len(nf))
    if n == 0:
        return {
            "trades": 0,
            "winrate_pct": 0.0,
            "sum_r": 0.0,
            "expectancy_r": 0.0,
            "exit_reason_counts": {},
            "pct_session_end": 0.0,
            "pct_tp": 0.0,
            "pct_sl": 0.0,
            "median_duration_min": None,
            "median_r_tp1_exits": None,
            "median_r_tp1_over_tp1_rr": None,
        }
    wins = (nf["outcome"] == "win").sum()
    wr = float(wins / n * 100.0)
    sum_r = float(nf["r_multiple"].sum())
    exp = float(nf["r_multiple"].mean())
    reasons = nf["exit_reason"].fillna("").astype(str)
    vc = reasons.value_counts().to_dict()
    pct_se = float((reasons == "session_end").mean() * 100.0)
    pct_tp = float(reasons.isin(["TP1", "TP2"]).mean() * 100.0)
    pct_sl = float((reasons == "SL").mean() * 100.0)
    med_dur = float(nf["duration_minutes"].median()) if "duration_minutes" in nf.columns else None
    tp1_mask = reasons == "TP1"
    med_r_tp1 = float(nf.loc[tp1_mask, "r_multiple"].median()) if tp1_mask.any() else None
    ratio = (med_r_tp1 / tp1_rr) if (med_r_tp1 is not None and tp1_rr > 0) else None
    return {
        "trades": n,
        "winrate_pct": wr,
        "sum_r": sum_r,
        "expectancy_r": exp,
        "exit_reason_counts": {str(k): int(v) for k, v in vc.items()},
        "pct_session_end": pct_se,
        "pct_tp": pct_tp,
        "pct_sl": pct_sl,
        "median_duration_min": med_dur,
        "median_r_tp1_exits": med_r_tp1,
        "median_r_tp1_over_tp1_rr": ratio,
    }


def _funnel_ny_lss(root: Path, parent: Optional[str], week: str) -> Dict[str, Any]:
    if parent:
        sp = root / parent / week / f"mini_lab_summary_{week}.json"
    else:
        sp = root / week / f"mini_lab_summary_{week}.json"
    if not sp.is_file():
        return {}
    s = _load_summary(sp)
    f = s.get("funnel") or {}
    return {
        "NY_Open_Reversal": f.get("NY_Open_Reversal"),
        "Liquidity_Sweep_Scalp": f.get("Liquidity_Sweep_Scalp"),
    }


def _compare_ny_across_variants(root: Path) -> Dict[str, Any]:
    """Pour chaque semaine : funnel NY (et LSS) doit coïncider entre les 4 variantes."""
    by_week: Dict[str, Any] = {}
    for w in WEEKS:
        snapshots = []
        for tp1 in TP1_VALUES:
            snap = _funnel_ny_lss(root, _variant_parent(tp1), w)
            snapshots.append({"tp1_rr": tp1, "funnel_slice": snap})
        first = json.dumps(snapshots[0]["funnel_slice"], sort_keys=True)
        all_match = all(json.dumps(s["funnel_slice"], sort_keys=True) == first for s in snapshots)
        by_week[w] = {
            "ny_funnel_identical_across_tp1_variants": all_match,
            "per_variant": snapshots,
        }
    return by_week


def _compare_ny_to_baseline(root: Path) -> Dict[str, Any]:
    """Baseline = mini_week/<week>/ sans output_parent."""
    out: Dict[str, Any] = {}
    for w in WEEKS:
        base = _funnel_ny_lss(root, None, w)
        row = {"baseline_NY": base.get("NY_Open_Reversal")}
        for tp1 in TP1_VALUES:
            v = _funnel_ny_lss(root, _variant_parent(tp1), w)
            row[f"variant_{nf_tp1_rr_tag(tp1)}_NY"] = v.get("NY_Open_Reversal")
        bjson = json.dumps(row["baseline_NY"], sort_keys=True)
        row["each_variant_matches_baseline_funnel"] = all(
            json.dumps(row[f"variant_{nf_tp1_rr_tag(tp1)}_NY"], sort_keys=True) == bjson
            for tp1 in TP1_VALUES
        )
        out[w] = row
    return out


def _build_markdown(rows: List[Dict[str, Any]], ny_proof: Dict[str, Any]) -> str:
    lines = [
        "# PHASE B — Sweep `tp1_rr` News_Fade (nov2025)",
        "",
        f"YAML canonique (inchangé sur disque) : `{CANONICAL_PLAYBOOKS.relative_to(backend_dir)}`.",
        "",
        "## Tableau comparatif (News_Fade, 4 semaines agrégées)",
        "",
        "| tp1_rr (=min_rr) | trades | winrate % | ΣR | expectancy R | % session_end | % TP | % SL | durée méd. (min) | médiane R (TP1) / tp1_rr |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in rows:
        med_r = r.get("median_r_tp1_exits")
        ratio = r.get("median_r_tp1_over_tp1_rr")
        ratio_s = f"{ratio:.3f}" if ratio is not None else "n/a"
        med_tp1_s = f"{med_r:.3f}" if med_r is not None else "n/a"
        lines.append(
            f"| {r['tp1_rr']} | {r['trades']} | {r['winrate_pct']:.1f} | {r['sum_r']:.2f} | "
            f"{r['expectancy_r']:.3f} | {r['pct_session_end']:.1f} | {r['pct_tp']:.1f} | {r['pct_sl']:.1f} | "
            f"{r['median_duration_min'] if r['median_duration_min'] is not None else 'n/a'} | "
            f"{med_tp1_s} / {ratio_s} |"
        )
    lines.extend(
        [
            "",
            "### exit_reason (agrégé par variante)",
            "",
        ]
    )
    for r in rows:
        lines.append(f"- **tp1_rr={r['tp1_rr']}** : `{r['exit_reason_counts']}`")
    lines.extend(
        [
            "",
            "## Preuve NY / LSS (funnel mini_lab_summary)",
            "",
            "- Comparaison **entre les 4 variantes** (même semaine) : le funnel `NY_Open_Reversal` doit être identique.",
            "- Comparaison **vs baseline** `mini_week/<week>/` : idem si le YAML dérivé ne touche pas NY.",
            "",
            "```json",
            json.dumps(ny_proof, indent=2),
            "```",
            "",
            "### Note MFE",
            "",
            "Le journal ne contient pas de MFE bar-by-bar. **Proxy** : médiane `r_multiple` sur sorties `TP1` vs `tp1_rr` "
            "(frais inclus : le ratio est souvent inférieur à 1).",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out-json",
        type=str,
        default=str(_mini_week_root() / "_phase_b_nf_tp1_aggregate.json"),
        help="Chemin sortie JSON",
    )
    parser.add_argument("--out-md", type=str, default="", help="Optionnel : rapport Markdown")
    args = parser.parse_args()

    root = _mini_week_root()
    rows: List[Dict[str, Any]] = []
    for tp1 in TP1_VALUES:
        df = _collect_nf_parquet_frames(tp1)
        m = _nf_metrics(df, tp1)
        m["tp1_rr"] = tp1
        m["variant_dir"] = _variant_parent(tp1)
        rows.append(m)

    ny_proof = {
        "canonical_playbooks_path": str(CANONICAL_PLAYBOOKS),
        "cross_variant_ny_funnel": _compare_ny_across_variants(root),
        "baseline_vs_variants_NY": _compare_ny_to_baseline(root),
    }

    out_path = Path(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"nf_by_tp1_rr": rows, "ny_verification": ny_proof}
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[aggregate] wrote {out_path}", flush=True)

    if args.out_md:
        md_path = Path(args.out_md)
        if not md_path.is_absolute():
            md_path = backend_dir / md_path
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(_build_markdown(rows, ny_proof), encoding="utf-8")
        print(f"[aggregate] wrote {md_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
