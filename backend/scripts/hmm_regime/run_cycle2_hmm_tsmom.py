"""run_cycle2_hmm_tsmom.py — R&D Cycle v2 / Cycle 2 HMM regime gate sur TSMOM 4-asset.

Hypothèse pré-spec :
  TSMOM 4-asset (SPY/QQQ/GLD/TLT) Sharpe unconditional 0.96 contient mix régimes.
  Conditional sur P(calm)_t+1 > 0.7 (HMM 2-state vol-based features SPY), Sharpe attendu > 1.3.
  Sinon, regime gate sans valeur ajoutée → ARCHIVE.

Anti-leak garanti :
  - HMM rolling fit strictement sur features < t (252-day past window)
  - StandardScaler fit sur fenêtre passée seulement
  - State_t+1 prédit avec features <= t, deploy à t+1 (signal shifté)
  - Pas de re-fit sur full sample même pour exploration

Gates pré-écrits :
  - ARCHIVE si conditional Sharpe ≤ unconditional + 0.3
  - ARCHIVE si permutation labels p ≥ 0.10 (réel doit BATTRE random)
  - 1 amélioration K=3 states OU threshold tune si coverage < 30% en baseline
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM
from sklearn.preprocessing import StandardScaler

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SPY_PATH = REPO_ROOT / "backend/data/f2_daily/SPY_1d.parquet"
TSMOM_PATH = REPO_ROOT / "backend/data/equities/tsmom_4etf_daily_returns.parquet"
OUT_DIR = REPO_ROOT / "backend/data/hmm_regime"
DEFAULT_N_COMPONENTS = 2
DEFAULT_TRAINING_WINDOW = 252
DEFAULT_THRESHOLD = 0.7
TRADING_DAYS_PER_YEAR = 252
PERMUTATION_ITER = 500
SEED = 42


def load_spy_features() -> pd.DataFrame:
    """Load SPY daily and compute features : return_5d + log_realized_vol_20d."""
    df = pd.read_parquet(SPY_PATH)
    df = df[["date", "Adj Close"]].rename(columns={"Adj Close": "adj_close"}).copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df["log_ret"] = np.log(df["adj_close"]).diff()
    df["return_5d"] = df["log_ret"].rolling(5).sum()
    df["realized_vol_20d"] = df["log_ret"].rolling(20).std() * np.sqrt(TRADING_DAYS_PER_YEAR)
    df["log_realized_vol_20d"] = np.log(df["realized_vol_20d"])
    return df.dropna(subset=["return_5d", "log_realized_vol_20d"]).reset_index(drop=True)


def load_tsmom_returns() -> pd.DataFrame:
    """Load persisted TSMOM 4-asset daily returns. Cleaned to date + ret columns."""
    df = pd.read_parquet(TSMOM_PATH)
    if df.index.name == "date":
        df = df.reset_index()
    df["date"] = pd.to_datetime(df["date"])
    return df[["date", "ret"]].sort_values("date").reset_index(drop=True)


def fit_hmm_rolling(features_df: pd.DataFrame,
                     window: int = DEFAULT_TRAINING_WINDOW,
                     n_components: int = DEFAULT_N_COMPONENTS,
                     seed: int = SEED) -> pd.DataFrame:
    """Rolling HMM fit on features [return_5d, log_realized_vol_20d].

    For each bar t starting at window+1 :
      - Fit HMM on features[t-window : t] (past only)
      - Compute P(state_k | observation_t) for next-day deployment
      - Return state probabilities + assigned label (calm = lowest mean vol state)

    Anti-leak guarantees :
      - StandardScaler fit on past window only, transform to t
      - HMM never sees features at or beyond t
      - Returned probabilities are for t (deployment day t+1 by signal shift)
    """
    feat_cols = ["return_5d", "log_realized_vol_20d"]
    n = len(features_df)
    proba_calm = np.full(n, np.nan)
    proba_storm = np.full(n, np.nan)
    state_label = np.full(n, -1, dtype=int)
    rng = np.random.RandomState(seed)

    for t in range(window, n):
        train = features_df.iloc[t - window:t][feat_cols].values
        scaler = StandardScaler()
        train_scaled = scaler.fit_transform(train)
        try:
            model = GaussianHMM(
                n_components=n_components,
                covariance_type="full",
                n_iter=50,
                tol=1e-3,
                random_state=int(rng.randint(0, 1_000_000)),
            )
            model.fit(train_scaled)
        except Exception:
            continue
        # Identify calm state (lowest mean log_realized_vol_20d)
        means = model.means_
        # log_realized_vol_20d is feature index 1
        calm_idx = int(np.argmin(means[:, 1]))
        # Predict state probabilities for current observation
        obs_t = features_df.iloc[[t]][feat_cols].values
        obs_scaled = scaler.transform(obs_t)
        # forward algorithm score for current obs alone
        # Use predict_proba which gives smoothed posterior over training data
        # For OUT-OF-SAMPLE single point, we use the HMM's transition + emission to compute:
        # P(state | obs_t) ∝ stationary * P(obs_t | state)
        log_emission = model._compute_log_likelihood(obs_scaled)[0]
        log_prior = np.log(model.startprob_ + 1e-30)
        # Use stationary distribution from transition matrix
        try:
            eigvals, eigvecs = np.linalg.eig(model.transmat_.T)
            idx = np.argmin(np.abs(eigvals - 1))
            stat = np.real(eigvecs[:, idx])
            stat = stat / stat.sum()
            stat = np.maximum(stat, 1e-10)
            log_prior = np.log(stat)
        except Exception:
            pass
        log_post = log_emission + log_prior
        log_post -= log_post.max()
        post = np.exp(log_post)
        post = post / post.sum()
        proba_calm[t] = post[calm_idx]
        proba_storm[t] = 1.0 - post[calm_idx]
        state_label[t] = calm_idx

    out = features_df[["date"]].copy()
    out["proba_calm"] = proba_calm
    out["proba_storm"] = proba_storm
    out["state_label_idx"] = state_label
    return out


def apply_regime_gate(strat_returns: pd.DataFrame, regime_df: pd.DataFrame,
                       threshold: float = DEFAULT_THRESHOLD) -> pd.DataFrame:
    """Apply regime gate to strategy returns (SHIFTED 1 day to deploy at t+1).

    Anti-leak : we use proba_calm at t-1 to decide deployment at t.
    """
    df = strat_returns.merge(regime_df, on="date", how="inner")
    # Shift signal : decision at end of t deploys at t+1
    df["proba_calm_shifted"] = df["proba_calm"].shift(1)
    df["deploy"] = (df["proba_calm_shifted"] > threshold).astype(int)
    df["ret_conditional"] = df["ret"] * df["deploy"]
    return df


def compute_sharpe(returns: np.ndarray) -> float:
    """Annualized Sharpe ratio (assumes daily returns, 252 trading days/year)."""
    r = returns[~np.isnan(returns)]
    if len(r) == 0 or r.std() == 0:
        return 0.0
    return float(r.mean() / r.std() * np.sqrt(TRADING_DAYS_PER_YEAR))


def compute_calmar(returns: np.ndarray) -> tuple[float, float, float]:
    """Returns (cagr, max_dd, calmar)."""
    r = returns[~np.isnan(returns)]
    if len(r) == 0:
        return 0.0, 0.0, 0.0
    equity = np.cumprod(1 + r)
    cagr = equity[-1] ** (TRADING_DAYS_PER_YEAR / len(r)) - 1
    rolling_max = np.maximum.accumulate(equity)
    dd = (equity - rolling_max) / rolling_max
    max_dd = float(dd.min())
    calmar = cagr / abs(max_dd) if max_dd < 0 else 0.0
    return float(cagr), float(max_dd), float(calmar)


def permutation_test(real_ret: np.ndarray, deploy_signal: np.ndarray,
                       n_iter: int = PERMUTATION_ITER, seed: int = SEED
                       ) -> tuple[float, float]:
    """Shuffle deploy labels n_iter times, compute conditional Sharpe distribution.

    Returns (real_sharpe, p_value_one_sided_real_beats_shuffled).
    Gate per plan : p < 0.10 (real must BEAT shuffled).
    """
    rng = np.random.RandomState(seed)
    real_ret = np.asarray(real_ret, dtype=float)
    deploy_signal = np.asarray(deploy_signal, dtype=int)
    mask = ~np.isnan(real_ret)
    real_ret = real_ret[mask]
    deploy_signal = deploy_signal[mask]
    if real_ret.size == 0:
        return 0.0, 1.0
    real_sharpe = compute_sharpe(real_ret * deploy_signal)
    shuffled_sharpes: list[float] = []
    for _ in range(n_iter):
        permuted = rng.permutation(deploy_signal)
        shuffled_sharpes.append(compute_sharpe(real_ret * permuted))
    shuffled = np.array(shuffled_sharpes)
    p_value = float((shuffled >= real_sharpe).mean())
    return real_sharpe, p_value


def audit_table(deploy_df: pd.DataFrame, threshold: float) -> dict:
    """Compute audit metrics for the verdict."""
    days_total = len(deploy_df)
    deploy_mask = deploy_df["deploy"] == 1
    days_calm = int(deploy_mask.sum())
    coverage = days_calm / days_total if days_total else 0.0
    # Per-state Sharpe of base strategy
    sharpe_when_calm = compute_sharpe(deploy_df.loc[deploy_mask, "ret"].values)
    sharpe_when_storm = compute_sharpe(deploy_df.loc[~deploy_mask, "ret"].values)
    # Number of regime switches
    switches = int((deploy_df["deploy"].diff().fillna(0).abs() > 0).sum())
    # Per-year breakdown
    deploy_df = deploy_df.copy()
    deploy_df["year"] = pd.to_datetime(deploy_df["date"]).dt.year
    by_year = deploy_df.groupby("year").apply(
        lambda g: pd.Series({
            "n_days": len(g),
            "n_deploy": int((g["deploy"] == 1).sum()),
            "uncond_sharpe": compute_sharpe(g["ret"].values),
            "cond_sharpe": compute_sharpe(g["ret_conditional"].values),
        })
    ).reset_index()
    return {
        "n_days_total": days_total,
        "n_days_deploy": days_calm,
        "coverage_pct": round(coverage * 100, 2),
        "sharpe_base_when_calm": sharpe_when_calm,
        "sharpe_base_when_storm": sharpe_when_storm,
        "n_regime_switches": switches,
        "by_year": by_year.to_dict(orient="records"),
        "threshold": threshold,
    }


def render_verdict(*, params: dict, results: dict, audit: dict, perm: dict,
                     decision: str, decision_emoji: str) -> str:
    lines: list[str] = []
    lines.append("# Cycle 2 — HMM regime gate / TSMOM 4-asset")
    lines.append("")
    lines.append(f"**Generated** : {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"**Plan** : R&D Cycle v2 (rd-cycle-v2.md) — Cycle 2")
    lines.append("")
    lines.append(f"## Decision : {decision_emoji}")
    lines.append("")
    lines.append(f"**Verdict** : {decision}")
    lines.append("")
    lines.append("## Identité")
    lines.append("")
    lines.append(f"- **Hypothèse** : TSMOM Sharpe unconditional 0.96 contient mix régimes ; "
                  f"conditional sur P(calm)>{params['threshold']} attendu Sharpe > 1.3")
    lines.append(f"- **HMM config** : GaussianHMM K={params['n_components']} states, "
                  f"covariance=full, training rolling {params['training_window']}d strictement < t")
    lines.append(f"- **Features** : SPY return_5d + log_realized_vol_20d")
    lines.append(f"- **Base strategy** : TSMOM 4-asset SPY/QQQ/GLD/TLT (1382 days, "
                  f"{params['date_min']} → {params['date_max']})")
    lines.append("")
    lines.append("## Métriques")
    lines.append("")
    lines.append(f"| Métrique | Unconditional | Conditional (P(calm)>{params['threshold']}) | Δ |")
    lines.append(f"|---|---:|---:|---:|")
    lines.append(f"| Sharpe net | {results['uncond_sharpe']:.3f} | {results['cond_sharpe']:.3f} | "
                  f"{results['cond_sharpe'] - results['uncond_sharpe']:+.3f} |")
    lines.append(f"| CAGR | {results['uncond_cagr']*100:.2f}% | {results['cond_cagr']*100:.2f}% | "
                  f"{(results['cond_cagr'] - results['uncond_cagr'])*100:+.2f}pp |")
    lines.append(f"| Max DD | {results['uncond_dd']*100:.2f}% | {results['cond_dd']*100:.2f}% | "
                  f"{(results['cond_dd'] - results['uncond_dd'])*100:+.2f}pp |")
    lines.append(f"| Calmar | {results['uncond_calmar']:.2f} | {results['cond_calmar']:.2f} | "
                  f"{results['cond_calmar'] - results['uncond_calmar']:+.2f} |")
    lines.append("")
    lines.append("## Audit trade-level")
    lines.append("")
    lines.append(f"- **Coverage** : {audit['n_days_deploy']}/{audit['n_days_total']} days = "
                  f"{audit['coverage_pct']}% in deploy state")
    lines.append(f"- **Regime switches** : {audit['n_regime_switches']}")
    lines.append(f"- **Base strategy Sharpe in deploy state** : {audit['sharpe_base_when_calm']:.3f}")
    lines.append(f"- **Base strategy Sharpe in cash state** : {audit['sharpe_base_when_storm']:.3f}")
    lines.append("")
    lines.append("### Per-year breakdown")
    lines.append("")
    lines.append(f"| Year | n_days | n_deploy | Uncond Sharpe | Cond Sharpe |")
    lines.append(f"|---|---:|---:|---:|---:|")
    for r in audit["by_year"]:
        lines.append(f"| {int(r['year'])} | {int(r['n_days'])} | {int(r['n_deploy'])} | "
                      f"{r['uncond_sharpe']:.3f} | {r['cond_sharpe']:.3f} |")
    lines.append("")
    lines.append("## Permutation test (regime labels)")
    lines.append("")
    lines.append(f"- **Iterations** : {perm['n_iter']} (seed={perm['seed']})")
    lines.append(f"- **Real Sharpe** : {perm['real_sharpe']:.3f}")
    lines.append(f"- **Shuffled Sharpe** : mean={perm['shuffled_mean']:.3f}, "
                  f"p95={perm['shuffled_p95']:.3f}")
    lines.append(f"- **p-value (one-sided real beats shuffled)** : **{perm['p_value']:.4f}**")
    lines.append(f"- **Gate** : p < 0.10 → real regime BEATS random labels")
    lines.append(f"- **Result** : {'PASS' if perm['p_value'] < 0.10 else 'FAIL'}")
    lines.append("")
    lines.append("## Diagnostic (gates pré-écrits)")
    lines.append("")
    lines.append(f"| Gate | Result | Status |")
    lines.append(f"|---|---|---|")
    delta = results["cond_sharpe"] - results["uncond_sharpe"]
    lines.append(f"| Conditional Sharpe > unconditional + 0.3 | Δ = {delta:+.3f} | "
                  f"{'PASS' if delta > 0.3 else 'FAIL'} |")
    lines.append(f"| Permutation labels p < 0.10 | p = {perm['p_value']:.4f} | "
                  f"{'PASS' if perm['p_value'] < 0.10 else 'FAIL'} |")
    lines.append(f"| Coverage in [30%, 90%] (not too rare/permissive) | {audit['coverage_pct']}% | "
                  f"{'PASS' if 30 <= audit['coverage_pct'] <= 90 else 'WARN'} |")
    lines.append("")
    lines.append("## Methodology notes")
    lines.append("")
    lines.append(f"- **Anti-leak** : HMM rolling fit strictement sur features < t. "
                  f"StandardScaler fit past-only. Signal shifted +1 day (deploy at t+1 from features ≤ t-1).")
    lines.append(f"- **Calm state** : state with lowest mean `log_realized_vol_20d` (canonical Hamilton 1989).")
    lines.append(f"- **Permutation** : {PERMUTATION_ITER} shuffles of deploy signal, gate p<0.10.")
    lines.append(f"- **Costs** : same as base TSMOM (no extra cycling cost modeled in this run — to be quantified Stage 2).")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--n-components", type=int, default=DEFAULT_N_COMPONENTS)
    parser.add_argument("--training-window", type=int, default=DEFAULT_TRAINING_WINDOW)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print("[Cycle 2] HMM regime gate / TSMOM 4-asset", flush=True)
    print(f"  HMM config : K={args.n_components}, training_window={args.training_window}, "
          f"threshold={args.threshold}", flush=True)

    # 1) Load features + base strategy
    print("[1/5] Loading SPY features + TSMOM returns...", flush=True)
    features = load_spy_features()
    tsmom = load_tsmom_returns()
    print(f"      SPY features : {len(features)} days {features['date'].min()} → {features['date'].max()}",
          flush=True)
    print(f"      TSMOM returns : {len(tsmom)} days {tsmom['date'].min()} → {tsmom['date'].max()}",
          flush=True)

    # 2) Rolling HMM fit
    print("[2/5] Fitting HMM rolling 252d (anti-leak)...", flush=True)
    regime = fit_hmm_rolling(features, window=args.training_window,
                              n_components=args.n_components, seed=SEED)
    print(f"      Regime probas computed for {regime['proba_calm'].notna().sum()} days", flush=True)

    # 3) Apply gate (signal shifted)
    print("[3/5] Applying regime gate (signal shifted t+1)...", flush=True)
    deploy_df = apply_regime_gate(tsmom, regime, threshold=args.threshold)
    deploy_df = deploy_df.dropna(subset=["proba_calm_shifted", "ret"]).reset_index(drop=True)
    print(f"      Deploy days : {(deploy_df['deploy']==1).sum()} / {len(deploy_df)}", flush=True)

    # 4) Compute metrics
    print("[4/5] Computing Sharpe / CAGR / DD / Calmar...", flush=True)
    uncond_ret = deploy_df["ret"].values
    cond_ret = deploy_df["ret_conditional"].values
    uncond_sharpe = compute_sharpe(uncond_ret)
    cond_sharpe = compute_sharpe(cond_ret)
    uncond_cagr, uncond_dd, uncond_calmar = compute_calmar(uncond_ret)
    cond_cagr, cond_dd, cond_calmar = compute_calmar(cond_ret)
    print(f"      Sharpe : uncond {uncond_sharpe:.3f} / cond {cond_sharpe:.3f} "
          f"(Δ {cond_sharpe - uncond_sharpe:+.3f})", flush=True)

    # 5) Permutation test
    print(f"[5/5] Permutation test ({PERMUTATION_ITER} iter, seed={SEED})...", flush=True)
    real_sharpe, p_value = permutation_test(
        uncond_ret, deploy_df["deploy"].values,
        n_iter=PERMUTATION_ITER, seed=SEED,
    )
    # Compute shuffle distribution stats
    rng = np.random.RandomState(SEED)
    shuffled = []
    deploy_sig = deploy_df["deploy"].values.astype(int)
    for _ in range(PERMUTATION_ITER):
        permuted = rng.permutation(deploy_sig)
        mask = ~np.isnan(uncond_ret)
        sh = compute_sharpe(uncond_ret[mask] * permuted[mask])
        shuffled.append(sh)
    shuffled = np.array(shuffled)
    print(f"      Real Sharpe = {real_sharpe:.3f}, shuffled mean = {shuffled.mean():.3f}, "
          f"p-value = {p_value:.4f}", flush=True)

    # 6) Audit + verdict
    audit = audit_table(deploy_df, args.threshold)
    delta = cond_sharpe - uncond_sharpe
    if delta > 0.3 and p_value < 0.10:
        decision = "Stage 1 PASS candidate — proceed to Stage 2 robustness"
        emoji = "✅ STAGE 1 PASS"
    elif delta > 0.3:
        decision = (f"Conditional Sharpe gain Δ={delta:+.3f} > 0.3 mais permutation p={p_value:.4f} ≥ 0.10 → "
                    f"random labels match real → ARCHIVE (HMM detecte du bruit)")
        emoji = "🛑 ARCHIVE (perm fail)"
    elif p_value < 0.10:
        decision = (f"Permutation p={p_value:.4f} < 0.10 mais conditional Sharpe gain Δ={delta:+.3f} ≤ 0.3 → "
                    f"real beats random sur magnitude trop faible → ARCHIVE (regime gate sans valeur)")
        emoji = "🛑 ARCHIVE (gain<0.3)"
    else:
        decision = (f"Conditional Sharpe Δ={delta:+.3f} ≤ 0.3 ET permutation p={p_value:.4f} ≥ 0.10 → "
                    f"ARCHIVE (regime gate ineffective sur TSMOM)")
        emoji = "🛑 ARCHIVE (both fail)"

    params = {
        "threshold": args.threshold,
        "n_components": args.n_components,
        "training_window": args.training_window,
        "date_min": str(deploy_df["date"].min().date()),
        "date_max": str(deploy_df["date"].max().date()),
    }
    results = {
        "uncond_sharpe": uncond_sharpe,
        "cond_sharpe": cond_sharpe,
        "uncond_cagr": uncond_cagr,
        "cond_cagr": cond_cagr,
        "uncond_dd": uncond_dd,
        "cond_dd": cond_dd,
        "uncond_calmar": uncond_calmar,
        "cond_calmar": cond_calmar,
    }
    perm_data = {
        "n_iter": PERMUTATION_ITER,
        "seed": SEED,
        "real_sharpe": real_sharpe,
        "shuffled_mean": float(shuffled.mean()),
        "shuffled_p95": float(np.percentile(shuffled, 95)),
        "p_value": p_value,
    }
    md = render_verdict(
        params=params, results=results, audit=audit, perm=perm_data,
        decision=decision, decision_emoji=emoji,
    )
    out_md = args.out_dir / "cycle2_hmm_tsmom_verdict.md"
    out_md.write_text(md, encoding="utf-8")
    # Persist deploy_df for audit
    deploy_df.to_parquet(args.out_dir / "cycle2_hmm_tsmom_deploy.parquet", index=False)
    # Persist regime probas
    regime.to_parquet(args.out_dir / "cycle2_hmm_regime_probas.parquet", index=False)

    print(f"\n=== Verdict → {out_md}", flush=True)
    print(f"=== Decision : {emoji}", flush=True)
    print(f"=== {decision}", flush=True)


if __name__ == "__main__":
    main()
