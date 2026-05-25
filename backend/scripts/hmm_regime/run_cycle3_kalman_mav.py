"""run_cycle3_kalman_mav.py — R&D Cycle v2 / Cycle 3 Kalman dynamic hedge MA-V.

Hypothèse pré-spec :
  R2 baseline (z-score 60d static β=1) sur MA-V → Sharpe 0.32, β SPY +0.003 (perfect
  market-neutral), ΔSharpe sub-sample -0.06 (stable), DD -11%. Structure réelle, faible
  mais propre. Static β=1 manque la relation dynamique entre MA et V.
  Vidyamurthy 2004 + Chan 2009 : pairs trading sérieux exige Kalman filter.
  Forme falsifiable : Kalman dynamic β débloque Sharpe MA-V > 0.7 (passage de structure
  faible à edge product-grade). Sinon, MA-V définitivement archivée.

Anti-lookahead constraints (user correction 2026-04-27) :
  - Signal calculé au close t → exécution next close t+1 (jamais same close)
  - Prix yfinance adjusted (split + dividend)
  - Coûts short/borrow leg MA documentés (~0.5-1% APR pour large-cap, default 0.75%)
  - Stop hard intra-day non-actionnable sur daily → exit next close si |z|>3.5 au close

Gates pré-écrits :
  - PROMOTE Stage 1 PASS si Sharpe > 0.7 + |β SPY| < 0.1 + ΔSharpe sub-sample < 0.4 + half-life 5-30d
  - ARCHIVE si Sharpe ≤ baseline static + 0.1
  - Amélioration K.1 (tighten z-score 60d→30d) / K.2 (raise threshold 2.0→2.5) / K.3 (add SPY hedge leg)

Kalman state-space :
  observation : log(V_t) = β_t * log(MA_t) + α_t + ε_t,   ε_t ~ N(0, σ_obs²)
  state : [β_t, α_t]_t = [β, α]_{t-1} + [η_β, η_α]_t,   Q = diag(σ_β², σ_α²)
  σ_obs, σ_β, σ_α calibrated via MLE on first 504 days warmup, then frozen.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from scipy.optimize import minimize

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
OUT_DIR = REPO_ROOT / "backend/data/hmm_regime"
DEFAULT_START = "2019-06-01"
DEFAULT_END = "2025-11-30"
WARMUP_DAYS = 504
ZSCORE_WINDOW = 60
ENTRY_THRESHOLD = 2.0
EXIT_THRESHOLD = 0.5
STOP_THRESHOLD = 3.5
RT_BPS_PER_LEG = 5  # 5 bps per leg per round-trip
BORROW_APR_SHORT_LEG = 0.0075  # 0.75% annualized for large-cap short borrow
TRADING_DAYS = 252
SP500_PRICES_PATH = REPO_ROOT / "backend/data/equities/sp500_prices_6.5y.parquet"


def load_pair_prices(start: str, end: str) -> pd.DataFrame:
    """Load MA + V daily adjusted prices from yfinance, aligned."""
    ma = yf.Ticker("MA").history(start=start, end=end, auto_adjust=False)
    v = yf.Ticker("V").history(start=start, end=end, auto_adjust=False)
    df = pd.DataFrame({
        "ma_adj": ma["Close"] * ma["Adj Close"] / ma["Close"] if "Adj Close" in ma else ma["Close"],
        "v_adj": v["Close"] * v["Adj Close"] / v["Close"] if "Adj Close" in v else v["Close"],
        "ma_close": ma["Close"],
        "v_close": v["Close"],
    })
    # Use yfinance auto_adjust=False then derive adjusted via Adj Close column
    if "Adj Close" in ma.columns:
        df["ma_adj"] = ma["Adj Close"]
    if "Adj Close" in v.columns:
        df["v_adj"] = v["Adj Close"]
    df = df.dropna()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df.index.name = "date"
    df = df.reset_index()
    return df


def kalman_filter(log_ma: np.ndarray, log_v: np.ndarray,
                    sigma_obs: float, sigma_beta: float, sigma_alpha: float,
                    init_beta: float = 1.0, init_alpha: float = 0.0,
                    init_var: float = 1.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Run Kalman filter forward.

    Returns :
      states[n, 2] : [beta_t, alpha_t] post-update
      residuals[n] : innovation = log_v[t] - h_t · x_t|t-1
      log_likelihoods[n] : per-step log-likelihood contribution
    """
    n = len(log_ma)
    Q = np.diag([sigma_beta**2, sigma_alpha**2])
    R = sigma_obs**2
    x = np.array([init_beta, init_alpha])
    P = np.eye(2) * init_var
    states = np.zeros((n, 2))
    residuals = np.zeros(n)
    log_likelihoods = np.zeros(n)
    for t in range(n):
        # Predict
        x_pred = x
        P_pred = P + Q
        # Observation
        h = np.array([log_ma[t], 1.0])
        y_pred = h @ x_pred
        innovation = log_v[t] - y_pred
        S = h @ P_pred @ h + R
        if S <= 0:
            S = 1e-10
        K = (P_pred @ h) / S
        # Update
        x = x_pred + K * innovation
        P = (np.eye(2) - np.outer(K, h)) @ P_pred
        states[t] = x
        residuals[t] = innovation
        log_likelihoods[t] = -0.5 * (np.log(2 * np.pi * S) + innovation**2 / S)
    return states, residuals, log_likelihoods


