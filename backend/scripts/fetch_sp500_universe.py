"""Fetch current SP500 constituents via Wikipedia scrape.

Caveat : this is the CURRENT SP500 list (as of today), NOT point-in-time
membership. Introduces survivorship bias for historical backtests :
  - Stocks delisted/dropped before today are MISSING from universe
  - Stocks added recently to SP500 might not have full history
  - Effect on PEAD : long-decile may be inflated (survivors had positive drift)
  - Mitigation : V3 long-short market-neutral less affected (both legs sampled
    from same biased universe)

For paid alternatives (point-in-time SP500) : Bloomberg, FactSet, CRSP.
For free retail backtest : current constituents is the practical compromise.

Output : data/universe/sp500_constituents.txt (one ticker per line)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "universe" / "sp500_constituents.txt"


def fetch_sp500_wikipedia() -> list[str]:
    """Scrape Wikipedia for current SP500 constituents (via requests with UA)."""
    import io
    import urllib.request
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; DexterioBot/1.0)"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
    tables = pd.read_html(io.StringIO(html))
    # First table is the constituents list
    df = tables[0]
    # Column name is "Symbol" (Wikipedia)
    if "Symbol" not in df.columns:
        # Fallback : try other common names
        for c in df.columns:
            if "symbol" in c.lower() or "ticker" in c.lower():
                df = df.rename(columns={c: "Symbol"})
                break
    if "Symbol" not in df.columns:
        raise RuntimeError(f"Cannot find Symbol column in Wikipedia table : {df.columns.tolist()}")
    # Clean : Yahoo uses BRK-B not BRK.B
    symbols = df["Symbol"].astype(str).str.replace(".", "-", regex=False).str.upper().tolist()
    return sorted(set(symbols))


def main() -> int:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"Fetching SP500 constituents from Wikipedia...")
    symbols = fetch_sp500_wikipedia()
    print(f"  Found {len(symbols)} unique tickers")
    print(f"  Sample : {symbols[:10]}")
    OUT_PATH.write_text("\n".join(symbols) + "\n")
    print(f"  Saved → {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
