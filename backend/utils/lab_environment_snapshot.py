"""
Snapshot des variables d'environnement pertinentes pour reproductibilité lab / paper.

Inspiré de la discipline Freqtrade (config explicite, séparation dry-run / prod) :
on fige dans le manifest ce qui pilote RiskEngine / mini-lab sans importer Freqtrade.

Empreinte data (Nautilus-like : traçabilité du catalogue) : métadonnées fichiers 1m
(résolu, taille, mtime) — pas de hash complet du parquet (trop lourd).
"""
from __future__ import annotations

import hashlib
import os
from typing import Any, Dict, List, Optional, Sequence

from utils.path_resolver import discover_symbol_parquet, historical_data_path

_RISK_KEYS: List[str] = [
    "RISK_EVAL_ALLOW_ALL_PLAYBOOKS",
    "RISK_EVAL_RELAX_CAPS",
    "RISK_EVAL_DISABLE_KILL_SWITCH",
    "RISK_BYPASS_DYNAMIC_QUARANTINE_LSS_ONLY",
]


def snapshot_risk_lab_environment(*, extra_keys: Optional[List[str]] = None) -> Dict[str, Any]:
    """Valeurs courantes (ou null si absentes) — sérialisable JSON."""
    keys = list(_RISK_KEYS)
    if extra_keys:
        keys.extend(k for k in extra_keys if k not in keys)
    return {k: os.environ.get(k) for k in keys}


def compute_data_fingerprint_v0(
    symbols: Sequence[str],
    *,
    timeframe: str = "1m",
) -> Dict[str, Any]:
    """
    Identifiant reproductible des fichiers historiques utilisés par le mini-lab.
    Basé sur chemins résolus + taille + mtime (détection remplacement / MAJ data).
    """
    by_sym: Dict[str, Any] = {}
    lines: List[str] = []
    for sym in sorted({s.strip().upper() for s in symbols if s and str(s).strip()}):
        p = discover_symbol_parquet(sym, timeframe)
        if p is None:
            p = historical_data_path(timeframe, f"{sym}.parquet")
        st = p.stat() if p.is_file() else None
        mtime_ns: Optional[int]
        if st is None:
            mtime_ns = None
        else:
            mt = getattr(st, "st_mtime_ns", None)
            if mt is not None:
                mtime_ns = int(mt)
            else:
                mtime_ns = int(st.st_mtime * 1_000_000_000)
        rec = {
            "path": str(p.resolve()) if p is not None else None,
            "exists": st is not None,
            "size_bytes": int(st.st_size) if st else None,
            "mtime_ns": mtime_ns,
        }
        by_sym[sym] = rec
        lines.append(
            f"{sym}|{rec['path']}|{rec['exists']}|{rec['size_bytes']}|{rec['mtime_ns']}"
        )
    blob = "\n".join(lines).encode("utf-8")
    full = hashlib.sha256(blob).hexdigest()
    return {
        "schema_version": "DataFingerprintV0",
        "timeframe": timeframe,
        "sha256": full,
        "by_symbol": by_sym,
    }


def build_lab_environment_for_manifest(
    symbols: Sequence[str],
    *,
    extra_keys: Optional[List[str]] = None,
    include_data_fingerprint: bool = True,
) -> Dict[str, Any]:
    """Fusionne env risk + empreinte data pour `run_manifest.json` (`lab_environment`)."""
    env = snapshot_risk_lab_environment(extra_keys=extra_keys)
    if include_data_fingerprint and os.environ.get("DEXTERIO_OMIT_DATA_FINGERPRINT", "").lower() not in (
        "1",
        "true",
        "yes",
    ):
        env = dict(env)
        env["data_fingerprint_v0"] = compute_data_fingerprint_v0(symbols)
    return env