def calibrate_kalman_mle(log_ma: np.ndarray, log_v: np.ndarray,
                           n_warmup: int = WARMUP_DAYS) -> tuple[float, float, float]:
    """MLE calibration of (σ_obs, σ_β, σ_α) on first n_warmup days. Returns the values.

    Floor σ_β ≥ 1e-4 to avoid degenerate fixed-β solution (Kalman = static β if σ_β=0,
    which defeats the purpose of dynamic hedge).
    """
    def neg_log_lik(log_params):
        sigma_obs, sigma_beta, sigma_alpha = np.exp(log_params)
        sigma_beta = max(sigma_beta, 1e-4)  # floor to keep dynamic
        try:
            _, _, lls = kalman_filter(
                log_ma[:n_warmup], log_v[:n_warmup],
                sigma_obs, sigma_beta, sigma_alpha,
            )
            return -lls.sum()
        except Exception:
            return 1e10

    x0 = np.log([0.01, 0.001, 0.001])
    result = minimize(neg_log_lik, x0=x0, method="Nelder-Mead",
                       options={"xatol": 1e-4, "fatol": 1e-3, "maxiter": 200})
    sigma_obs, sigma_beta, sigma_alpha = np.exp(result.x)
    sigma_beta = max(sigma_beta, 1e-4)
    return float(sigma_obs), float(sigma_beta), float(sigma_alpha)


def compute_zscore(residuals: np.ndarray, window: int = ZSCORE_WINDOW) -> np.ndarray:
    """Rolling z-score with PAST-ONLY mean/std (anti-lookahead)."""
    s = pd.Series(residuals)
    mean = s.rolling(window, min_periods=window).mean()
    std = s.rolling(window, min_periods=window).std()
    z = (s - mean) / std
    return z.values


