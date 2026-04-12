#!/usr/bin/env python3
"""
Arbitrage News_Fade tp1 1.0R vs 1.5R — mêmes fenêtres aug/sep/oct 2025 (presets multiweek).

Prérequis : campagnes jumelles produites par `run_mini_lab_multiweek.py` avec YAML dérivés :
  - nf_tp1_arb_1p00_<preset>  (ex. nf_tp1_arb_1p00_sep2025)
  - nf_tp1_arb_1p50_<preset>

Ne lit pas les anciens `nf1r_confirm_*` (YAML canonique sans override ≠ preuve tp1 explicite).

Usage (depuis backend/) :
  .venv/bin/python scripts/aggregate_nf_tp1_arbitration.py
  .venv/bin/python scripts/aggregate_nf_tp1_arbitration.py --out-md docs/PHASE_NF_TP1_ARBITRATION_TABLE.md
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

from utils.nf_tp1_arbitration_campaign import (
    NF_TP1_ARBITRATION_WINDOWS,
    analyze_nf_trade_count_alignment,
    build_campaign_manifest,
    pair_status,
    trades_parquet_path,
)

MINI_WEEK = backend_dir / "results" / "labs" / "mini_week"
PHASE_B_AGG = MINI_WEEK / "_phase_b_nf_tp1_aggregate.json"
CAMPAIGN_MANIFEST_PATH = MINI_WEEK / "_nf_tp1_arbitration_campaign_manifest.json"

EPSILON_ER = 0.015
# Documenté dans docs/PHASE_NF_TP1_ARBITRATION.md — section « Seuil ε (epsilon_er) ».
EPSILON_ER_RATIONALE = (
    "Seuil opérationnel heuristique (pas intervalle de confiance ni test d'hypothèse formel sur E[R]). "
    "Objectif : exiger une séparation nette entre 1.0R et 1.5R après agrégation sur 12 semaines, "
    "plutôt que trancher sur des différences du même ordre que le bruit de petits sous-échantillons. "
    "Ancrage qualitatif : sur PHASE B nov (~27 trades NF), l'écart d'expectancy entre tp1=1.0 et 1.5 "
    "est très étroit (~4·10⁻⁴R), largement sous 0.015R ; le seuil vise donc un écart « structurel » "
    "sur la campagne multi-semaines, pas le micro-raffinement d'un seul mois. "
    "Esprit aligné sur les gates NF existantes (marges fixes vs ref, sans z-score). "
    "À réviser si le volume agrégé augmente fortement ou si la politique produit impose une autre sensibilité."
)


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


def _load_summary(campaign: str, label: str) -> Optional[Dict[str, Any]]:
    p = MINI_WEEK / campaign / label / f"mini_lab_summary_{label}.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _phase_b_rows() -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    if not PHASE_B_AGG.is_file():
        return None, None
    data = json.loads(PHASE_B_AGG.read_text(encoding="utf-8"))
    r1 = r15 = None
    for row in data.get("nf_by_tp1_rr") or []:
        t = float(row.get("tp1_rr", 0))
        if abs(t - 1.0) < 1e-9:
            r1 = row
        if abs(t - 1.5) < 1e-9:
            r15 = row
    return r1, r15


def decide_nf_tp1_arbitration(
    *,
    expectancy_1p00: float,
    expectancy_1p50: float,
    sum_r_1p00: float,
    sum_r_1p50: float,
    nf_trades_1p00: int,
    nf_trades_1p50: int,
    epsilon_er: float = EPSILON_ER,
) -> Tuple[str, str]:
    """
    Retourne (code décision, raison courte).
    Codes : KEEP_1P0R | SWITCH_TO_1P5R | KEEP_BOTH_UNRESOLVED_PENDING_MORE_DATA
    """
    if nf_trades_1p00 == 0 and nf_trades_1p50 == 0:
        return "KEEP_BOTH_UNRESOLVED_PENDING_MORE_DATA", "aucun trade NF sur les deux bras"
    # Écart de cardinal : diagnostiqué via analyze_nf_trade_count_alignment (manifest / decision),
    # sans blocage dur — voir PHASE_NF_TP1_ARBITRATION.md.
    de = expectancy_1p50 - expectancy_1p00
    ds = sum_r_1p50 - sum_r_1p00
    if abs(de) < epsilon_er:
        return (
            "KEEP_BOTH_UNRESOLVED_PENDING_MORE_DATA",
            f"|ΔE[R]|={abs(de):.4f}R < seuil {epsilon_er}R (zone équivalence)",
        )
    if de >= epsilon_er and ds > 0:
        return "SWITCH_TO_1P5R", f"ΔE[R]={de:+.4f}R, ΔΣR={ds:+.4f}R"
    if de <= -epsilon_er and ds < 0:
        return "KEEP_1P0R", f"ΔE[R]={de:+.4f}R, ΔΣR={ds:+.4f}R"
    return (
        "KEEP_BOTH_UNRESOLVED_PENDING_MORE_DATA",
        f"contradiction ΔE[R]={de:+.4f}R vs ΔΣR={ds:+.4f}R",
    )


def _build_paired_rows() -> Tuple[List[Dict[str, Any]], List[str]]:
    """Une ligne par fenêtre attendue dans NF_TP1_ARBITRATION_WINDOWS si la paire est complète."""
    errors: List[str] = []
    rows: List[Dict[str, Any]] = []
    for preset, label in NF_TP1_ARBITRATION_WINDOWS:
        st = pair_status(MINI_WEEK, preset, label)
        if st["status"] != "complete":
            errors.append(f"pair {preset}/{label} incomplete ({st['status']})")
            continue
        c0, c1 = st["campaign_1p00"], st["campaign_1p50"]
        p0 = trades_parquet_path(MINI_WEEK, c0, label)
        p1 = trades_parquet_path(MINI_WEEK, c1, label)
        m0 = _nf_trade_metrics(pd.read_parquet(p0))
        m1 = _nf_trade_metrics(pd.read_parquet(p1))
        s0 = _load_summary(c0, label) or {}
        s1 = _load_summary(c1, label) or {}
        e0w = m0["expectancy_r"] - m1["expectancy_r"]
        rows.append(
            {
                "preset_month": preset,
                "label": label,
                "campaign_1p00": c0,
                "campaign_1p50": c1,
                "git_sha_1p00": s0.get("git_sha"),
                "git_sha_1p50": s1.get("git_sha"),
                "playbooks_yaml_1p00": s0.get("playbooks_yaml"),
                "playbooks_yaml_1p50": s1.get("playbooks_yaml"),
                "nf_tp1_rr_meta_1p00": s0.get("nf_tp1_rr_meta"),
                "nf_tp1_rr_meta_1p50": s1.get("nf_tp1_rr_meta"),
                "trades_1p00": m0["trades"],
                "trades_1p50": m1["trades"],
                "trade_count_delta_abs": abs(m0["trades"] - m1["trades"]),
                "winrate_1p00": m0["winrate_pct"],
                "winrate_1p50": m1["winrate_pct"],
                "sum_r_1p00": m0["sum_r"],
                "sum_r_1p50": m1["sum_r"],
                "expectancy_1p00": m0["expectancy_r"],
                "expectancy_1p50": m1["expectancy_r"],
                "pct_tp_1p00": m0["pct_tp"],
                "pct_tp_1p50": m1["pct_tp"],
                "pct_sl_1p00": m0["pct_sl"],
                "pct_sl_1p50": m1["pct_sl"],
                "pct_session_end_1p00": m0["pct_session_end"],
                "pct_session_end_1p50": m1["pct_session_end"],
                "median_dur_1p00": m0["median_duration_min"],
                "median_dur_1p50": m1["median_duration_min"],
                "delta_expectancy_1p50_minus_1p00": -e0w,
                "delta_sum_r_1p50_minus_1p00": m1["sum_r"] - m0["sum_r"],
                "exit_counts_1p00": m0["exit_reason_counts"],
                "exit_counts_1p50": m1["exit_reason_counts"],
            }
        )
    return rows, errors


def _rollup(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    t0 = sum(int(r["trades_1p00"]) for r in rows)
    t1 = sum(int(r["trades_1p50"]) for r in rows)
    sr0 = sum(float(r["sum_r_1p00"]) for r in rows)
    sr1 = sum(float(r["sum_r_1p50"]) for r in rows)
    e0 = (sr0 / t0) if t0 else None
    e1 = (sr1 / t1) if t1 else None
    wins_15 = sum(1 for r in rows if r["expectancy_1p50"] > r["expectancy_1p00"] + 1e-12)
    wins_00 = sum(1 for r in rows if r["expectancy_1p00"] > r["expectancy_1p50"] + 1e-12)
    ties = len(rows) - wins_15 - wins_00
    return {
        "windows_paired": len(rows),
        "nf_trades_total_1p00": t0,
        "nf_trades_total_1p50": t1,
        "sum_r_total_1p00": round(sr0, 6),
        "sum_r_total_1p50": round(sr1, 6),
        "expectancy_r_1p00": e0,
        "expectancy_r_1p50": e1,
        "weeks_expectancy_better_1p50": wins_15,
        "weeks_expectancy_better_1p00": wins_00,
        "weeks_expectancy_tie": ties,
    }


def _fmt_er(v: Optional[float]) -> str:
    return f"{v:.4f}" if v is not None else "n/a"


def _md_table(
    rows: List[Dict[str, Any]],
    roll: Dict[str, Any],
    decision: Dict[str, Any],
    manifest: Dict[str, Any],
) -> str:
    miss = manifest.get("pairs_missing") or []
    lines = [
        "# Arbitrage NF tp1 — 1.0R vs 1.5R (aug + sep + oct 2025)",
        "",
        "## Campagne (manifest)",
        "",
        f"- **statut global** : `{manifest.get('global_status')}`",
        f"- **paires complètes** : {manifest.get('complete_pair_count')}/{manifest.get('expected_pair_count')}",
        f"- **manquantes** : {', '.join(miss) if miss else '—'}",
        "",
        f"**Décision** : `{decision['decision']}` — {decision['reason']}",
        "",
    ]
    warn = decision.get("warnings") or []
    if warn:
        lines.append("### Avertissements")
        for w in warn:
            lines.append(f"- {w}")
        lines.append("")
    ta = decision.get("trade_count_alignment") or {}
    if ta:
        lines.append("### Alignement nombre de trades NF (agrégat)")
        pct = ta.get("delta_pct_of_max")
        pct_s = f"{float(pct) * 100:.2f}%" if pct is not None else "n/a"
        lines.append(
            f"- niveau `{ta.get('alignment_level')}` — Δ={ta.get('delta_abs')} ({pct_s} du max)"
        )
        lines.append("")
    lines.extend(
        [
            "## Totaux (fenêtres appariées)",
            "",
            "| métrique | 1.0R | 1.5R |",
            "|---|---:|---:|",
            f"| fenêtres | {roll['windows_paired']} | {roll['windows_paired']} |",
            f"| NF trades | {roll['nf_trades_total_1p00']} | {roll['nf_trades_total_1p50']} |",
            f"| ΣR | {roll['sum_r_total_1p00']:.4f} | {roll['sum_r_total_1p50']:.4f} |",
            f"| E[R] | {_fmt_er(roll['expectancy_r_1p00'])} | {_fmt_er(roll['expectancy_r_1p50'])} |",
            f"| semaines E[R] meilleur | {roll['weeks_expectancy_better_1p00']} | {roll['weeks_expectancy_better_1p50']} |",
            "",
            "## Par fenêtre",
            "",
            "| mois | label | trades 1.0/1.5 | WR% 1.0 / 1.5 | ΣR 1.0 / 1.5 | E[R] 1.0 / 1.5 | %TP | %SL | %sess_end |",
            "|---|---|---:|---|---|---|---|---|---|",
        ]
    )
    for r in rows:
        lines.append(
            f"| {r['preset_month']} | {r['label']} | {r['trades_1p00']}/{r['trades_1p50']} | "
            f"{r['winrate_1p00']:.1f} / {r['winrate_1p50']:.1f} | "
            f"{r['sum_r_1p00']:.2f} / {r['sum_r_1p50']:.2f} | "
            f"{r['expectancy_1p00']:.3f} / {r['expectancy_1p50']:.3f} | "
            f"{r['pct_tp_1p00']:.0f}/{r['pct_tp_1p50']:.0f} | "
            f"{r['pct_sl_1p00']:.0f}/{r['pct_sl_1p50']:.0f} | "
            f"{r['pct_session_end_1p00']:.0f}/{r['pct_session_end_1p50']:.0f} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out-json",
        type=str,
        default=str(MINI_WEEK / "_nf_tp1_arbitration_aggregate.json"),
    )
    parser.add_argument("--out-md", type=str, default="")
    parser.add_argument(
        "--epsilon-er",
        type=float,
        default=EPSILON_ER,
        help="Seuil |ΔE[R]| minimum pour trancher (défaut 0.015)",
    )
    args = parser.parse_args()

    manifest = build_campaign_manifest(mini_week=MINI_WEEK)
    CAMPAIGN_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    CAMPAIGN_MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(
        f"[nf_tp1_arb] manifest {manifest['global_status']} "
        f"{manifest['complete_pair_count']}/{manifest['expected_pair_count']} -> {CAMPAIGN_MANIFEST_PATH}",
        flush=True,
    )

    rows, errors = _build_paired_rows()
    roll = _rollup(rows)
    alignment = analyze_nf_trade_count_alignment(
        int(roll["nf_trades_total_1p00"]),
        int(roll["nf_trades_total_1p50"]),
    )
    roll["trade_count_alignment"] = alignment

    warnings: List[str] = []
    if alignment["alignment_level"] in ("moderate", "major"):
        warnings.extend(alignment["notes"])

    ref1, ref15 = _phase_b_rows()
    if len(rows) < 12:
        dcode = "KEEP_BOTH_UNRESOLVED_PENDING_MORE_DATA"
        dreason = f"paires complètes={len(rows)}/12 requis (voir eligibility_errors)"
    elif roll["expectancy_r_1p00"] is None or roll["expectancy_r_1p50"] is None:
        dcode = "KEEP_BOTH_UNRESOLVED_PENDING_MORE_DATA"
        dreason = "E[R] indéfini (trades NF nuls sur un bras)"
    else:
        dcode, dreason = decide_nf_tp1_arbitration(
            expectancy_1p00=float(roll["expectancy_r_1p00"]),
            expectancy_1p50=float(roll["expectancy_r_1p50"]),
            sum_r_1p00=float(roll["sum_r_total_1p00"]),
            sum_r_1p50=float(roll["sum_r_total_1p50"]),
            nf_trades_1p00=int(roll["nf_trades_total_1p00"]),
            nf_trades_1p50=int(roll["nf_trades_total_1p50"]),
            epsilon_er=float(args.epsilon_er),
        )

    decision_block: Dict[str, Any] = {
        "decision": dcode,
        "reason": dreason,
        "epsilon_er": float(args.epsilon_er),
        "epsilon_er_rationale": EPSILON_ER_RATIONALE,
        "eligibility_errors": errors,
        "warnings": warnings,
        "trade_count_alignment": alignment,
    }
    out_path = Path(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "reference_phase_b_nov2025": {"tp1_1p00": ref1, "tp1_1p50": ref15},
        "methodology_note": (
            "Comparaison sur YAML dérivés playbooks_nf_tp1_1p00 / 1p50 (seul News_Fade change). "
            "Les dossiers nf1r_confirm_* (playbooks_yaml null) ne prouvent pas tp1=1.0 au moteur."
        ),
        "campaign_manifest_path": str(CAMPAIGN_MANIFEST_PATH),
        "campaign_manifest": manifest,
        "rollup_paired_windows": roll,
        "decision": decision_block,
        "paired_window_rows": rows,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[nf_tp1_arb] wrote {out_path} paired={len(rows)} decision={dcode}", flush=True)

    if args.out_md:
        md_path = Path(args.out_md)
        if not md_path.is_absolute():
            md_path = backend_dir / md_path
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(_md_table(rows, roll, decision_block, manifest), encoding="utf-8")
        print(f"[nf_tp1_arb] wrote {md_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
