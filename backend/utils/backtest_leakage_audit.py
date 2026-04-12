"""Contrôles légers anti-lookahead / cohérence (hors hot path du moteur)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from utils.backtest_data_coverage import check_backtest_data_coverage


def audit_trades_parquet_temporal(path: Path | str) -> Dict[str, Any]:
    """
    Vérifie timestamp_entry <= timestamp_exit sur lignes avec les deux champs renseignés.
    """
    p = Path(path)
    errors: List[str] = []
    warnings: List[str] = []
    if not p.is_file():
        return {"ok": False, "path": str(p), "errors": [f"fichier absent: {p}"], "warnings": []}
    try:
        df = pd.read_parquet(p, columns=["timestamp_entry", "timestamp_exit"])
    except Exception as e:
        try:
            df = pd.read_parquet(p)
        except Exception as e2:
            return {"ok": False, "path": str(p), "errors": [f"lecture parquet: {e2}"], "warnings": []}
        if "timestamp_entry" not in df.columns or "timestamp_exit" not in df.columns:
            return {
                "ok": False,
                "path": str(p),
                "errors": [f"colonnes timestamp_entry/timestamp_exit manquantes ({e})"],
                "warnings": [],
            }
    te = pd.to_datetime(df["timestamp_entry"], utc=True, errors="coerce")
    tx = pd.to_datetime(df["timestamp_exit"], utc=True, errors="coerce")
    both = te.notna() & tx.notna()
    if both.any():
        bad = both & (tx < te)
        n_bad = int(bad.sum())
        if n_bad:
            errors.append(f"{n_bad} ligne(s) avec timestamp_exit < timestamp_entry")
    else:
        warnings.append("aucune ligne avec entry et exit non nuls — audit temporel vide")
    return {"ok": len(errors) == 0, "path": str(p.resolve()), "errors": errors, "warnings": warnings}


def audit_ohlcv_parquet_monotonic(path: Path | str, datetime_col: str = "datetime") -> Dict[str, Any]:
    """Vérifie ordre chronologique et absence de doublons sur la colonne datetime."""
    p = Path(path)
    errors: List[str] = []
    warnings: List[str] = []
    if not p.is_file():
        return {"ok": False, "path": str(p), "errors": [f"fichier absent: {p}"], "warnings": []}
    try:
        d = pd.read_parquet(p, columns=[datetime_col])
    except Exception:
        d = pd.read_parquet(p)
        if datetime_col not in d.columns:
            return {
                "ok": False,
                "path": str(p),
                "errors": [f"colonne {datetime_col!r} absente"],
                "warnings": [],
            }
    t = pd.to_datetime(d[datetime_col], utc=True, errors="coerce")
    t = t.dropna()
    if len(t) < 2:
        warnings.append("moins de 2 timestamps — skip monotonic")
        return {"ok": True, "path": str(p.resolve()), "errors": [], "warnings": warnings}
    if not t.is_monotonic_increasing:
        errors.append("datetime non strictement croissante (tri attendu)")
    dup = int(t.duplicated().sum())
    if dup:
        errors.append(f"{dup} datetime dupliqué(s)")
    return {"ok": len(errors) == 0, "path": str(p.resolve()), "errors": errors, "warnings": warnings}


def run_backtest_leakage_audit_bundle(
    *,
    trades_parquet: Optional[Path | str] = None,
    data_parquets: Optional[List[Path | str]] = None,
    symbols: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    htf_warmup_days: int = 0,
) -> Dict[str, Any]:
    """
    Agrège plusieurs audits. `data_parquets` + fenêtre : réutilise `check_backtest_data_coverage`
    (pas de lookahead bar-by-bar — garde-fou données vs fenêtre de run).
    """
    parts: Dict[str, Any] = {}
    if trades_parquet:
        parts["trades_temporal"] = audit_trades_parquet_temporal(trades_parquet)
    if data_parquets and symbols and start_date and end_date:
        parts["data_window_coverage"] = check_backtest_data_coverage(
            data_paths=[str(Path(x)) for x in data_parquets],
            symbols=list(symbols),
            start_date=start_date,
            end_date=end_date,
            htf_warmup_days=htf_warmup_days,
            max_gap_warn_minutes=None,
        )
    elif data_parquets:
        parts["data_ohlcv"] = [audit_ohlcv_parquet_monotonic(x) for x in data_parquets]

    ok = True
    if "trades_temporal" in parts and not parts["trades_temporal"].get("ok", True):
        ok = False
    cov = parts.get("data_window_coverage")
    if isinstance(cov, dict) and not cov.get("ok", True):
        ok = False
    for item in parts.get("data_ohlcv") or []:
        if isinstance(item, dict) and not item.get("ok", True):
            ok = False
    return {"schema_version": "BacktestLeakageAuditBundleV0", "ok": ok, "parts": parts}