def simulate_trades(df: pd.DataFrame,
                      entry: float = ENTRY_THRESHOLD,
                      exit_th: float = EXIT_THRESHOLD,
                      stop: float = STOP_THRESHOLD,
                      bps_per_leg: float = RT_BPS_PER_LEG,
                      borrow_apr: float = BORROW_APR_SHORT_LEG) -> pd.DataFrame:
    """Simulate trades : signal at close t, execute at close t+1 (anti-lookahead).

    Position: long V, short β_t × MA (dollar-neutral via Kalman β at entry).
    Daily PnL after entry: dV/V - β_entry · dMA/MA - borrow_cost_per_day.
    """
    df = df.copy().reset_index(drop=True)
    n = len(df)
    position = 0  # 0 = flat, +1 = long-V short-MA, -1 = short-V long-MA
    beta_entry = 0.0
    pnl = np.zeros(n)
    side = np.zeros(n, dtype=int)
    exit_reason = np.full(n, "", dtype=object)
    trade_starts: list[int] = []
    trade_ends: list[int] = []
    trade_directions: list[int] = []

    for t in range(1, n):
        z_yesterday = df["z"].iloc[t - 1]
        z_today = df["z"].iloc[t]
        beta_yesterday = df["beta"].iloc[t - 1]
        # PnL from current position (entered at t-1 close, mark-to-market at t close)
        if position != 0:
            v_ret = df["v_adj"].iloc[t] / df["v_adj"].iloc[t - 1] - 1
            ma_ret = df["ma_adj"].iloc[t] / df["ma_adj"].iloc[t - 1] - 1
            # Long V short β·MA → daily pnl = v_ret - β_entry · ma_ret
            # (assuming dollar-neutral: $1 long V, $β_entry short MA at entry, no rebalancing intraday)
            day_pnl = position * (v_ret - beta_entry * ma_ret)
            # Borrow cost on short leg: β_entry · borrow_daily (short MA when position=+1, short V when position=-1)
            borrow_cost = borrow_apr / TRADING_DAYS * abs(beta_entry if position == +1 else 1.0)
            day_pnl -= borrow_cost
            pnl[t] = day_pnl
            side[t] = position

        # Decision logic AT END OF t-1 (z_yesterday) → applied at t open (we approximate with t close PnL)
        if position == 0:
            # Look at z at t-1 to enter at t
            if not np.isnan(z_yesterday):
                if z_yesterday > entry:
                    # Spread too wide → expect mean-rev → short the spread → short V long MA → position=-1
                    # Actually : spread = log_V - β·log_MA - α. If spread positive (z>+entry),
                    # V is rich vs MA → short V long MA → position = -1 (short V) but we use "long V"
                    # convention as position=+1. So position=-1 = short V.
                    position = -1
                    beta_entry = beta_yesterday
                    trade_starts.append(t)
                    trade_directions.append(-1)
                    # Entry cost
                    pnl[t] -= 2 * bps_per_leg / 10_000.0
                elif z_yesterday < -entry:
                    # Spread too tight (negative z) → V cheap vs MA → long V short MA → position = +1
                    position = +1
                    beta_entry = beta_yesterday
                    trade_starts.append(t)
                    trade_directions.append(+1)
                    pnl[t] -= 2 * bps_per_leg / 10_000.0
        else:
            # Currently in position, check for exit/stop using yesterday's z (anti-lookahead)
            should_exit = False
            reason = ""
            if not np.isnan(z_yesterday):
                if abs(z_yesterday) < exit_th:
                    should_exit = True
                    reason = "target_z"
                elif abs(z_yesterday) > stop:
                    should_exit = True
                    reason = "stop"
            if should_exit:
                pnl[t] -= 2 * bps_per_leg / 10_000.0
                trade_ends.append(t)
                exit_reason[t] = reason
                position = 0
                beta_entry = 0.0

    out = df[["date", "z", "beta", "alpha"]].copy()
    out["pnl"] = pnl
    out["side"] = side

    trades = pd.DataFrame({
        "start_idx": trade_starts[:len(trade_ends)],
        "end_idx": trade_ends,
        "direction": trade_directions[:len(trade_ends)],
    })
    if len(trades):
        trades["start_date"] = trades["start_idx"].map(lambda i: df["date"].iloc[i])
        trades["end_date"] = trades["end_idx"].map(lambda i: df["date"].iloc[i])
        trades["duration_days"] = (trades["end_idx"] - trades["start_idx"]).astype(int)
        trades["exit_reason"] = trades["end_idx"].map(lambda i: exit_reason[i])
    return out, trades


def compute_sharpe(returns: np.ndarray) -> float:
    r = returns[~np.isnan(returns)]
    if len(r) == 0 or r.std() == 0:
        return 0.0
    return float(r.mean() / r.std() * np.sqrt(TRADING_DAYS))


def compute_dd_calmar(returns: np.ndarray) -> tuple[float, float, float]:
    r = returns[~np.isnan(returns)]
    if len(r) == 0:
        return 0.0, 0.0, 0.0
    equity = np.cumprod(1 + r)
    cagr = equity[-1] ** (TRADING_DAYS / len(r)) - 1
    rmax = np.maximum.accumulate(equity)
    dd = (equity - rmax) / rmax
    max_dd = float(dd.min())
    calmar = cagr / abs(max_dd) if max_dd < 0 else 0.0
    return float(cagr), float(max_dd), float(calmar)


