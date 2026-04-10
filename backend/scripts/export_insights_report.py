"""
Consolide les exports déjà produits (leaderboard, labo, sanity, résumés) en un seul rapport JSON + texte.

Usage (depuis backend/) :
  python scripts/export_insights_report.py
  python scripts/export_insights_report.py --lab-subdir labs/full_playbooks_24m

Ne dépend pas de Wave 1 : utile quand la shortlist est vide mais qu'on veut
prioriser quarantaine, playbooks à diagnostiquer, et anomalies sanity.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from scripts.playbook_lab_utils import aggregate_playbook_stats  # noqa: E402
from utils.path_resolver import results_path  # noqa: E402


def _read_json(p: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _latest_match(root: Path, glob_pat: str) -> Optional[Path]:
    matches = sorted(root.glob(glob_pat), key=lambda x: x.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def _sanity_digest(payload: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {"status": payload.get("status"), "run_id": payload.get("run_id")}
    dur = payload.get("duration_validation") or {}
    scalp = dur.get("scalp") or {}
    out["scalp_time_stop_broken"] = bool(scalp.get("time_stop_broken"))
    out["scalp_violations_sample"] = len(scalp.get("violations") or [])
    ep = payload.get("entry_price_validation") or {}
    out["placeholder_entries"] = bool(ep.get("placeholder_detected"))
    la = payload.get("lookahead_detector") or payload.get("lookahead") or {}
    if isinstance(la, dict) and la.get("pass") is not None:
        out["lookahead_pass"] = la.get("pass")
    return {k: v for k, v in out.items() if v is not None}


def _summary_digest(payload: Dict[str, Any]) -> Dict[str, Any]:
    keys = (
        "final_capital",
        "initial_capital",
        "total_trades",
        "total_pnl_r",
        "winrate",
        "profit_factor",
        "expectancy_r",
        "max_drawdown_r",
    )
    return {k: payload.get(k) for k in keys if payload.get(k) is not None}


def main() -> None:
    parser = argparse.ArgumentParser(description="Rapport unique depuis exports results/")
    parser.add_argument(
        "--lab-subdir",
        type=str,
        default="labs/full_playbooks_24m",
        help="Sous-dossier results/ contenant lab_windows_index + playbook_stats",
    )
    parser.add_argument(
        "--leaderboard",
        type=str,
        default="playbooks_leaderboard_24m.json",
        help="Fichier sous results/",
    )
    args = parser.parse_args()

    root = results_path()
    lab_dir = root / args.lab_subdir
    lb_path = root / args.leaderboard

    report: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results_root": str(root),
        "sources": {},
    }

    rows: List[Dict[str, Any]] = []
    if lb_path.exists():
        raw = _read_json(lb_path) or {}
        rows = list(raw.get("rows") or [])
        report["sources"]["leaderboard"] = str(lb_path)
        report["leaderboard_meta"] = {
            "windows_count": raw.get("windows_count"),
            "rows_count": len(rows),
        }
    else:
        report["sources"]["leaderboard"] = None
        report["note"] = f"Leaderboard absent: {lb_path}"

    # Agrégat direct depuis les playbook_stats du lab (si index présent)
    lab_files: List[Path] = []
    idx_path = lab_dir / "lab_windows_index.json"
    if idx_path.exists():
        idx = _read_json(idx_path) or {}
        for w in idx.get("windows") or []:
            p = Path(w.get("playbook_stats_file") or "")
            if p.is_file():
                lab_files.append(p)
        report["sources"]["lab_windows_index"] = str(idx_path)
        report["lab_meta"] = {
            "windows_in_index": len(idx.get("windows") or []),
            "playbook_stats_files_found": len(lab_files),
        }

    aggregated: List[Dict[str, Any]] = []
    if lab_files:
        aggregated = aggregate_playbook_stats(lab_files)
        report["sources"]["aggregated_from_lab"] = [str(p) for p in lab_files]

    # Utiliser agrégat lab si dispo, sinon leaderboard
    base_rows = aggregated if aggregated else rows

    enriched: List[Dict[str, Any]] = []
    for r in base_rows:
        tr = int(r.get("trades", 0) or 0)
        tr_net = float(r.get("total_r_net", 0.0) or 0.0)
        ex = r.get("expectancy_r")
        if ex is None and tr > 0:
            ex = tr_net / tr
        enriched.append(
            {
                "playbook": r.get("playbook"),
                "trades": tr,
                "total_r_net": tr_net,
                "profit_factor": float(r.get("profit_factor", 0.0) or 0.0),
                "winrate": float(r.get("winrate", 0.0) or 0.0),
                "stability_score": float(r.get("stability_score", 0.0) or 0.0),
                "expectancy_r": float(ex) if ex is not None else 0.0,
            }
        )

    enriched.sort(key=lambda x: x["total_r_net"])

    worst = enriched[:8]
    best = list(reversed(enriched[-8:])) if len(enriched) > 8 else list(reversed(enriched))

    drainers = [x for x in enriched if x["total_r_net"] <= -3.0 and x["trades"] >= 15]
    maybe_ok = [x for x in enriched if x["total_r_net"] > 0 and x["trades"] >= 10]

    recommendations: List[str] = []
    if not maybe_ok:
        recommendations.append(
            "Aucun playbook ne sort clairement du lot avec R net > 0 et volume suffisant — "
            "Wave 1 vide est attendu; prioriser réduction du scope (moins de playbooks) ou recherche de setups."
        )
    else:
        recommendations.append(
            f"Playbooks à analyser en priorité (R net > 0, trades >= 10): {', '.join(p['playbook'] for p in maybe_ok[:5])}."
        )
    if drainers:
        recommendations.append(
            "Fortes pertes cumulées — examiner désactivation / quarantaine: "
            + ", ".join(d["playbook"] for d in drainers[:5])
        )

    sanity_path = _latest_match(lab_dir, "sanity_report*.json")
    sanity_digest: Optional[Dict[str, Any]] = None
    if sanity_path and sanity_path.exists():
        sp = _read_json(sanity_path) or {}
        sanity_digest = _sanity_digest(sp)
        report["sources"]["sanity_report"] = str(sanity_path)
        if sanity_digest.get("scalp_time_stop_broken"):
            recommendations.append(
                "Sanity: time_stop scalp cassé — durées de trade scalps au-delà du plafond; vérifier exécution / filtres."
            )

    summary_path = _latest_match(lab_dir, "summary_*_AGGRESSIVE*.json")
    summary_d: Optional[Dict[str, Any]] = None
    if summary_path and summary_path.exists():
        sraw = _read_json(summary_path) or {}
        summary_d = _summary_digest(sraw)
        report["sources"]["summary"] = str(summary_path)

    setup_ctx_path = _latest_match(lab_dir, "setup_context_stats_*.json")
    if setup_ctx_path and setup_ctx_path.exists():
        ctx_raw = _read_json(setup_ctx_path) or {}
        rows_ctx = list(ctx_raw.get("rows") or [])
        report["sources"]["setup_context_stats"] = str(setup_ctx_path)
        report["setup_context_top_indecision"] = rows_ctx[:8]
        noisy = [r for r in rows_ctx if float(r.get("avg_indecision_ratio", 0.0) or 0.0) >= 0.55]
        if noisy:
            recommendations.append(
                "Setups souvent générés en marché indécis (avg_indecision_ratio >= 0.55) : "
                + ", ".join(str(x.get("playbook")) for x in noisy[:5])
            )

    dbg_path = _latest_match(lab_dir, "debug_counts_*.json")
    if dbg_path and dbg_path.exists():
        dbg_raw = _read_json(dbg_path) or {}
        report["sources"]["debug_counts"] = str(dbg_path)
        rr = dbg_raw.get("setup_engine_reject_reasons")
        if isinstance(rr, dict):
            top_rr = sorted(rr.items(), key=lambda kv: kv[1], reverse=True)[:8]
            report["setup_reject_reasons_top"] = [{"reason": k, "count": v} for k, v in top_rr]

    pf_zero = sum(1 for x in enriched if x["profit_factor"] == 0.0 and x["trades"] > 0)
    if pf_zero:
        recommendations.append(
            f"{pf_zero} ligne(s) avec profit_factor=0 — souvent gross_loss_r mal agrégé en amont; "
            "vérifier playbook_stats source ou recalculer depuis trades."
        )

    report["playbooks_worst_r"] = worst
    report["playbooks_best_r"] = best
    report["sanity"] = sanity_digest
    report["summary_snapshot"] = summary_d
    report["recommendations"] = recommendations
    report["wave1_note"] = (
        "Tant qu'aucun playbook ne dépasse des seuils réalistes (edge + volume), Wave 1 restera vide — "
        "utiliser ce rapport pour quarantaine / debug, pas pour une shortlist fictive."
    )

    out_path = root / "export_insights_report.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[insights] écrit: {out_path}")
    print()
    print("=== Recommandations ===")
    for line in recommendations:
        print(f"  - {line}")
    print()
    print("=== Pires playbooks (R net cumulé) ===")
    for x in worst[:5]:
        print(
            f"  {x['playbook']}: {x['total_r_net']:.2f} R, {x['trades']} trades, PF={x['profit_factor']:.3f}"
        )
    print()
    print("=== Moins mauvais / positifs ===")
    for x in best[:5]:
        print(
            f"  {x['playbook']}: {x['total_r_net']:.2f} R, {x['trades']} trades, PF={x['profit_factor']:.3f}"
        )
    if sanity_digest:
        print()
        print("=== Sanity (extrait) ===")
        for k, v in sanity_digest.items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
