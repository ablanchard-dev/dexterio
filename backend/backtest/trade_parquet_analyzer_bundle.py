"""
Registre d'analyzers post-parquet (pattern Backtrader « analyzers », sans framework).

Chaque entrée produit un dict JSON-serialisable à partir d'un fichier trades
(éventuellement filtré par playbook). Réutilise `summarize_trades_parquet` pour
l'analyzer canonique `summary_r`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd

from backtest.trade_parquet_analysis import summarize_trades_parquet

AnalyzerFn = Callable[[Path, Optional[str]], Dict[str, Any]]


def _analyzer_summary_r(path: Path, playbook: Optional[str]) -> Dict[str, Any]:
    return summarize_trades_parquet(path, playbook=playbook)


def _analyzer_exit_reason_mix(path: Path, playbook: Optional[str]) -> Dict[str, Any]:
    df = pd.read_parquet(path)
    if playbook is not None and "playbook" in df.columns:
        df = df[df["playbook"] == playbook]
    if df.empty or "exit_reason" not in df.columns:
        return {"trades": int(len(df)), "exit_reason_counts": {}}
    reasons = df["exit_reason"].fillna("").astype(str)
    vc = reasons.value_counts()
    return {
        "trades": int(len(df)),
        "exit_reason_counts": {str(k): int(v) for k, v in vc.items()},
    }


def _analyzer_playbook_counts(path: Path, playbook: Optional[str]) -> Dict[str, Any]:
    """Effectifs par playbook (ignore le filtre `playbook` : vue globale du fichier)."""
    df = pd.read_parquet(path)
    if "playbook" not in df.columns:
        return {"playbook_counts": {}}
    vc = df["playbook"].astype(str).value_counts()
    return {"playbook_counts": {str(k): int(v) for k, v in vc.items()}}


# Enregistrement explicite : clés stables pour scripts / rapports.
ANALYZER_REGISTRY: Dict[str, AnalyzerFn] = {
    "summary_r": _analyzer_summary_r,
    "exit_reason_mix": _analyzer_exit_reason_mix,
    "playbook_counts": _analyzer_playbook_counts,
}


def list_analyzers() -> Tuple[str, ...]:
    return tuple(sorted(ANALYZER_REGISTRY.keys()))


def run_parquet_analyzer_bundle(
    path: Path | str,
    *,
    playbook: Optional[str] = None,
    names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Exécute un ou plusieurs analyzers sur le même parquet.

    Args:
        path: fichier trades parquet.
        playbook: si défini, passé aux analyzers qui supportent un filtre (summary_r, exit_reason_mix).
        names: sous-ensemble d'analyzers ; défaut = tous les enregistrés.

    Returns:
        { "meta": {...}, "results": { analyzer_name: dict } }
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(str(p))
    keys = list(names) if names is not None else list(ANALYZER_REGISTRY.keys())
    unknown = [k for k in keys if k not in ANALYZER_REGISTRY]
    if unknown:
        raise KeyError(
            f"analyzers inconnus: {unknown} — disponibles: {list_analyzers()}"
        )
    results: Dict[str, Any] = {}
    for k in keys:
        results[k] = ANALYZER_REGISTRY[k](p, playbook)
    return {
        "meta": {
            "path": str(p.resolve()),
            "playbook_filter": playbook,
            "analyzers_run": keys,
        },
        "results": results,
    }
