"""Métriques légères depuis le parquet trades mini-lab (hors moteur, après run)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd


def summarize_trades_parquet(path: Path | str) -> Optional[Dict[str, Any]]:
    """
    Lit le parquet trades du moteur (colonnes optionnelles selon version).

    Retourne None si fichier absent ou illisible.
    `expectancy_r` = moyenne de `r_multiple` (approx. espérance en R / trade si risque ~constant).
    """
    p = Path(path)
    if not p.is_file():
        return None
    try:
        df = pd.read_parquet(p)
    except Exception:
        return None
    if df.empty:
        return {
            "schema_version": "MiniLabTradeMetricsParquetV0",
            "trades_rows": 0,
            "sum_pnl_dollars": None,
            "mean_r_multiple": None,
            "expectancy_r": None,
        }

    n = int(len(df))
    out: Dict[str, Any] = {
        "schema_version": "MiniLabTradeMetricsParquetV0",
        "trades_rows": n,
        "parquet_path": str(p.resolve()),
    }
    if "pnl_dollars" in df.columns:
        s = pd.to_numeric(df["pnl_dollars"], errors="coerce")
        out["sum_pnl_dollars"] = float(s.sum(skipna=True))
        out["mean_pnl_dollars"] = float(s.mean(skipna=True)) if n else None
    else:
        out["sum_pnl_dollars"] = None
        out["mean_pnl_dollars"] = None

    if "r_multiple" in df.columns:
        r = pd.to_numeric(df["r_multiple"], errors="coerce").dropna()
        if len(r):
            mr = float(r.mean())
            out["mean_r_multiple"] = mr
            out["expectancy_r"] = mr
        else:
            out["mean_r_multiple"] = None
            out["expectancy_r"] = None
    else:
        out["mean_r_multiple"] = None
        out["expectancy_r"] = None

    return out
