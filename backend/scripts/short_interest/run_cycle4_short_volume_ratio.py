"""run_cycle4_short_volume_ratio.py — R&D Cycle v3 / Cycle 4 FINRA daily short volume ratio.

Hypothèse pré-spec :
  Diether-Lee-Werner 2009 "Short-Sale Strategies and Return Predictability" :
  high daily short volume predicts negative returns next 1-5 days (continuation),
  reverses at 20-30d horizon (mean-reversion).
  Trend hypothesis (1-day continuation) : long bottom-decile z-score of short ratio
  (least shorted relative to history) vs short top-decile (most shorted), daily rebalance.
  Forme falsifiable : Sharpe net > 0.6 + market-neutral (|β SPY|<0.1) sur 6.5y SP500.

Anti-lookahead constraints :
  - Short volume ratio computed from FINRA daily T-1 file (settled t-1, public t)
  - Z-score rolling 60d past-only (excludes t)
  - Signal at end-of-day t-1 → trade close t (anti-lookahead)
  - Daily rebalance, equal-weight long/short basket dollar-neutral

Stage 0 already validated : FINRA cdn.finra.org/equity/regsho/daily archive accessible
all 2019-06-03 → 2025-11-28 trading days. 8/8 dates HTTP 200.

Gates pré-écrits :
  - PROMOTE Stage 1 si Sharpe net > 0.7 + |β SPY| < 0.1 + ΔSharpe sub-sample < 0.4 + capture > 50%
  - ARCHIVE si Sharpe < 0.5
  - ARCHIVE si |β SPY| > 0.2 (not market-neutral)
  - ARCHIVE si ΔSharpe sub-sample > 0.5 (régime-dependent extreme)
"""
from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
import requests

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SP500_PRICES_PATH = REPO_ROOT / "backend/data/equities/sp500_prices_6.5y.parquet"
SPY_PATH = REPO_ROOT / "backend/data/f2_daily/SPY_1d.parquet"
OUT_DIR = REPO_ROOT / "backend/data/short_interest"
CACHE_DIR = OUT_DIR / "cache"
SP500_CONSTITUENTS = REPO_ROOT / "backend/data/universe/sp500_constituents.txt"
PARSED_PARQUET = OUT_DIR / "short_volume_sp500_daily.parquet"

FINRA_USER_AGENT = "Dexterio Research short-interest-feasibility blanchardalexayrtongood@gmail.com"
FINRA_RATE_LIMIT_S = 0.05  # ~20 req/s (FINRA more lenient than SEC)
FINRA_BASE = "https://cdn.finra.org/equity/regsho/daily"

ZSCORE_WINDOW = 60
ENTRY_Z = 1.5
DECILE_FRACTION = 0.10
RT_BPS_PER_LEG = 10
TRADING_DAYS = 252


