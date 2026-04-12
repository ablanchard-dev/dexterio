"""
Vérification légère de la couverture temporelle des parquets 1m pour le backtest.

Inspiration Freqtrade / Nautilus : valider les données **avant** un run long,
sans relire toute la logique du `BacktestEngine`.

Aligné sur le découpe `BacktestEngine.load_data` : `end_date` est **inclusive**
(coupure exclusive à J+1 00:00 UTC).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd


def _read_datetime_column(path: Path) -> pd.Series:
    """Lit uniquement la colonne datetime si possible (évite charger OHLCV complet)."""
    try:
        df = pd.read_parquet(path, columns=["datetime"])
    except Exception:
        df = pd.read_parquet(path)
    if isinstance(df.index, pd.DatetimeIndex):
        s = pd.to_datetime(df.index, utc=True)
        return pd.Series(s)
    if "datetime" not in df.columns:
        raise ValueError(f"Pas de colonne 'datetime' dans {path}")
    s = pd.to_datetime(df["datetime"], utc=True, errors="coerce")
    if s.dt.tz is None:
        s = s.dt.tz_localize("UTC")
    else:
        s = s.dt.tz_convert("UTC")
    return s


def parquet_datetime_bounds(path: Path | str) -> Dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        return {"path": str(p), "exists": False, "min_utc": None, "max_utc": None, "rows": 0}
    s = _read_datetime_column(p)
    s = s.dropna().sort_values()
    if s.empty:
        return {"path": str(p.resolve()), "exists": True, "min_utc": None, "max_utc": None, "rows": 0}
    return {
        "path": str(p.resolve()),
        "exists": True,
        "min_utc": s.min().isoformat(),
        "max_utc": s.max().isoformat(),
        "rows": int(len(s)),
    }


def _bounds_to_window(
    start_date: str,
    end_date: str,
    *,
    htf_warmup_days: int,
) -> Tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp]:
    """Retourne (warmup_start, start_dt inclusive, end_exclusive) en UTC."""
    start_raw = pd.to_datetime(start_date)
    start_dt = start_raw.tz_localize("UTC") if start_raw.tz is None else start_raw.tz_convert("UTC")
    end_raw = pd.to_datetime(end_date)
    end_dt = end_raw.tz_localize("UTC") if end_raw.tz is None else end_raw.tz_convert("UTC")
    end_excl = end_dt + pd.Timedelta(days=1)
    warmup_start = start_dt - pd.Timedelta(days=max(0, int(htf_warmup_days)))
    return warmup_start, start_dt, end_excl


def max_intraday_gap_minutes(datetimes: pd.Series) -> Optional[float]:
    """Écart max entre barres consécutives (minutes). Utile pour détecter trous 1m."""
    if datetimes is None or len(datetimes) < 2:
        return None
    s = pd.to_datetime(datetimes, utc=True).sort_values()
    delta = s.diff().dt.total_seconds().div(60.0)
    return float(delta.max())


def check_backtest_data_coverage(
    *,
    data_paths: Sequence[str],
    symbols: Sequence[str],
    start_date: str,
    end_date: str,
    htf_warmup_days: int = 0,
    max_gap_warn_minutes: Optional[float] = 6.0,
) -> Dict[str, Any]:
    """
    Vérifie que chaque parquet couvre [warmup_start, end_exclusive) en min/max
    et signale les grands trous intra-fichier (1m).

    Returns:
        dict avec ok (bool), by_path, warnings, errors.
    """
    warmup_start, start_dt, end_excl = _bounds_to_window(
        start_date, end_date, htf_warmup_days=htf_warmup_days
    )
    errors: List[str] = []
    warnings: List[str] = []
    by_path: List[Dict[str, Any]] = []

    if len(data_paths) != len(symbols):
        errors.append(
            f"data_paths ({len(data_paths)}) et symbols ({len(symbols)}) doivent avoir la même longueur"
        )
        return {
            "ok": False,
            "warmup_start_utc": warmup_start.isoformat(),
            "start_utc": start_dt.isoformat(),
            "end_exclusive_utc": end_excl.isoformat(),
            "by_path": [],
            "warnings": warnings,
            "errors": errors,
        }

    for sym, pstr in zip(symbols, data_paths):
        p = Path(pstr)
        meta = parquet_datetime_bounds(p)
        meta["symbol"] = sym
        if not meta["exists"]:
            errors.append(f"{sym}: fichier manquant {p}")
            by_path.append(meta)
            continue
        if meta["rows"] == 0:
            errors.append(f"{sym}: parquet vide {p}")
            by_path.append(meta)
            continue
        tmin = pd.Timestamp(meta["min_utc"])
        tmax = pd.Timestamp(meta["max_utc"])
        if tmin > warmup_start:
            errors.append(
                f"{sym}: min datetime {tmin} > warmup_start {warmup_start} "
                f"(besoin de données pour warmup HTF si htf_warmup_days={htf_warmup_days})"
            )
        if tmax < end_excl - pd.Timedelta(seconds=1):
            # Dernière barre strictement avant la fin de fenêtre demandée
            errors.append(
                f"{sym}: max datetime {tmax} < fin de fenêtre attendue ({end_excl} exclus) — données trop courtes"
            )
        if max_gap_warn_minutes is not None:
            try:
                s = _read_datetime_column(p)
                mg = max_intraday_gap_minutes(s)
                meta["max_gap_minutes"] = mg
                if mg is not None and mg > float(max_gap_warn_minutes):
                    warnings.append(
                        f"{sym}: écart max entre barres ≈ {mg:.1f} min (> {max_gap_warn_minutes}) — vérifier trous 1m"
                    )
            except Exception as e:
                warnings.append(f"{sym}: impossible d'analyser les gaps ({e})")
        by_path.append(meta)

    ok = len(errors) == 0
    return {
        "ok": ok,
        "warmup_start_utc": warmup_start.isoformat(),
        "start_utc": start_dt.isoformat(),
        "end_exclusive_utc": end_excl.isoformat(),
        "htf_warmup_days": int(htf_warmup_days),
        "by_path": by_path,
        "warnings": warnings,
        "errors": errors,
    }
