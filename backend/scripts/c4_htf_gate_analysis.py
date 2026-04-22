#!/usr/bin/env python3
"""
Phase C.4 analysis: selective D-HTF alignment gate.

Compares baseline calib_corpus_v1 vs c4_htf_gate_v1 per playbook:
- n, WR, E[R], total_R
- Direction split (LONG/SHORT)
- Computes bias-rejection rate for the 2 gated playbooks from matches_by_playbook
  vs setups_created_by_playbook delta.

Prints a markdown-ready table to stdout.
"""
import json
from pathlib import Path
from typing import Dict, List, Tuple
import pandas as pd

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
LABS = BACKEND / "results" / "labs" / "mini_week"

WEEKS = ["jun_w3", "aug_w3", "oct_w2", "nov_w4"]
TARGETS = [
    "Morning_Trap_Reversal",
    "Engulfing_Bar_V056",
    "BOS_Scalp_1m",
    "Liquidity_Sweep_Scalp",
]
GATED = {"Engulfing_Bar_V056", "BOS_Scalp_1m"}
CONTROLS = {"Morning_Trap_Reversal", "Liquidity_Sweep_Scalp"}


def load_trades(variant: str) -> pd.DataFrame:
    frames = []
    for w in WEEKS:
        p = LABS / variant / w / f"trades_miniweek_{variant}_{w}_AGGRESSIVE_DAILY_SCALP.parquet"
        if not p.exists():
            continue
        df = pd.read_parquet(p)
        df["week"] = w
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def load_debug_counts(variant: str) -> Dict[str, Dict]:
    out: Dict[str, Dict] = {}
    for w in WEEKS:
        p = LABS / variant / w / f"debug_counts_miniweek_{variant}_{w}.json"
        if not p.exists():
            continue
        out[w] = json.loads(p.read_text())["counts"]
    return out


def summarize(df: pd.DataFrame) -> Dict[str, Dict]:
    out: Dict[str, Dict] = {}
    for pb in TARGETS:
        sub = df[df["playbook"] == pb]
        n = int(len(sub))
        if n == 0:
            out[pb] = {"n": 0, "wr": float("nan"), "er": float("nan"), "total_r": 0.0,
                       "dir_long": 0, "dir_short": 0}
            continue
        r = sub["r_multiple"]
        out[pb] = {
            "n": n,
            "wr": float((r > 0).mean()),
            "er": float(r.mean()),
            "total_r": float(r.sum()),
            "dir_long": int((sub["direction"] == "LONG").sum()),
            "dir_short": int((sub["direction"] == "SHORT").sum()),
        }
    return out


def compute_gate_rejection(base_counts: Dict, c4_counts: Dict, pb: str) -> Dict[str, int]:
    """
    Approximates HTF gate rejection rate by comparing:
      base matches_by_playbook - c4 matches_by_playbook = engine-drift noise
      base setups_created_by_playbook - c4 setups_created_by_playbook = gate + engine-drift

    The cleanest per-week approximation of the gate effect is:
      (c4 matches_by_playbook - c4 setups_created_by_playbook) = setups rejected
        at the _create_setup_from_playbook_match stage (which includes HTF gate for gated pbs)
    """
    agg = {"matches": 0, "setups_created": 0}
    for w in WEEKS:
        cc = c4_counts.get(w, {})
        agg["matches"] += int(cc.get("matches_by_playbook", {}).get(pb, 0))
        agg["setups_created"] += int(cc.get("setups_created_by_playbook", {}).get(pb, 0))
    agg["delta"] = agg["matches"] - agg["setups_created"]
    return agg


