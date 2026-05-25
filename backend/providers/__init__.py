"""Data providers minimal layer — S+2 P0 plan refais-moi-le-plan-swirling-orbit.md.

Scope strict S+2 (gelé) :
  - Yahoo price provider (OHLCV daily via yfinance)
  - Yahoo earnings provider (earnings dates + EPS surprise via yfinance per-ticker
    + yahooquery batch fallback)

Out of scope explicite S+2 :
  - FRED provider (post-PEAD verdict seulement)
  - Polygon paid provider (pivot fondamental D)
  - Alpha Vantage / autres sources
  - Generic multi-provider abstraction au-delà de ces 2

Pattern : interface Provider abstract minimale (5 méthodes max), implémentations
concrètes injectent dépendances data sources. Manifest JSON per dataset stocké
à côté du fichier parquet pour traçabilité (source / start / end / rows /
last_updated / provider / checksum / warnings).
"""
from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd

MANIFEST_VERSION = 1


def _checksum_dataframe(df: pd.DataFrame) -> str:
    """Simple deterministic checksum of a DataFrame (first/last rows + shape)."""
    if df.empty:
        return "empty"
    fingerprint = (
        f"{df.shape}|"
        f"{df.iloc[0].to_json()}|"
        f"{df.iloc[-1].to_json()}"
    )
    return hashlib.sha256(fingerprint.encode()).hexdigest()[:16]


def write_manifest(
    output_path: Path,
    *,
    source: str,
    symbols: list[str],
    start: str,
    end: str,
    rows: int,
    provider: str,
    df: Optional[pd.DataFrame] = None,
    warnings: Optional[list[str]] = None,
    extra: Optional[dict[str, Any]] = None,
) -> Path:
    """Write a manifest JSON sidecar for a dataset.

    Args:
        output_path : path of the data file (e.g. data/equities/SP500_prices.parquet)
        source : data source identifier (e.g. "yfinance", "yahooquery")
        symbols : list of symbols included
        start, end : ISO date strings (inclusive)
        rows : total row count
        provider : provider class name (e.g. "YahooPriceProvider")
        df : optional dataframe to compute checksum
        warnings : optional list of quality warnings
        extra : optional extra metadata dict

    Returns:
        Path of the manifest file (next to data file with .manifest.json suffix).
    """
    manifest_path = output_path.with_suffix(output_path.suffix + ".manifest.json")
    manifest = {
        "version": MANIFEST_VERSION,
        "source": source,
        "provider": provider,
        "symbols": symbols,
        "n_symbols": len(symbols),
        "start": start,
        "end": end,
        "rows": rows,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "checksum": _checksum_dataframe(df) if df is not None else None,
        "warnings": warnings or [],
    }
    if extra:
        manifest["extra"] = extra
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str))
    return manifest_path


def read_manifest(data_path: Path) -> Optional[dict[str, Any]]:
    """Read manifest sidecar for a data file. Returns None if absent."""
    manifest_path = data_path.with_suffix(data_path.suffix + ".manifest.json")
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text())


class Provider(ABC):
    """Abstract base class for data providers.

    All providers must implement fetch() returning a DataFrame and write
    a manifest sidecar via write_manifest() helper.
    """

    name: str = "abstract"

    @abstractmethod
    def fetch(self, symbols: list[str], start: str, end: str,
              **kwargs: Any) -> pd.DataFrame:
        """Fetch data for given symbols + date range.

        Args:
            symbols : list of ticker symbols
            start : ISO date YYYY-MM-DD inclusive
            end : ISO date YYYY-MM-DD inclusive
            **kwargs : provider-specific options

        Returns:
            DataFrame with at minimum columns ['symbol', 'date'] + provider data
        """
        raise NotImplementedError

    def save(self, df: pd.DataFrame, output_path: Path,
             symbols: list[str], start: str, end: str,
             warnings: Optional[list[str]] = None,
             extra: Optional[dict[str, Any]] = None) -> tuple[Path, Path]:
        """Save dataframe to parquet + write manifest sidecar.

        Returns:
            (data_path, manifest_path)
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(output_path, index=False)
        manifest_path = write_manifest(
            output_path,
            source=self.__class__.__name__.lower().replace("provider", ""),
            symbols=symbols,
            start=start,
            end=end,
            rows=len(df),
            provider=self.__class__.__name__,
            df=df,
            warnings=warnings,
            extra=extra,
        )
        return output_path, manifest_path
