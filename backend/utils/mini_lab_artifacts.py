"""Chemins d'artefacts standardisés mini-lab (alignés sur BacktestEngine._save_results)."""
from __future__ import annotations

from pathlib import Path
from typing import Sequence


def trades_parquet_path(
    output_dir: Path | str,
    run_id: str,
    trading_mode: str,
    trade_types: Sequence[str],
) -> Path:
    """Ex. trades_miniweek_202511_w01_AGGRESSIVE_DAILY_SCALP.parquet"""
    out = Path(output_dir)
    tt = "_".join(trade_types)
    return out / f"trades_{run_id}_{trading_mode}_{tt}.parquet"