def fetch_finra_daily(date_str: str, session: requests.Session) -> pd.DataFrame | None:
    """Fetch one daily FINRA Reg SHO file, return parsed DF or None if 403/error."""
    cache_path = CACHE_DIR / f"shrt_{date_str}.parquet"
    if cache_path.exists():
        return pd.read_parquet(cache_path)
    url = f"{FINRA_BASE}/CNMSshvol{date_str}.txt"
    try:
        resp = session.get(url, timeout=30)
        if resp.status_code != 200:
            return None
        # Parse pipe-delimited
        df = pd.read_csv(StringIO(resp.text), sep="|", dtype=str)
        if df.empty:
            return None
        df.columns = [c.strip() for c in df.columns]
        # Drop trailer rows
        df = df[df["Date"].str.match(r"^\d{8}$", na=False)]
        df["Date"] = pd.to_datetime(df["Date"], format="%Y%m%d")
        for col in ["ShortVolume", "ShortExemptVolume", "TotalVolume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df[["Date", "Symbol", "ShortVolume", "TotalVolume"]].dropna()
        cache_path.write_bytes(b"")  # touch
        df.to_parquet(cache_path, index=False)
        return df
    except Exception:
        return None


def build_sp500_short_volume(start: str, end: str, sp500_set: set[str],
                              n_workers: int = 1) -> pd.DataFrame:
    """Download all FINRA daily files in [start, end], filter to SP500, return long-format DF.

    Cached on disk per date. Sequential at FINRA_RATE_LIMIT_S.
    """
    if PARSED_PARQUET.exists():
        existing = pd.read_parquet(PARSED_PARQUET)
        if existing["Date"].min() <= pd.Timestamp(start) and existing["Date"].max() >= pd.Timestamp(end):
            print(f"      Loaded existing parsed data : {len(existing)} rows", flush=True)
            return existing
    session = requests.Session()
    session.headers.update({"User-Agent": FINRA_USER_AGENT, "Accept-Encoding": "gzip"})
    dates = pd.date_range(start, end, freq="B")  # business days
    all_rows: list[pd.DataFrame] = []
    last_req = 0.0
    n_total = len(dates)
    n_ok = 0
    n_skip = 0
    for i, d in enumerate(dates):
        date_str = d.strftime("%Y%m%d")
        # Rate limit
        delta = time.time() - last_req
        if delta < FINRA_RATE_LIMIT_S:
            time.sleep(FINRA_RATE_LIMIT_S - delta)
        last_req = time.time()
        df = fetch_finra_daily(date_str, session)
        if df is None or df.empty:
            n_skip += 1
            continue
        df_sp = df[df["Symbol"].isin(sp500_set)].copy()
        if not df_sp.empty:
            all_rows.append(df_sp)
            n_ok += 1
        if (i + 1) % 100 == 0 or i == n_total - 1:
            print(f"      [{i+1}/{n_total}] {date_str} ok={n_ok} skip={n_skip}", flush=True)
    if not all_rows:
        return pd.DataFrame()
    combined = pd.concat(all_rows, ignore_index=True)
    combined["short_ratio"] = combined["ShortVolume"] / combined["TotalVolume"]
    combined = combined.dropna(subset=["short_ratio"])
    combined.to_parquet(PARSED_PARQUET, index=False)
    return combined


def compute_z_score(short_ratio_wide: pd.DataFrame,
                      window: int = ZSCORE_WINDOW) -> pd.DataFrame:
    """Past-only rolling z-score per symbol."""
    z = short_ratio_wide.copy()
    for sym in short_ratio_wide.columns:
        s = short_ratio_wide[sym]
        mean = s.rolling(window, min_periods=window).mean().shift(1)
        std = s.rolling(window, min_periods=window).std().shift(1)
        z[sym] = (s - mean) / std
    return z


def simulate_long_short_decile(log_ret_wide: pd.DataFrame, z_wide: pd.DataFrame,
                                 entry_z: float, decile_frac: float,
                                 bps_per_leg: float) -> pd.DataFrame:
    """Long bottom-decile z (least shorted relative to history) — short top-decile.

    Trend hypothesis : high short volume → next-day continued downside.
      → SHORT high short volume z, LONG low short volume z.

    Anti-lookahead : signal at z[t-1] (using yesterday's short ratio) → trade close t.
    """
    common_idx = log_ret_wide.index.intersection(z_wide.index)
    common_cols = log_ret_wide.columns.intersection(z_wide.columns)
    log_ret = log_ret_wide.loc[common_idx, common_cols]
    z = z_wide.loc[common_idx, common_cols]
    n = len(common_idx)
    daily_pnl = pd.Series(0.0, index=common_idx)
    n_longs = pd.Series(0, index=common_idx)
    n_shorts = pd.Series(0, index=common_idx)
    prev_long: set[str] = set()
    prev_short: set[str] = set()
    for i in range(2, n):
        z_y = z.iloc[i - 1].dropna()
        if len(z_y) < 30:
            continue
        n_decile = max(1, int(len(z_y) * decile_frac))
        sorted_z = z_y.sort_values()
        long_set = set(sorted_z.head(n_decile).index)  # most negative z = least shorted = LONG (trend up)
        short_set = set(sorted_z.tail(n_decile).index)  # most positive z = most shorted = SHORT (trend down)
        long_set = {s for s in long_set if z_y[s] < -entry_z}
        short_set = {s for s in short_set if z_y[s] > entry_z}
        if not long_set and not short_set:
            continue
        today_ret = log_ret.iloc[i]
        long_ret = today_ret[list(long_set)].mean() if long_set else 0.0
        short_ret = today_ret[list(short_set)].mean() if short_set else 0.0
        spread_ret = (long_ret if long_set else 0.0) - (short_ret if short_set else 0.0)
        new_l = long_set - prev_long
        new_s = short_set - prev_short
        cost = ((len(new_l) / max(1, len(long_set))) + (len(new_s) / max(1, len(short_set)))) * bps_per_leg / 10_000.0
        if not long_set:
            cost -= bps_per_leg / 10_000.0
        if not short_set:
            cost -= bps_per_leg / 10_000.0
        cost = max(cost, 0.0)
        daily_pnl.iloc[i] = spread_ret - cost
        n_longs.iloc[i] = len(long_set)
        n_shorts.iloc[i] = len(short_set)
        prev_long = long_set
        prev_short = short_set
    return pd.DataFrame({
        "date": common_idx,
        "pnl": daily_pnl.values,
        "n_longs": n_longs.values,
        "n_shorts": n_shorts.values,
    })


def compute_sharpe(returns: np.ndarray) -> float:
    r = returns[~np.isnan(returns)]
    if len(r) == 0 or r.std() == 0:
        return 0.0
    return float(r.mean() / r.std() * np.sqrt(TRADING_DAYS))


def compute_dd_calmar(returns: np.ndarray) -> tuple[float, float, float]:
    r = returns[~np.isnan(returns)]
    if len(r) == 0:
        return 0.0, 0.0, 0.0
    eq = np.cumprod(1 + r)
    cagr = eq[-1] ** (TRADING_DAYS / len(r)) - 1
    rmax = np.maximum.accumulate(eq)
    dd = (eq - rmax) / rmax
    return float(cagr), float(dd.min()), float(cagr / abs(dd.min()) if dd.min() < 0 else 0.0)


def beta_vs_spy(returns: np.ndarray, dates: pd.Series) -> float:
    df_spy = pd.read_parquet(SPY_PATH)[["date", "Adj Close"]].rename(columns={"Adj Close": "spy_adj"})
    df_spy["date"] = pd.to_datetime(df_spy["date"])
    df_spy["spy_ret"] = df_spy["spy_adj"].pct_change()
    pair = pd.DataFrame({"date": pd.to_datetime(dates).values, "ret": returns})
    merged = pair.merge(df_spy[["date", "spy_ret"]], on="date", how="inner").dropna()
    if len(merged) < 10:
        return 0.0
    cov = np.cov(merged["ret"].values, merged["spy_ret"].values)
    return float(cov[0, 1] / cov[1, 1] if cov[1, 1] != 0 else 0.0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2019-06-03")
    parser.add_argument("--end", default="2025-11-28")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    print("[Cycle 4] FINRA daily short volume ratio Diether-Lee-Werner trend", flush=True)
    print(f"  Window {args.start} → {args.end}", flush=True)
    print(f"  Anti-lookahead : signal z[t-1] → trade close t", flush=True)
    print(f"  Costs : {RT_BPS_PER_LEG} bps RT/leg, decile {DECILE_FRACTION:.0%}, entry_z {ENTRY_Z}", flush=True)

    # 1) SP500 universe
    sp500 = {l.strip().upper() for l in SP500_CONSTITUENTS.read_text().splitlines() if l.strip()}
    print(f"[1/5] SP500 universe : {len(sp500)} tickers", flush=True)

    # 2) Download + parse FINRA daily files
    print("[2/5] Downloading FINRA Reg SHO daily files (cached)...", flush=True)
    short_data = build_sp500_short_volume(args.start, args.end, sp500)
    if short_data.empty:
        print("ERROR: no data fetched", flush=True)
        return
    print(f"      Total rows : {len(short_data)} ({short_data['Symbol'].nunique()} symbols, "
          f"{short_data['Date'].nunique()} days)", flush=True)

    # 3) Build wide-format short ratio + z-score
    print(f"[3/5] Computing z-score short_ratio (rolling {ZSCORE_WINDOW}d past-only)...", flush=True)
    short_ratio_wide = short_data.pivot(index="Date", columns="Symbol", values="short_ratio").sort_index()
    z_wide = compute_z_score(short_ratio_wide, ZSCORE_WINDOW)

    # Load price returns aligned
    px = pd.read_parquet(SP500_PRICES_PATH)
    px = px[["date", "symbol", "adj_close"]].copy()
    px["date"] = pd.to_datetime(px["date"])
    px_wide = px.pivot(index="date", columns="symbol", values="adj_close").sort_index()
    log_ret_wide = np.log(px_wide).diff()

    # 4) Simulate
    print("[4/5] Simulating long-short decile (trend continuation)...", flush=True)
    sim = simulate_long_short_decile(log_ret_wide, z_wide,
                                       entry_z=ENTRY_Z, decile_frac=DECILE_FRACTION,
                                       bps_per_leg=RT_BPS_PER_LEG)
    n_active = (sim["n_longs"] + sim["n_shorts"] > 0).sum()
    print(f"      Active days : {n_active}/{len(sim)}", flush=True)

    # Skip warmup
    perf = sim.iloc[ZSCORE_WINDOW + 5:].copy().reset_index(drop=True)

    # 5) Metrics + decision
    print("[5/5] Metrics + decision...", flush=True)
    sharpe = compute_sharpe(perf["pnl"].values)
    cagr, dd, calmar = compute_dd_calmar(perf["pnl"].values)
    beta_spy = beta_vs_spy(perf["pnl"].values, perf["date"])
    mid = pd.Timestamp("2022-09-01")
    h1 = perf[perf["date"] < mid]
    h2 = perf[perf["date"] >= mid]
    sh_h1 = compute_sharpe(h1["pnl"].values)
    sh_h2 = compute_sharpe(h2["pnl"].values)
    delta_sub = abs(sh_h1 - sh_h2)
    print(f"      Sharpe = {sharpe:.3f}, CAGR = {cagr*100:.2f}%, MaxDD = {dd*100:.2f}%, |β SPY|={abs(beta_spy):.4f}, ΔSub={delta_sub:.2f}", flush=True)

    # Decision
    archive: list[str] = []
    if sharpe < 0.5:
        archive.append(f"Sharpe {sharpe:.3f} < 0.5")
    if abs(beta_spy) > 0.2:
        archive.append(f"|β SPY| {abs(beta_spy):.3f} > 0.2 (not market-neutral)")
    if delta_sub > 0.5:
        archive.append(f"ΔSharpe sub-sample {delta_sub:.2f} > 0.5 (régime-dependent)")
    if archive:
        decision = "ARCHIVE — " + " ; ".join(archive)
        emoji = "🛑 ARCHIVE"
    elif (sharpe > 0.7 and abs(beta_spy) < 0.1 and delta_sub < 0.4):
        decision = "Stage 1 PASS — short volume ratio trend débloque edge multi-asset cross-sectional"
        emoji = "✅ STAGE 1 PASS"
    else:
        decision = (f"Marginal (Sharpe {sharpe:.3f}, |β|={abs(beta_spy):.3f}, Δsub={delta_sub:.2f}) — "
                    f"ARCHIVE strict per discipline (1 amélioration max non-déclenchée car gates ne signalent pas défaut clair)")
        emoji = "🛑 ARCHIVE (marginal)"

    md_lines: list[str] = []
    md_lines.append("# Cycle 4 — FINRA daily short volume ratio (Diether-Lee-Werner trend)")
    md_lines.append("")
    md_lines.append(f"**Generated** : {datetime.now(timezone.utc).isoformat()}")
    md_lines.append(f"**Plan** : R&D Cycle v3 — Cycle 4")
    md_lines.append(f"**Window** : {args.start} → {args.end}")
    md_lines.append("")
    md_lines.append(f"## Decision : {emoji}")
    md_lines.append("")
    md_lines.append(f"**Verdict** : {decision}")
    md_lines.append("")
    md_lines.append("## Identité")
    md_lines.append("")
    md_lines.append(f"- **Hypothèse** : Diether-Lee-Werner 2009 — high daily short volume → next-day continuation downside, "
                     f"reversal at 20-30d horizon. Test ici : 1-day continuation TREND hypothesis.")
    md_lines.append(f"- **Univers** : SP500 503 tickers (current 2026), FINRA Reg SHO daily files filtered.")
    md_lines.append(f"- **Source** : `cdn.finra.org/equity/regsho/daily/CNMSshvol{{YYYYMMDD}}.txt` (Stage 0 GO confirmed 8/8 dates accessible).")
    md_lines.append(f"- **Signal** : short_ratio = ShortVolume / TotalVolume, z-score rolling {ZSCORE_WINDOW}d past-only. "
                     f"Long bottom-decile z (z<-{ENTRY_Z}, least shorted), short top-decile z (z>+{ENTRY_Z}, most shorted), "
                     f"daily rebalance equal-weight dollar-neutral.")
    md_lines.append(f"- **Anti-lookahead** : z[t-1] → trade close t (FINRA file published end-of-day t-1 → available pre-open t).")
    md_lines.append(f"- **Costs** : {RT_BPS_PER_LEG} bps RT/leg turnover-aware.")
    md_lines.append("")
    md_lines.append("## Métriques")
    md_lines.append("")
    md_lines.append(f"| Métrique | Valeur |")
    md_lines.append(f"|---|---:|")
    md_lines.append(f"| Sharpe net | {sharpe:.3f} |")
    md_lines.append(f"| CAGR | {cagr*100:.2f}% |")
    md_lines.append(f"| Max DD | {dd*100:.2f}% |")
    md_lines.append(f"| Calmar | {calmar:.2f} |")
    md_lines.append(f"| β SPY | {beta_spy:+.4f} |")
    md_lines.append(f"| ΔSharpe sub (h1<2022-09 vs h2≥) | {delta_sub:.2f} (h1={sh_h1:.2f}, h2={sh_h2:.2f}) |")
    md_lines.append(f"| Active days | {n_active}/{len(sim)} |")
    md_lines.append("")
    md_lines.append("## Diagnostic (gates pré-écrits)")
    md_lines.append("")
    md_lines.append(f"| Gate | Result | Status |")
    md_lines.append(f"|---|---|---|")
    md_lines.append(f"| Sharpe > 0.7 | {sharpe:.3f} | {'PASS' if sharpe > 0.7 else 'FAIL'} |")
    md_lines.append(f"| Sharpe ≥ 0.5 | {sharpe:.3f} | {'PASS' if sharpe >= 0.5 else 'FAIL'} |")
    md_lines.append(f"| |β SPY| < 0.1 (market-neutral) | {abs(beta_spy):.4f} | "
                     f"{'PASS' if abs(beta_spy) < 0.1 else 'FAIL'} |")
    md_lines.append(f"| ΔSharpe sub-sample < 0.4 | {delta_sub:.2f} | "
                     f"{'PASS' if delta_sub < 0.4 else 'FAIL'} |")
    md_lines.append("")
    out_md = args.out_dir / "cycle4_short_volume_ratio_verdict.md"
    out_md.write_text("\n".join(md_lines), encoding="utf-8")
    perf.to_parquet(args.out_dir / "cycle4_short_volume_pnl.parquet", index=False)

    print(f"\n=== Verdict → {out_md}", flush=True)
    print(f"=== Decision : {emoji}", flush=True)
    print(f"=== {decision}", flush=True)


if __name__ == "__main__":
    main()
