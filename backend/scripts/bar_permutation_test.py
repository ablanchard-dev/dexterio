"""Stage 3 gate O5.3 — Bar permutation test for strategy edge (plan §0.7 item #5).

Tests whether total_R (or E[R]) of a strategy is statistically distinguishable from
random ordering of its R-multiples. Null hypothesis : sequence of wins/losses is
exchangeable → permuted total_R ≥ observed should have p >> 0.05 if strategy has
no edge beyond individual trade R-multiples (this variant tests SEQUENCE/CLUSTERING
alpha, not alpha in the distribution itself — distribution alpha is already visible
in E[R]).

A stricter "shuffle-then-refill" test requires redoing entry signals on permuted
bar data — that's a heavier lift (see plan §0.7). This v1 is the "trades permutation"
flavor, useful for cohort-level sign checks.

Usage :
    .venv/bin/python scripts/bar_permutation_test.py <trades.parquet> [--iterations 1000]
    .venv/bin/python scripts/bar_permutation_test.py --cohort survivor_v1
    .venv/bin/python scripts/bar_permutation_test.py --cohort htf_bias_15m_bos_solo_12w
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_cohort_trades(cohort: str) -> pd.DataFrame:
    labs = REPO_ROOT / "results" / "labs" / "mini_week"
    if cohort == "survivor_v1":
        frames = []
        for w in ("jun_w3", "aug_w3", "oct_w2", "nov_w4"):
            p = labs / "survivor_v1" / w / f"trades_miniweek_survivor_v1_{w}_AGGRESSIVE_DAILY_SCALP.parquet"
            df = pd.read_parquet(p)
            df["week_label"] = w
            frames.append(df)
        df = pd.concat(frames, ignore_index=True)
        survivors = ["News_Fade", "Engulfing_Bar_V056", "Session_Open_Scalp", "Liquidity_Sweep_Scalp"]
        df = df[df["playbook"].isin(survivors)].copy()
        return df
    if cohort == "htf_bias_15m_bos_solo_12w":
        root = labs / "htf_bias_15m_bos_solo_12w"
        frames = []
        for p in sorted(root.glob("**/trades_*.parquet")):
            df = pd.read_parquet(p)
            df["week_label"] = p.parent.name
            frames.append(df)
        return pd.concat(frames, ignore_index=True)
    raise ValueError(f"Unknown cohort : {cohort}")


def permutation_test(r_multiples: np.ndarray, iterations: int = 1000, seed: int = 42) -> dict:
    """Sign permutation test on R-multiples.

    Null : expected R under random sign assignment is 0 (each trade's magnitude
    fixed, sign flipped with p=0.5). Tests whether observed E[R] is significantly
    different from 0 under sign-flip null.

    Returns p-value for two-sided test on |E[R]|.
    """
    rng = np.random.default_rng(seed)
    r = np.asarray(r_multiples, dtype=float)
    n = len(r)
    obs_mean = float(r.mean())
    obs_total = float(r.sum())

    magnitudes = np.abs(r)
    count_ge = 0
    count_le = 0
    permuted_means = np.empty(iterations, dtype=float)
    for i in range(iterations):
        signs = rng.choice([-1.0, 1.0], size=n)
        perm = magnitudes * signs
        pm = float(perm.mean())
        permuted_means[i] = pm
        if pm >= obs_mean:
            count_ge += 1
        if pm <= obs_mean:
            count_le += 1

    p_one_sided_ge = count_ge / iterations
    p_one_sided_le = count_le / iterations
    p_two_sided = float(2 * min(p_one_sided_ge, p_one_sided_le))

    return {
        "n": n,
        "iterations": iterations,
        "observed_E_R": obs_mean,
        "observed_total_R": obs_total,
        "permuted_E_R_mean": float(permuted_means.mean()),
        "permuted_E_R_std": float(permuted_means.std(ddof=1)),
        "permuted_E_R_p5": float(np.quantile(permuted_means, 0.05)),
        "permuted_E_R_p95": float(np.quantile(permuted_means, 0.95)),
        "p_one_sided_ge": p_one_sided_ge,
        "p_one_sided_le": p_one_sided_le,
        "p_two_sided": p_two_sided,
        "gate_O53_pass": (p_two_sided < 0.05) and (obs_mean > 0),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("trades_parquet", nargs="?", help="Path to trades.parquet")
    ap.add_argument("--cohort", choices=["survivor_v1", "htf_bias_15m_bos_solo_12w"], help="Preset cohort loader")
    ap.add_argument("--iterations", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out-json", help="Write results JSON to this path")
    ap.add_argument("--split-by", help="Column to split results on (e.g. 'playbook')")
    args = ap.parse_args()

    if args.cohort:
        df = load_cohort_trades(args.cohort)
        label = args.cohort
    elif args.trades_parquet:
        df = pd.read_parquet(args.trades_parquet)
        label = Path(args.trades_parquet).stem
    else:
        print("ERROR : must provide trades_parquet or --cohort", file=sys.stderr)
        return 1

    results = {"label": label, "total_trades_loaded": len(df), "cohort": {}}
    cohort_result = permutation_test(df["r_multiple"].values, iterations=args.iterations, seed=args.seed)
    results["cohort"] = cohort_result

    print(f"\n=== cohort={label} n={cohort_result['n']} ===")
    print(f"observed E[R]       = {cohort_result['observed_E_R']:+.4f}")
    print(f"permuted E[R] mean  = {cohort_result['permuted_E_R_mean']:+.4f}  (std {cohort_result['permuted_E_R_std']:.4f})")
    print(f"permuted E[R] p5/p95= {cohort_result['permuted_E_R_p5']:+.4f} / {cohort_result['permuted_E_R_p95']:+.4f}")
    print(f"p two-sided         = {cohort_result['p_two_sided']:.4f}")
    print(f"gate O5.3 PASS      = {cohort_result['gate_O53_pass']}  (requires p<0.05 AND E[R]>0)")

    if args.split_by and args.split_by in df.columns:
        results["splits"] = {}
        for group_val, sub in df.groupby(args.split_by):
            sr = permutation_test(sub["r_multiple"].values, iterations=args.iterations, seed=args.seed)
            results["splits"][str(group_val)] = sr
            print(f"  {args.split_by}={group_val:30s} n={sr['n']:4d} E[R]={sr['observed_E_R']:+.4f} p={sr['p_two_sided']:.3f}")

    if args.out_json:
        Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
        with open(args.out_json, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nwrote {args.out_json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