def beta_vs_spy(returns: np.ndarray, dates: pd.Series) -> float:
    """Compute β to SPY using same dates."""
    spy_path = SP500_PRICES_PATH
    df_spy = pd.read_parquet(REPO_ROOT / "backend/data/f2_daily/SPY_1d.parquet")
    df_spy = df_spy[["date", "Adj Close"]].rename(columns={"Adj Close": "spy_adj"})
    df_spy["date"] = pd.to_datetime(df_spy["date"])
    df_spy["spy_ret"] = df_spy["spy_adj"].pct_change()
    pair_df = pd.DataFrame({"date": pd.to_datetime(dates).values, "ret": returns})
    merged = pair_df.merge(df_spy[["date", "spy_ret"]], on="date", how="inner").dropna()
    if len(merged) < 10:
        return 0.0
    cov = np.cov(merged["ret"].values, merged["spy_ret"].values)
    if cov[1, 1] == 0:
        return 0.0
    return float(cov[0, 1] / cov[1, 1])


def half_life_ou(residuals: np.ndarray) -> float:
    """OU half-life estimate via AR(1) regression of dr_t on r_{t-1}."""
    r = pd.Series(residuals).dropna().values
    if len(r) < 30:
        return float("nan")
    dr = np.diff(r)
    r_lag = r[:-1]
    if r_lag.std() == 0:
        return float("nan")
    A = np.vstack([r_lag, np.ones(len(r_lag))]).T
    coeffs = np.linalg.lstsq(A, dr, rcond=None)[0]
    theta = float(coeffs[0])  # slope of dr ~ theta * r_lag
    if theta >= 0:
        return float("nan")
    return float(-np.log(2) / theta)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", default=DEFAULT_END)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print("[Cycle 3] Kalman dynamic hedge MA-V", flush=True)
    print(f"  Window {args.start} → {args.end}", flush=True)
    print(f"  Anti-lookahead : signal at close t → execute at close t+1", flush=True)
    print(f"  Costs : 5bps × 2 legs RT + borrow {BORROW_APR_SHORT_LEG*100:.2f}% APR short leg", flush=True)

    # 1) Load pair
    print("[1/5] Loading MA + V adjusted prices...", flush=True)
    df = load_pair_prices(args.start, args.end)
    log_ma = np.log(df["ma_adj"].values)
    log_v = np.log(df["v_adj"].values)
    print(f"      Loaded {len(df)} days", flush=True)

    # 2) Calibrate Kalman σ via MLE on first 504 days warmup
    print(f"[2/5] Calibrating Kalman (MLE on first {WARMUP_DAYS}d warmup)...", flush=True)
    sigma_obs, sigma_beta, sigma_alpha = calibrate_kalman_mle(log_ma, log_v, WARMUP_DAYS)
    print(f"      σ_obs={sigma_obs:.6f}, σ_β={sigma_beta:.6f}, σ_α={sigma_alpha:.6f}", flush=True)

    # 3) Run Kalman forward over full sample with frozen σ
    print("[3/5] Running Kalman forward (full sample, frozen σ)...", flush=True)
    states, residuals, _ = kalman_filter(log_ma, log_v, sigma_obs, sigma_beta, sigma_alpha)
    df["beta"] = states[:, 0]
    df["alpha"] = states[:, 1]
    df["residual"] = residuals

    # Z-score (past-only window)
    df["z"] = compute_zscore(df["residual"].values, ZSCORE_WINDOW)

    # 4) Simulate trades (anti-lookahead, signal at t-1 → trade at t)
    print("[4/5] Simulating trades (anti-lookahead, signal shifted t+1)...", flush=True)
    out_df, trades = simulate_trades(df)
    n_trades = len(trades) if len(trades) else 0
    print(f"      Trades : {n_trades}", flush=True)

    # Skip warmup period for performance metrics
    perf_start = WARMUP_DAYS + ZSCORE_WINDOW
    perf_df = out_df.iloc[perf_start:].copy().reset_index(drop=True)

    # 5) Metrics
    print("[5/5] Computing metrics + verdict...", flush=True)
    sharpe_kalman = compute_sharpe(perf_df["pnl"].values)
    cagr, dd, calmar = compute_dd_calmar(perf_df["pnl"].values)
    beta_spy = beta_vs_spy(perf_df["pnl"].values, perf_df["date"])
    hl = half_life_ou(perf_df["residual"].dropna().values if "residual" in perf_df.columns else df["residual"].values)
    # Sub-sample stability (split in half post-warmup)
    mid = len(perf_df) // 2
    sharpe_h1 = compute_sharpe(perf_df["pnl"].iloc[:mid].values)
    sharpe_h2 = compute_sharpe(perf_df["pnl"].iloc[mid:].values)
    delta_subsample = abs(sharpe_h1 - sharpe_h2)

    print(f"      Sharpe Kalman = {sharpe_kalman:.3f} (R2 baseline static = 0.32)", flush=True)
    print(f"      |β SPY| = {abs(beta_spy):.4f}, half-life = {hl:.1f}d, ΔSharpe sub = {delta_subsample:.2f}", flush=True)

    # Decision logic per plan rd-cycle-v2.md
    R2_BASELINE_SHARPE = 0.32
    if (sharpe_kalman > 0.7 and abs(beta_spy) < 0.1 and delta_subsample < 0.4
            and 5 <= hl <= 30):
        decision = "Stage 1 PASS — Kalman dynamic hedge débloque MA-V"
        emoji = "✅ STAGE 1 PASS"
    elif sharpe_kalman <= R2_BASELINE_SHARPE + 0.1:
        decision = (f"Sharpe Kalman {sharpe_kalman:.3f} ≤ R2 baseline {R2_BASELINE_SHARPE} + 0.1 "
                    f"→ ARCHIVE (Kalman ne débloque pas MA-V)")
        emoji = "🛑 ARCHIVE"
    elif delta_subsample > 0.5:
        decision = (f"ΔSharpe sub-sample {delta_subsample:.2f} > 0.5 → ARCHIVE "
                    f"(régime-dependent, instable)")
        emoji = "🛑 ARCHIVE (subsample)"
    else:
        # Marginal zone — possible amélioration
        decision = (f"Sharpe {sharpe_kalman:.3f} marginal (entre baseline+0.1 et 0.7), "
                    f"|β SPY|={abs(beta_spy):.4f}, half-life={hl:.1f}d. "
                    f"Verdict : MARGINAL → ARCHIVE strict per discipline plan (1 amélioration max, "
                    f"non-déclenchée car gates pré-écrits ne signalent pas défaut clair corrigeable).")
        emoji = "🛑 ARCHIVE (marginal)"

    # Render verdict
    md_lines: list[str] = []
    md_lines.append("# Cycle 3 — Kalman dynamic hedge MA-V")
    md_lines.append("")
    md_lines.append(f"**Generated** : {datetime.now(timezone.utc).isoformat()}")
    md_lines.append(f"**Plan** : R&D Cycle v2 (rd-cycle-v2.md) — Cycle 3")
    md_lines.append(f"**Window** : {args.start} → {args.end}")
    md_lines.append("")
    md_lines.append(f"## Decision : {emoji}")
    md_lines.append("")
    md_lines.append(f"**Verdict** : {decision}")
    md_lines.append("")
    md_lines.append("## Identité")
    md_lines.append("")
    md_lines.append(f"- **Hypothèse** : R2 baseline static β=1 sur MA-V donne Sharpe 0.32 (structure faible "
                     f"mais propre, β SPY +0.003 perfect market-neutral). Kalman dynamic β doit débloquer "
                     f"Sharpe > 0.7. Sinon MA-V définitivement archivée.")
    md_lines.append(f"- **Source** : Vidyamurthy 2004 (Pairs Trading: Quantitative Methods and Analysis) + "
                     f"Chan 2009 (Quantitative Trading)")
    md_lines.append(f"- **Modèle** : Kalman state-space [β_t, α_t] avec random walk + observation linéaire")
    md_lines.append(f"- **Calibration** : MLE sur {WARMUP_DAYS} premiers jours warmup, σ frozen ensuite")
    md_lines.append(f"- **Costs** : 5 bps × 2 legs RT + borrow {BORROW_APR_SHORT_LEG*100:.2f}% APR sur short leg")
    md_lines.append(f"- **Anti-lookahead** : signal calculé au close t → exécution close t+1, prix yfinance "
                     f"adjusted (split + dividend)")
    md_lines.append("")
    md_lines.append("## Calibration MLE")
    md_lines.append("")
    md_lines.append(f"| σ | Valeur |")
    md_lines.append(f"|---|---:|")
    md_lines.append(f"| σ_obs (observation noise) | {sigma_obs:.6f} |")
    md_lines.append(f"| σ_β (state β walk) | {sigma_beta:.6f} |")
    md_lines.append(f"| σ_α (state α walk) | {sigma_alpha:.6f} |")
    md_lines.append("")
    md_lines.append("## Métriques")
    md_lines.append("")
    md_lines.append(f"| Métrique | Kalman | R2 baseline (static β=1) |")
    md_lines.append(f"|---|---:|---:|")
    md_lines.append(f"| Sharpe net | {sharpe_kalman:.3f} | 0.320 |")
    md_lines.append(f"| CAGR | {cagr*100:.2f}% | — |")
    md_lines.append(f"| Max DD | {dd*100:.2f}% | -11.0% |")
    md_lines.append(f"| Calmar | {calmar:.2f} | — |")
    md_lines.append(f"| β SPY | {beta_spy:+.4f} | +0.003 |")
    md_lines.append(f"| Half-life OU | {hl:.1f}d | — |")
    md_lines.append(f"| Sub-sample ΔSharpe | {delta_subsample:.2f} | -0.06 |")
    md_lines.append(f"| n trades | {n_trades} | — |")
    md_lines.append("")
    md_lines.append("## Diagnostic (gates pré-écrits)")
    md_lines.append("")
    md_lines.append(f"| Gate | Result | Status |")
    md_lines.append(f"|---|---|---|")
    md_lines.append(f"| Sharpe > 0.7 | {sharpe_kalman:.3f} | {'PASS' if sharpe_kalman > 0.7 else 'FAIL'} |")
    md_lines.append(f"| Sharpe > baseline + 0.1 = 0.42 | {sharpe_kalman:.3f} | "
                     f"{'PASS' if sharpe_kalman > 0.42 else 'FAIL'} |")
    md_lines.append(f"| |β SPY| < 0.1 | {abs(beta_spy):.4f} | "
                     f"{'PASS' if abs(beta_spy) < 0.1 else 'FAIL'} |")
    md_lines.append(f"| ΔSharpe sub-sample < 0.4 | {delta_subsample:.2f} | "
                     f"{'PASS' if delta_subsample < 0.4 else 'FAIL'} |")
    md_lines.append(f"| Half-life 5-30d | {hl:.1f} | "
                     f"{'PASS' if 5 <= hl <= 30 else 'FAIL'} |")
    md_lines.append("")
    md_lines.append("## Methodology notes")
    md_lines.append("")
    md_lines.append(f"- **Kalman state-space** : log(V) = β_t · log(MA) + α_t + ε ; β_t et α_t random walks")
    md_lines.append(f"- **MLE warmup** : Nelder-Mead sur log-σ pour positivité ; frozen post-warmup")
    md_lines.append(f"- **Z-score** : rolling 60d past-only mean/std")
    md_lines.append(f"- **Trade exec** : signal at close t-1 → trade at close t (anti-lookahead). "
                     f"Daily PnL mark-to-market avec β_entry frozen.")
    md_lines.append(f"- **Borrow cost** : 0.75% APR sur short leg (ajusté daily)")
    md_lines.append(f"- **Stop** : |z| > 3.5 au close → exit close t+1 (intra-day non actionnable sur daily)")
    md_lines.append("")
    out_md = args.out_dir / "cycle3_kalman_mav_verdict.md"
    out_md.write_text("\n".join(md_lines), encoding="utf-8")

    # Persist trades + states
    out_df.to_parquet(args.out_dir / "cycle3_kalman_mav_states.parquet", index=False)
    if len(trades):
        trades.to_parquet(args.out_dir / "cycle3_kalman_mav_trades.parquet", index=False)

    print(f"\n=== Verdict → {out_md}", flush=True)
    print(f"=== Decision : {emoji}", flush=True)
    print(f"=== {decision}", flush=True)


if __name__ == "__main__":
    main()
