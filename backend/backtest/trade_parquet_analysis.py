"""
Analyse post-hoc d'un parquet de trades (style « analyzer » Backtrader TradeAnalyzer,
sans dépendre de backtrader : agrégats simples sur colonnes Dexterio).

Usage : diagnostics labs, futures rapports ; validation ligne à ligne possible via `contracts.trade_row_v0.parse_trade_row_v0`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd


def summarize_trades_parquet(
    path: Path | str,
    *,
    playbook: Optional[str] = None,
) -> Dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(str(p))
    df = pd.read_parquet(p)
    if playbook:
        df = df[df.get("playbook") == playbook]
    n = int(len(df))
    if n == 0:
        return {"trades": 0, "winrate_pct": 0.0, "sum_r": 0.0, "expectancy_r": 0.0}
    wins = (df["outcome"] == "win").sum() if "outcome" in df.columns else 0
    rcol = df["r_multiple"] if "r_multiple" in df.columns else None
    if rcol is None:
        raise ValueError("parquet sans colonne r_multiple")
    sr = float(rcol.sum())
    return {
        "trades": n,
        "winrate_pct": float(wins / n * 100.0),
        "sum_r": sr,
        "expectancy_r": float(rcol.mean()),
    }
