"""
Spécification campagne arbitrage NF tp1 1.0R vs 1.5R (aug / sep / oct 2025).

Les paires DOIVENT rester alignées sur `scripts/run_mini_lab_multiweek.PRESETS`
pour les clés aug2025, sep2025, oct2025 (labels et dates identiques).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

# (preset_multiweek, label) — 12 entrées. Sync: run_mini_lab_multiweek.PRESETS.
NF_TP1_ARBITRATION_WINDOWS: List[Tuple[str, str]] = [
    ("aug2025", "202508_w01"),
    ("aug2025", "202508_w02"),
    ("aug2025", "202508_w03"),
    ("aug2025", "202508_w04"),
    ("sep2025", "202509_w01"),
    ("sep2025", "202509_w02"),
    ("sep2025", "202509_w03"),
    ("sep2025", "202509_w04"),
    ("oct2025", "202510_w01"),
    ("oct2025", "202510_w02"),
    ("oct2025", "202510_w03"),
    ("oct2025", "202510_w04"),
]

PREFIX_1P00 = "nf_tp1_arb_1p00_"
PREFIX_1P50 = "nf_tp1_arb_1p50_"


def campaign_dir_names(preset: str) -> Tuple[str, str]:
    return f"{PREFIX_1P00}{preset}", f"{PREFIX_1P50}{preset}"


def trades_parquet_path(mini_week: Path, campaign: str, label: str) -> Path:
    run_id = f"miniweek_{campaign}_{label}"
    return mini_week / campaign / label / f"trades_{run_id}_AGGRESSIVE_DAILY_SCALP.parquet"


def summary_path(mini_week: Path, campaign: str, label: str) -> Path:
    return mini_week / campaign / label / f"mini_lab_summary_{label}.json"


def pair_status(mini_week: Path, preset: str, label: str) -> Dict[str, Any]:
    c0, c1 = campaign_dir_names(preset)
    s0 = summary_path(mini_week, c0, label)
    s1 = summary_path(mini_week, c1, label)
    p0 = trades_parquet_path(mini_week, c0, label)
    p1 = trades_parquet_path(mini_week, c1, label)
    ok_s0, ok_s1 = s0.is_file(), s1.is_file()
    ok_p0, ok_p1 = p0.is_file(), p1.is_file()
    complete = ok_s0 and ok_s1 and ok_p0 and ok_p1
    if complete:
        st = "complete"
    elif not ok_s0 and not ok_s1 and not ok_p0 and not ok_p1:
        st = "missing_both"
    elif not ok_s0 or not ok_p0:
        st = "incomplete_1p00"
    elif not ok_s1 or not ok_p1:
        st = "incomplete_1p50"
    else:
        st = "incomplete"
    return {
        "preset": preset,
        "label": label,
        "campaign_1p00": c0,
        "campaign_1p50": c1,
        "status": st,
        "paths": {
            "summary_1p00": str(s0),
            "summary_1p50": str(s1),
            "parquet_1p00": str(p0),
            "parquet_1p50": str(p1),
        },
        "flags": {
            "has_summary_1p00": ok_s0,
            "has_summary_1p50": ok_s1,
            "has_parquet_1p00": ok_p0,
            "has_parquet_1p50": ok_p1,
        },
    }


def analyze_nf_trade_count_alignment(nf_trades_1p00: int, nf_trades_1p50: int) -> Dict[str, Any]:
    """
    Diagnostic d'écart de taille de cohorte NF entre bras (pas un blocage dur).

    Pourquoi l'égalité stricte existait avant : hypothèse « même entrées, seul TP change »
    → même cardinal de trades NF ; l'égalité évitait de trancher sur des ΣR/E[R]
    comparables à des effectifs différents (biais de composition). En pratique le moteur
    peut diverger légèrement (effets d'ordre, risk, session) : on quantifie l'écart et
    on alerte sans invalider systématiquement la décision.
    """
    n0, n1 = int(nf_trades_1p00), int(nf_trades_1p50)
    delta = abs(n0 - n1)
    mx = max(n0, n1, 1)
    pct = delta / mx
    notes: List[str] = []
    if delta == 0:
        level = "aligned"
    elif pct <= 0.05 and delta <= 2:
        level = "minor"
        notes.append("écart faible — usuel si bruit d'exécution / timing")
    elif pct <= 0.15 and delta <= 8:
        level = "moderate"
        notes.append("écart modéré — vérifier les fenêtres sources si doute")
    else:
        level = "major"
        notes.append(
            "écart important — cohortes de tailles nettement différentes ; "
            "interpréter E[R] et ΣR avec prudence (pas d'invalidation automatique)"
        )
    return {
        "nf_trades_1p00": n0,
        "nf_trades_1p50": n1,
        "delta_abs": delta,
        "delta_pct_of_max": round(pct, 6),
        "alignment_level": level,
        "notes": notes,
    }


def build_campaign_manifest(*, mini_week: Path) -> Dict[str, Any]:
    pairs = [pair_status(mini_week, preset, label) for preset, label in NF_TP1_ARBITRATION_WINDOWS]
    complete = [x for x in pairs if x["status"] == "complete"]
    missing = [x for x in pairs if x["status"] != "complete"]
    n_exp = len(NF_TP1_ARBITRATION_WINDOWS)
    n_ok = len(complete)
    if n_ok == 0:
        global_status = "NOT_STARTED"
    elif n_ok < n_exp:
        global_status = "IN_PROGRESS"
    else:
        global_status = "COMPLETE_OK"
    return {
        "schema_version": "NfTp1ArbitrationCampaignManifestV0",
        "expected_pair_count": n_exp,
        "complete_pair_count": n_ok,
        "missing_pair_count": len(missing),
        "global_status": global_status,
        "expected_pairs": [
            {"preset": pr, "label": lb, "campaign_1p00": campaign_dir_names(pr)[0], "campaign_1p50": campaign_dir_names(pr)[1]}
            for pr, lb in NF_TP1_ARBITRATION_WINDOWS
        ],
        "pairs_detail": pairs,
        "pairs_complete": [f"{x['preset']}/{x['label']}" for x in complete],
        "pairs_missing": [f"{x['preset']}/{x['label']}" for x in missing],
    }
