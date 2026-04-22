#!/usr/bin/env python3
"""
Audit 3 — scoring predictive power.

Read-only. For each playbook with n>=30 trades, tests whether `match_score`
and `match_grade` predict `r_multiple`:

  - Pearson correlation match_score vs r_multiple
  - Spearman rank correlation (robust to outliers)
  - E[R] by grade bucket (A_plus / A / B / C)
  - Monotonic check: does higher grade → higher E[R]?

Also global across all playbooks.

If |corr| < 0.1 → scoring has no predictive power, grading is decorative.
If monotonicity fails → the thresholds A+/A/B are meaningless.
"""
from __future__ import annotations
import argparse
import glob
import json
from pathlib import Path
import pandas as pd
import numpy as np
from scipy.stats import pearsonr, spearmanr


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_all_trades() -> pd.DataFrame:
    patterns = [
        "backend/results/labs/mini_week/fair_*/trades_*.parquet",
        "backend/results/labs/mini_week/survivor_v1/*/trades_*.parquet",
        "backend/results/labs/mini_week/aplus03_v2/*/trades_*.parquet",
        "backend/results/labs/mini_week/b_aplus04_v1/*/trades_*.parquet",
        "backend/results/labs/mini_week/r3_aplus03_tpcalib_v1/*/trades_*.parquet",
        "backend/results/labs/mini_week/calib_corpus_v1/*/trades_*.parquet",
    ]
    dfs = []
    for pat in patterns:
        for f in glob.glob(str(REPO_ROOT / pat)):
            if "normalcaps" in f:
                continue
            try:
                df = pd.read_parquet(f)
                df["_source"] = Path(f).parent.parent.name
                dfs.append(df)
            except Exception:
                pass
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def score_analysis(sub: pd.DataFrame) -> dict:
    """Run all correlation tests on a playbook subset."""
    ret = {}
    s = sub.dropna(subset=["match_score", "r_multiple"])
    if len(s) < 10:
        return {"n": len(s), "insufficient": True}

    try:
        pr, pr_p = pearsonr(s["match_score"], s["r_multiple"])
    except Exception:
        pr, pr_p = float("nan"), float("nan")
    try:
        sr, sr_p = spearmanr(s["match_score"], s["r_multiple"])
    except Exception:
        sr, sr_p = float("nan"), float("nan")

    ret["n"] = int(len(s))
    ret["pearson_r"] = round(float(pr), 4)
    ret["pearson_p"] = round(float(pr_p), 4)
    ret["spearman_r"] = round(float(sr), 4)
    ret["spearman_p"] = round(float(sr_p), 4)
    ret["r_squared"] = round(float(pr) ** 2, 4) if not np.isnan(pr) else None

    # E[R] by grade bucket
    grade_stats = []
    order = ["A_plus", "A", "B", "C", None]
    for grade in order:
        if grade is None:
            gsub = s[s["match_grade"].isna()]
            name = "UNGRADED"
        else:
            gsub = s[s["match_grade"] == grade]
            name = grade
        if len(gsub) < 3:
            continue
        grade_stats.append({
            "grade": name,
            "n": int(len(gsub)),
            "avg_R": round(float(gsub["r_multiple"].mean()), 4),
            "winrate_pct": round(float((gsub["r_multiple"] > 0).mean()) * 100, 1),
            "avg_score": round(float(gsub["match_score"].mean()), 3),
        })
    ret["by_grade"] = grade_stats

    # Monotonicity: A_plus > A > B > C ?
    ordered_grades = [g for g in grade_stats if g["grade"] in ("A_plus", "A", "B", "C")]
    ordered_grades.sort(key=lambda g: ["A_plus", "A", "B", "C"].index(g["grade"]))
    if len(ordered_grades) >= 2:
        er_vals = [g["avg_R"] for g in ordered_grades]
        monotone = all(er_vals[i] >= er_vals[i+1] for i in range(len(er_vals)-1))
        ret["monotone_decreasing_with_grade"] = monotone
        ret["er_sequence"] = er_vals
    else:
        ret["monotone_decreasing_with_grade"] = None

    # Decile analysis: sort by score, compute E[R] per decile
    if len(s) >= 30:
        s_sorted = s.sort_values("match_score").reset_index(drop=True)
        s_sorted["decile"] = pd.qcut(s_sorted["match_score"], 10, labels=False, duplicates="drop")
        dec_er = s_sorted.groupby("decile")["r_multiple"].agg(["count", "mean"]).reset_index()
        ret["decile_er"] = [
            {"decile": int(row["decile"]), "n": int(row["count"]), "avg_R": round(float(row["mean"]), 4)}
            for _, row in dec_er.iterrows()
        ]
    return ret


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="backend/data/backtest_results/audit_scoring_power.json")
    ap.add_argument("--md-out", default="backend/data/backtest_results/audit_scoring_power.md")
    ap.add_argument("--min-n", type=int, default=30)
    args = ap.parse_args()

    df = load_all_trades()
    print(f"Total trades: {len(df)}")
    print(f"Unique playbooks: {df['playbook'].nunique()}")
    print(f"match_score missing: {df['match_score'].isna().sum()}")

    results = {}
    # Global (all trades)
    results["_GLOBAL_"] = score_analysis(df)

    for pb in sorted(df["playbook"].unique()):
        sub = df[df["playbook"] == pb]
        if len(sub.dropna(subset=["match_score"])) < args.min_n:
            continue
        results[pb] = score_analysis(sub)

    out_path = REPO_ROOT / args.out
    out_path.write_text(json.dumps(results, indent=2, default=str))
    print(f"JSON: {out_path}")

    md = [
        "# Audit 3 — scoring predictive power",
        "",
        f"- Total trades: {len(df)}",
        f"- Min n per playbook: {args.min_n}",
        "",
        "## Global (all playbooks merged)",
        "",
    ]
    g = results["_GLOBAL_"]
    md += [
        f"- n = **{g.get('n')}**",
        f"- Pearson r = **{g.get('pearson_r')}** (p={g.get('pearson_p')}, r²={g.get('r_squared')})",
        f"- Spearman r = **{g.get('spearman_r')}** (p={g.get('spearman_p')})",
        "",
        "### E[R] by grade bucket",
        "",
        "| Grade | n | avg_R | WR% | avg_score |",
        "|---|---:|---:|---:|---:|",
    ]
    for b in g.get("by_grade", []):
        md.append(f"| {b['grade']} | {b['n']} | {b['avg_R']:+.4f} | {b['winrate_pct']} | {b['avg_score']} |")
    md.append(f"\n- Monotone decreasing with grade? **{g.get('monotone_decreasing_with_grade')}**")
    if g.get("er_sequence"):
        md.append(f"  - Sequence (A+→C): {g['er_sequence']}")

    md += [
        "",
        "### Decile analysis (score quantiles)",
        "",
        "| Decile | n | avg_R |",
        "|---|---:|---:|",
    ]
    for d in g.get("decile_er", []):
        md.append(f"| {d['decile']} | {d['n']} | {d['avg_R']:+.4f} |")

    md += [
        "",
        "## Per-playbook correlations",
        "",
        "| Playbook | n | Pearson r | p | r² | Spearman r | monotone? | er_sequence |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for pb, r in sorted(results.items()):
        if pb == "_GLOBAL_" or r.get("insufficient"):
            continue
        md.append(
            f"| {pb} | {r.get('n')} | {r.get('pearson_r')} | {r.get('pearson_p')} "
            f"| {r.get('r_squared')} | {r.get('spearman_r')} | "
            f"{r.get('monotone_decreasing_with_grade')} | {r.get('er_sequence')} |"
        )

    md += [
        "",
        "## Lecture",
        "",
        "- **r² < 0.05** → le score n'explique <5% de la variance du r_multiple. Scoring est essentiellement du bruit.",
        "- **|r| < 0.1** → corrélation inexistante. Les grades A+/A/B ne discriminent pas.",
        "- **Monotonicity FALSE** → grade plus haut ≠ meilleur trade. Les thresholds sont mal calibrés OU les poids sont mauvais.",
        "- **Decile analysis** : si E[R] ne monte pas avec le décile de score, le score n'ordonne rien.",
        "",
        "## Implication",
        "",
        "Si |r| < 0.1 ET monotonicity FALSE → **le système de grading est décoratif, pas prédictif**.",
        "Actions possibles (plan séparé) :",
        "- Refondre les poids du scoring avec régression sur les trades historiques (fitted on training half, tested on holdout).",
        "- Ou abandonner le grading, utiliser un seuil binaire simple (détecté ou non).",
        "- Ou remplacer le score par un classifier meta-labeling (López de Prado) — interdit par règle anti-patterns tant que E[R]>0 pas atteint rule-based.",
        "",
    ]
    md_path = REPO_ROOT / args.md_out
    md_path.write_text("\n".join(md))
    print(f"MD: {md_path}")

    print()
    print(f"Global: Pearson r = {g.get('pearson_r')}, r² = {g.get('r_squared')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
