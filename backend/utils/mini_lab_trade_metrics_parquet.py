"""Métriques légères depuis le parquet trades mini-lab (hors moteur, après run)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

from backtest.metrics import (
    expectancy_from_r_multiples,
    gross_profit_loss_from_r_multiples,
    max_drawdown_from_pnl_r_accounts,
    profit_factor_from_gross_profit_loss,
)


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
            "max_drawdown_r": None,
        }

    n = int(len(df))
    out: Dict[str, Any] = {
        "schema_version": "MiniLabTradeMetricsParquetV0",
        "trades_rows": n,
        "parquet_path": str(p.resolve()),
    }

    # Outcome-based counters (UI/cockpit-friendly). Falls back to r_multiple sign if column absent.
    try:
        if "outcome" in df.columns:
            o = df["outcome"].astype(str).str.lower()
            wins = int((o == "win").sum())
            losses = int((o == "loss").sum())
            breakevens = int((o == "breakeven").sum())
        elif "r_multiple" in df.columns:
            r0 = pd.to_numeric(df["r_multiple"], errors="coerce")
            wins = int((r0 > 0).sum())
            losses = int((r0 < 0).sum())
            breakevens = int((r0 == 0).sum())
        else:
            wins = losses = breakevens = 0
        out["wins"] = wins
        out["losses"] = losses
        out["breakevens"] = breakevens
        out["winrate"] = float(100.0 * wins / n) if n else None
    except Exception:
        # Best-effort only; do not fail the summarizer on unexpected dtypes.
        out["wins"] = None
        out["losses"] = None
        out["breakevens"] = None
        out["winrate"] = None
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
            r_list = [float(x) for x in r.to_list()]
            mr = float(r.mean())
            out["mean_r_multiple"] = mr
            out["expectancy_r"] = expectancy_from_r_multiples(r_list)
            gp, gl = gross_profit_loss_from_r_multiples(r_list)
            out["gross_profit_r"] = gp
            out["gross_loss_r"] = gl
            out["profit_factor"] = profit_factor_from_gross_profit_loss(gp, gl)
        else:
            out["mean_r_multiple"] = None
            out["expectancy_r"] = None
            out["gross_profit_r"] = None
            out["gross_loss_r"] = None
            out["profit_factor"] = None
    else:
        out["mean_r_multiple"] = None
        out["expectancy_r"] = None
        out["gross_profit_r"] = None
        out["gross_loss_r"] = None
        out["profit_factor"] = None

    # Canonical MaxDD in R (account): drawdown on cumulative pnl_R_account.
    if "pnl_R_account" in df.columns:
        s = pd.to_numeric(df["pnl_R_account"], errors="coerce").fillna(0.0)
        out["max_drawdown_r"] = max_drawdown_from_pnl_r_accounts([float(x) for x in s.to_list()])
    else:
        out["max_drawdown_r"] = None

    return out