def main() -> None:
    base = load_trades("calib_corpus_v1")
    c4 = load_trades("c4_htf_gate_v1")
    if base.empty:
        print("ERROR: calib_corpus_v1 trades not found")
        return
    if c4.empty:
        print("ERROR: c4_htf_gate_v1 trades not found")
        return

    base_s = summarize(base)
    c4_s = summarize(c4)

    c4_counts = load_debug_counts("c4_htf_gate_v1")
    base_counts = load_debug_counts("calib_corpus_v1")

    SLIPPAGE = -0.065

    lines = []
    lines.append("# C.4 HTF gate — analysis output\n")
    lines.append("## Per-playbook trade metrics (4-week aggregate)\n")
    lines.append("| playbook | kind | base n | c4 n | Δn | base E[R] | c4 E[R] | ΔE[R] | c4 net E[R] (−0.065 slip) | base WR | c4 WR | base total_R | c4 total_R |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for pb in TARGETS:
        kind = "GATED (D)" if pb in GATED else "control"
        b = base_s[pb]
        c = c4_s[pb]
        dn = c["n"] - b["n"]
        der = c["er"] - b["er"]
        lines.append(
            f"| {pb} | {kind} | {b['n']} | {c['n']} | {dn:+d} | {b['er']:+.4f} | {c['er']:+.4f} | "
            f"{der:+.4f} | {c['er']+SLIPPAGE:+.4f} | {b['wr']:.2%} | {c['wr']:.2%} | "
            f"{b['total_r']:+.3f} | {c['total_r']:+.3f} |"
        )

    lines.append("\n## Direction distribution (LONG/SHORT)\n")
    lines.append("| playbook | base L/S | c4 L/S |")
    lines.append("|---|---|---|")
    for pb in TARGETS:
        b = base_s[pb]
        c = c4_s[pb]
        lines.append(f"| {pb} | {b['dir_long']}/{b['dir_short']} | {c['dir_long']}/{c['dir_short']} |")

    lines.append("\n## Gate funnel (matches → setups_created) in c4 run\n")
    lines.append("| playbook | matches | setups_created | rejected | reject% |")
    lines.append("|---|---|---|---|---|")
    for pb in TARGETS:
        ag = compute_gate_rejection(base_counts, c4_counts, pb)
        rej_pct = (ag["delta"] / ag["matches"] * 100.0) if ag["matches"] else 0.0
        lines.append(f"| {pb} | {ag['matches']} | {ag['setups_created']} | {ag['delta']} | {rej_pct:.1f}% |")

    lines.append("\n## Per-week per-playbook E[R]\n")
    lines.append("| playbook | kind | week | base n | c4 n | base E[R] | c4 E[R] | ΔE[R] |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for pb in TARGETS:
        kind = "GATED" if pb in GATED else "control"
        for w in WEEKS:
            b = base[(base["playbook"] == pb) & (base["week"] == w)]
            c = c4[(c4["playbook"] == pb) & (c4["week"] == w)]
            bn, cn = len(b), len(c)
            ber = float(b["r_multiple"].mean()) if bn else float("nan")
            cer = float(c["r_multiple"].mean()) if cn else float("nan")
            der_s = f"{cer-ber:+.4f}" if (bn and cn) else "n/a"
            lines.append(f"| {pb} | {kind} | {w} | {bn} | {cn} | {ber:+.4f} | {cer:+.4f} | {der_s} |")

    # Verdict
    lines.append("\n## Verdict logic\n")
    lines.append("**Hypothesis**: D-alignment helps continuation-type plays (+0.07 to +0.27 per bias_audit_v1).")
    for pb in GATED:
        b, c = base_s[pb], c4_s[pb]
        improved = (c["er"] > b["er"])
        crossed = (c["er"] > 0)
        lines.append(f"- **{pb}** (GATED): base E[R]={b['er']:+.4f}, c4 E[R]={c['er']:+.4f}, Δ={c['er']-b['er']:+.4f} — "
                     f"improved: {improved}, crosses zero: {crossed}")
    for pb in CONTROLS:
        b, c = base_s[pb], c4_s[pb]
        stable = abs(c["er"] - b["er"]) < 0.04
        lines.append(f"- **{pb}** (control): base E[R]={b['er']:+.4f}, c4 E[R]={c['er']:+.4f}, Δ={c['er']-b['er']:+.4f} — "
                     f"within ±0.04: {stable}")

    # Aggregate portfolio (4 targets)
    agg_base_n = sum(base_s[pb]["n"] for pb in TARGETS)
    agg_c4_n = sum(c4_s[pb]["n"] for pb in TARGETS)
    agg_base_r = sum(base_s[pb]["total_r"] for pb in TARGETS)
    agg_c4_r = sum(c4_s[pb]["total_r"] for pb in TARGETS)
    lines.append(f"\n## Portfolio aggregate (4 targets)\n")
    lines.append(f"- Base: n={agg_base_n}, total_R={agg_base_r:+.3f}, E[R]={agg_base_r/agg_base_n if agg_base_n else 0:+.4f}")
    lines.append(f"- c4:   n={agg_c4_n}, total_R={agg_c4_r:+.3f}, E[R]={agg_c4_r/agg_c4_n if agg_c4_n else 0:+.4f}")
    lines.append(f"- Net c4 (after −0.065 slip): E[R]={(agg_c4_r/agg_c4_n if agg_c4_n else 0)+SLIPPAGE:+.4f}")

    out = "\n".join(lines)
    print(out)


if __name__ == "__main__":
    main()
