"""
Vérification légère de la couverture temporelle des parquets 1m pour le backtest.

Inspiration Freqtrade / Nautilus : valider les données **avant** un run long,
sans relire toute la logique du `BacktestEngine`.

Aligné sur le découpe `BacktestEngine.load_data` : `end_date` est **inclusive**
(coupure exclusive à J+1 00:00 UTC).
"""
from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd

_DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


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
) -> Tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp]:
    """Retourne (warmup_start, start_dt inclusive, end_dt, end_exclusive) en UTC."""
    start_raw = pd.to_datetime(start_date)
    start_dt = start_raw.tz_localize("UTC") if start_raw.tz is None else start_raw.tz_convert("UTC")
    end_raw = pd.to_datetime(end_date)
    end_dt = end_raw.tz_localize("UTC") if end_raw.tz is None else end_raw.tz_convert("UTC")
    end_excl = end_dt + pd.Timedelta(days=1)
    warmup_start = start_dt - pd.Timedelta(days=max(0, int(htf_warmup_days)))
    return warmup_start, start_dt, end_dt, end_excl


def max_intraday_gap_minutes(datetimes: pd.Series) -> Optional[float]:
    """Écart max entre barres consécutives (minutes), **toutes** paires — inclut week-ends si données RTH."""
    if datetimes is None or len(datetimes) < 2:
        return None
    s = pd.to_datetime(datetimes, utc=True).sort_values()
    delta = s.diff().dt.total_seconds().div(60.0)
    return float(delta.max())


def max_gap_minutes_same_utc_day(datetimes: pd.Series) -> Optional[float]:
    """Écart max entre barres **consécutives le même jour UTC** (évite faux positifs vendredi → lundi)."""
    s = pd.to_datetime(datetimes, utc=True).sort_values()
    if len(s) < 2:
        return None
    max_gap = 0.0
    for i in range(1, len(s)):
        if s.iloc[i].date() != s.iloc[i - 1].date():
            continue
        gap = (s.iloc[i] - s.iloc[i - 1]).total_seconds() / 60.0
        if gap > max_gap:
            max_gap = gap
    return float(max_gap) if max_gap > 0 else None


def check_backtest_data_coverage(
    *,
    data_paths: Sequence[str],
    symbols: Sequence[str],
    start_date: str,
    end_date: str,
    htf_warmup_days: int = 0,
    max_gap_warn_minutes: Optional[float] = None,
    gap_same_utc_day_only: bool = True,
    ignore_warmup_check: bool = False,
) -> Dict[str, Any]:
    """
    Vérifie que chaque parquet couvre la fenêtre backtest [start, end] (fin exclusive moteur)
    et optionnellement le warmup HTF.

    - Toujours : ``tmin <= start_dt`` et ``tmax`` atteint la fin de fenêtre.
    - Warmup : si ``htf_warmup_days > 0`` et pas ``ignore_warmup_check``, exige ``tmin <= warmup_start``.

    Returns:
        dict avec ok (bool), by_path, warnings, errors.
    """
    warmup_start, start_dt, end_dt, end_excl = _bounds_to_window(
        start_date, end_date, htf_warmup_days=htf_warmup_days
    )
    end_is_date_only = bool(_DATE_ONLY_RE.match(end_date.strip()))
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
        if tmin > start_dt:
            errors.append(
                f"{sym}: première barre {tmin} est après start {start_dt} — élargir les données ou reculer --start"
            )
        if htf_warmup_days > 0 and not ignore_warmup_check:
            if tmin > warmup_start:
                errors.append(
                    f"{sym}: min datetime {tmin} > warmup_start {warmup_start} "
                    f"(pas assez d'historique pour htf_warmup_days={htf_warmup_days}; "
                    f"utiliser --ignore-warmup-check pour n'exiger que [start,end])"
                )
        elif htf_warmup_days > 0 and ignore_warmup_check and tmin > warmup_start:
            warnings.append(
                f"{sym}: warmup HTF potentiellement incomplet (min {tmin} > warmup_start {warmup_start})"
            )
        if end_is_date_only:
            # IMPORTANT: pour un `--end YYYY-MM-DD` (date-only), on veut éviter un faux négatif
            # sur des datasets RTH-only (pas de barres overnight jusqu'à 23:59 UTC).
            if tmax.date() < end_dt.date():
                errors.append(
                    f"{sym}: max datetime {tmax} < jour de fin demandé ({end_dt.date()}) "
                    f"— données trop courtes pour --end"
                )
        else:
            if tmax < end_excl - pd.Timedelta(seconds=1):
                # Dernière barre strictement avant la fin de fenêtre demandée
                errors.append(
                    f"{sym}: max datetime {tmax} < fin de fenêtre attendue ({end_excl} exclus) "
                    f"— données trop courtes pour --end"
                )
        if max_gap_warn_minutes is not None:
            try:
                s = _read_datetime_column(p)
                if gap_same_utc_day_only:
                    mg = max_gap_minutes_same_utc_day(s)
                    meta["max_gap_minutes_same_utc_day"] = mg
                else:
                    mg = max_intraday_gap_minutes(s)
                    meta["max_gap_minutes"] = mg
                if mg is not None and mg > float(max_gap_warn_minutes):
                    if gap_same_utc_day_only:
                        warnings.append(
                            f"{sym}: écart max entre barres (même jour UTC) ≈ {mg:.1f} min "
                            f"(> {max_gap_warn_minutes}) — vérifier trous 1m"
                        )
                    else:
                        warnings.append(
                            f"{sym}: écart max entre barres (toutes paires) ≈ {mg:.1f} min "
                            f"(> {max_gap_warn_minutes})"
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
