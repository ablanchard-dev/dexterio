#!/usr/bin/env python3
"""Phase B1 — SL/TP/duration calibration from calib_corpus_v1.

Reads calibration corpus (B0.4 output) and proposes per-playbook YAML deltas.

Per plan:
  SL_proposal         = pXX(|mae_r|, wins)      — protects winners (tight enough)
  TP1_proposal        = pYY(peak_r, non_SL)     — where most MFE lands
  max_dur_proposal    = pZZ(duration, wins)
  trailing (grid)     = deferred to B2 (needs per-bar MFE series not in trades parquet)

Adaptive percentiles (the plan's p95/p60/p75 need ≥20 wins — only Liquidity_Sweep_Scalp
qualifies strictly). For 10-19 wins we relax one notch (p85/p55/p70, confidence MEDIUM).
For <10 wins we relax again (p80/p50/p65, confidence LOW).

Outputs:
  backend/data/backtest_results/calibration_patch_v1.yml
  backend/data/backtest_results/calibration_report_v1.md

Usage:
  python backend/scripts/calibrate_sl_tp.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
import yaml

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from utils.path_resolver import results_path  # noqa: E402

CORPUS_DIR = Path(results_path("labs", "mini_week", "calib_corpus_v1"))
YAML_PATH = backend_dir / "knowledge" / "playbooks.yml"
OUT_PATCH = backend_dir / "data" / "backtest_results" / "calibration_patch_v1.yml"
OUT_REPORT = backend_dir / "data" / "backtest_results" / "calibration_report_v1.md"

TARGETS = [
    "Morning_Trap_Reversal",
    "Engulfing_Bar_V056",
    "BOS_Scalp_1m",
    "Liquidity_Sweep_Scalp",
]


def _load_corpus() -> pd.DataFrame:
    dfs: List[pd.DataFrame] = []
    for p in sorted(CORPUS_DIR.glob("*/trades_*.parquet")):
        dfs.append(pd.read_parquet(p))
    if not dfs:
        raise RuntimeError(f"No trades parquets found under {CORPUS_DIR}")
    return pd.concat(dfs, ignore_index=True)


def _load_yaml() -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    raw = yaml.safe_load(YAML_PATH.read_text())
    pbs = raw if isinstance(raw, list) else raw.get("playbooks", [])
    return raw, pbs


def _current(pb: Dict[str, Any]) -> Dict[str, Any]:
    tp = pb.get("take_profit_logic", {}) or {}
    sl = pb.get("stop_loss_logic", {}) or {}
    return {
        "tp1_rr": tp.get("tp1_rr"),
        "tp2_rr": tp.get("tp2_rr"),
        "breakeven_at_rr": tp.get("breakeven_at_rr"),
        "trailing_trigger_rr": tp.get("trailing_trigger_rr"),
        "trailing_offset_rr": tp.get("trailing_offset_rr"),
        "max_duration_minutes": pb.get("max_duration_minutes"),
        "sl_type": sl.get("type"),
        "sl_distance": sl.get("distance"),
    }


def _pct_levels(n_wins: int) -> Tuple[float, float, float, str]:
    """Return (sl_mae_pct, tp_peak_pct, duration_pct, confidence) for given win count."""
    if n_wins >= 20:
        return 95.0, 60.0, 75.0, "HIGH"
    if n_wins >= 10:
        return 85.0, 55.0, 70.0, "MEDIUM"
    if n_wins >= 5:
        return 80.0, 50.0, 65.0, "LOW"
    return 75.0, 50.0, 60.0, "VERY_LOW"


def _calibrate_pb(pb: str, df_all: pd.DataFrame) -> Dict[str, Any]:
    g = df_all[df_all["playbook"] == pb].copy()
    wins = g[g["outcome"] == "win"]
    non_sl = g[g["exit_reason"] != "SL"]
    sl_pct, tp_pct, dur_pct, conf = _pct_levels(len(wins))
    out: Dict[str, Any] = {
        "n_trades": int(len(g)),
        "n_wins": int(len(wins)),
        "n_non_sl": int(len(non_sl)),
        "wr": float(len(wins) / len(g)) if len(g) else 0.0,
        "e_r": float(g["r_multiple"].mean()) if len(g) else 0.0,
        "avg_peak_r": float(g["peak_r"].mean()) if len(g) else 0.0,
        "time_stop_pct": float((g["exit_reason"] == "time_stop").mean()) if len(g) else 0.0,
        "confidence": conf,
        "percentiles_used": {"sl_mae": sl_pct, "tp_peak": tp_pct, "duration": dur_pct},
    }
    # SL proposal from wins' |mae_r|. Pad +10% for safety.
    if len(wins) > 0:
        sl_from_wins = float(np.percentile(wins["mae_r"].abs(), sl_pct))
        out["sl_proposal_r"] = round(sl_from_wins * 1.10, 2)  # 10% buffer
    else:
        out["sl_proposal_r"] = None
    # TP1 from non-SL peak_r (where the MFE typically lands)
    if len(non_sl) > 0:
        out["tp1_proposal_rr"] = round(float(np.percentile(non_sl["peak_r"], tp_pct)), 2)
    else:
        out["tp1_proposal_rr"] = None
    # Max duration from wins
    if len(wins) > 0:
        out["max_duration_proposal"] = int(np.percentile(wins["duration_minutes"], dur_pct))
    else:
        out["max_duration_proposal"] = None
    # Breakeven recommendation: at 0.7 × TP1_proposal (lock in most of MFE before reversal)
    if out["tp1_proposal_rr"] is not None and out["tp1_proposal_rr"] > 0.5:
        out["breakeven_proposal_rr"] = round(out["tp1_proposal_rr"] * 0.7, 2)
    else:
        out["breakeven_proposal_rr"] = None
    # Diagnostics: wins by exit_reason, peak_r of time_stop wins
    out["wins_by_exit"] = wins["exit_reason"].value_counts().to_dict() if len(wins) else {}
    ts_wins = wins[wins["exit_reason"] == "time_stop"]
    if len(ts_wins) > 0:
        out["time_stop_win_peak_p50"] = float(ts_wins["peak_r"].quantile(0.5))
        out["time_stop_win_peak_p75"] = float(ts_wins["peak_r"].quantile(0.75))
    return out


def _build_patch_entry(pb_name: str, current: Dict[str, Any], proposal: Dict[str, Any]) -> Dict[str, Any]:
    """Return only the keys that should change in YAML for this playbook."""
    patch: Dict[str, Any] = {}
    # TP1 change
    if proposal["tp1_proposal_rr"] is not None:
        if current["tp1_rr"] is None or abs((current["tp1_rr"] or 0) - proposal["tp1_proposal_rr"]) > 0.1:
            patch.setdefault("take_profit_logic", {})["tp1_rr"] = proposal["tp1_proposal_rr"]
            patch["take_profit_logic"]["min_rr"] = proposal["tp1_proposal_rr"]
    # Breakeven change
    if proposal["breakeven_proposal_rr"] is not None:
        cur_be = current["breakeven_at_rr"]
        if cur_be is None or cur_be > 50 or abs(cur_be - proposal["breakeven_proposal_rr"]) > 0.1:
            patch.setdefault("take_profit_logic", {})["breakeven_at_rr"] = proposal["breakeven_proposal_rr"]
    # Max duration change
    if proposal["max_duration_proposal"] is not None:
        cur_dur = current["max_duration_minutes"]
        if cur_dur is None or abs(cur_dur - proposal["max_duration_proposal"]) > 5:
            patch["max_duration_minutes"] = int(proposal["max_duration_proposal"])
    return patch


def _fmt_rr(v: Any) -> str:
    return "—" if v is None else f"{v:.2f}"


def _fmt_int(v: Any) -> str:
    return "—" if v is None else f"{int(v)}"


def _write_patch_yaml(patches: Dict[str, Dict[str, Any]]) -> None:
    doc_lines = [
        "# Phase B1 — calibration_patch_v1",
        "# Generated by backend/scripts/calibrate_sl_tp.py from calib_corpus_v1/",
        "# Apply manually — each delta is documented in calibration_report_v1.md",
        "",
    ]
    for pb_name, delta in patches.items():
        if not delta:
            doc_lines.append(f"# {pb_name}: no change proposed")
            doc_lines.append("")
            continue
        wrapper = [{"playbook_name": pb_name, **delta}]
        doc_lines.append(yaml.safe_dump(wrapper, sort_keys=False, default_flow_style=False, indent=2).rstrip())
        doc_lines.append("")
    OUT_PATCH.write_text("\n".join(doc_lines))


def _reviewer_caveats(rows: List[Dict[str, Any]]) -> List[str]:
    """Produce explicit caveats for B1.3 human review — the numbers alone are misleading."""
    lines = ["## ⚠️ Reviewer caveats (READ BEFORE APPLYING)", ""]
    for r in rows:
        p = r["proposal"]
        c = r["current"]
        pb = r["name"]
        tp1_new = p["tp1_proposal_rr"]
        tp1_cur = c["tp1_rr"]
        sl_proposal = p["sl_proposal_r"]
        flags = []
        # Signal-quality red flag: proposed TP1 < 0.5R suggests the signal doesn't produce meaningful move
        if tp1_new is not None and tp1_new < 0.5:
            flags.append(
                f"**SIGNAL_QUALITY_SUSPECT** — proposed TP1={tp1_new}R is below 0.5R. "
                f"With full-SL losses at ~1R and winners capped at {tp1_new}R, break-even WR would need "
                f"{(1.0 / (1.0 + tp1_new) * 100):.0f}% (currently {p['wr']*100:.0f}%). "
                f"Calibrating TP down to catch MFE may not fix negative E[R] — the signal itself is weak."
            )
        # TP1 dropped >50% from current
        if tp1_cur and tp1_new and tp1_new < 0.5 * tp1_cur:
            flags.append(
                f"**LARGE_TP1_CUT** — current TP1={tp1_cur}R → {tp1_new}R (drop of {(1 - tp1_new/tp1_cur)*100:.0f}%). "
                f"Validate against B2 re-run before accepting — extreme cuts have overfit risk."
            )
        # time_stop > 50% suggests TP1 was unreachable OR signal weak
        if p["time_stop_pct"] > 0.50:
            flags.append(
                f"**HIGH_TIME_STOP** — {p['time_stop_pct']*100:.0f}% of trades exit on time_stop. "
                f"Either max_duration was too short or TP1 unreachable. Monitor in B2."
            )
        # BOS_Scalp_1m duration mismatch anomaly
        if pb == "BOS_Scalp_1m" and p.get("max_duration_proposal") and c["max_duration_minutes"]:
            if p["max_duration_proposal"] > 2 * c["max_duration_minutes"]:
                flags.append(
                    f"**DURATION_ANOMALY** — current YAML max_duration={c['max_duration_minutes']}m but observed "
                    f"winner durations reach {p['max_duration_proposal']}m. Either YAML is ignored by engine "
                    f"(bug) or `time_stop` triggers on a different limit. Investigate before applying."
                )
        # Low win count warning
        if p["n_wins"] < 10:
            flags.append(
                f"**LOW_WIN_SAMPLE** — only {p['n_wins']} wins. Proposed SL ({sl_proposal}R) sits on "
                f"thin statistics; expect instability in B2 validation."
            )
        if flags:
            lines.append(f"### {pb}")
            for f in flags:
                lines.append(f"- {f}")
            lines.append("")
    # Overall verdict
    lines.append("### Overall verdict")
    lines.append("")
    lines.append("- **Safest apply**: Morning_Trap_Reversal only (small TP/BE/duration tweaks, TP1≥3R preserved).")
    lines.append("- **Conditional apply**: Liquidity_Sweep_Scalp (HIGH confidence on percentiles) — but proposed TP1=0.28R is a red flag for signal weakness, not TP misplacement. Consider A/B in B2 (current YAML vs patch).")
    lines.append("- **Hold / investigate first**: BOS_Scalp_1m (duration anomaly) + Engulfing_Bar_V056 (large TP1 cut, signal-quality flag).")
    lines.append("- **Root cause likely upstream**: the cluster of low proposed TP1s (<0.7R) across 3/4 playbooks suggests the detectors fire on weak setups, not that TP1 is mis-placed. Phase C (regime/VWAP filters) may fix more than Phase B1 calibration can.")
    lines.append("")
    return lines


def _write_report(report_rows: List[Dict[str, Any]]) -> None:
    lines: List[str] = []
    lines.append("# Phase B1 — calibration_report_v1")
    lines.append("")
    lines.append("**Source corpus:** `calib_corpus_v1` (4 weeks, caps actives, allowlist 4 targets, 170 trades total).")
    lines.append("**Method:** adaptive percentiles by win count (HIGH/MEDIUM/LOW confidence). SL from p95/p85/p80 of `|mae_r|` on wins +10% buffer. TP1 from p60/p55/p50 of `peak_r` on non-SL exits. Max duration from p75/p70/p65 of wins. Breakeven at 0.7×TP1.")
    lines.append("**Deferred to B2:** trailing grid (needs per-bar MFE series — not in trades parquet). Current trailing values kept as-is.")
    lines.append("")
    lines.extend(_reviewer_caveats(report_rows))
    lines.append("## Summary table")
    lines.append("")
    lines.append("| playbook | n | wins | WR | E[R] | avg_peak_R | time_stop% | conf | SL curr→new | TP1 curr→new | BE curr→new | MaxDur curr→new |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in report_rows:
        c = r["current"]
        p = r["proposal"]
        sl_c = "SWING" if c["sl_type"] == "SWING" else _fmt_rr(None)
        sl_n = _fmt_rr(p["sl_proposal_r"]) + "R"
        lines.append(
            f"| {r['name']} | {p['n_trades']} | {p['n_wins']} | {p['wr']*100:.1f}% | "
            f"{p['e_r']:+.3f} | {p['avg_peak_r']:+.2f} | {p['time_stop_pct']*100:.0f}% | "
            f"{p['confidence']} | {sl_c}→{sl_n} | "
            f"{_fmt_rr(c['tp1_rr'])}→{_fmt_rr(p['tp1_proposal_rr'])} | "
            f"{_fmt_rr(c['breakeven_at_rr'])}→{_fmt_rr(p['breakeven_proposal_rr'])} | "
            f"{_fmt_int(c['max_duration_minutes'])}→{_fmt_int(p['max_duration_proposal'])} |"
        )
    lines.append("")
    for r in report_rows:
        pb = r["name"]
        c = r["current"]
        p = r["proposal"]
        delta = r["delta"]
        lines.append(f"## {pb}")
        lines.append("")
        lines.append(f"- **Corpus**: n={p['n_trades']}, wins={p['n_wins']}, WR={p['wr']*100:.1f}%, E[R]={p['e_r']:+.3f}, avg peak_R={p['avg_peak_r']:+.2f}, time_stop={p['time_stop_pct']*100:.0f}%")
        lines.append(f"- **Confidence**: `{p['confidence']}` (percentiles used: SL=p{p['percentiles_used']['sl_mae']:.0f} MAE, TP=p{p['percentiles_used']['tp_peak']:.0f} peak, dur=p{p['percentiles_used']['duration']:.0f})")
        lines.append(f"- **Wins by exit**: {p['wins_by_exit']}")
        if "time_stop_win_peak_p50" in p:
            lines.append(f"- **Time-stop wins peak_R**: p50={p['time_stop_win_peak_p50']:.2f}, p75={p['time_stop_win_peak_p75']:.2f}")
        lines.append("")
        lines.append("**Current vs proposed:**")
        lines.append(f"- SL: `{c['sl_type']}/{c['sl_distance']}` → proposed R-cap ≤ **{_fmt_rr(p['sl_proposal_r'])}R** (kept structural if SWING — new cap just protects downside)")
        lines.append(f"- TP1: `{_fmt_rr(c['tp1_rr'])}R` → **{_fmt_rr(p['tp1_proposal_rr'])}R**")
        lines.append(f"- TP2: `{_fmt_rr(c['tp2_rr'])}R` (unchanged)")
        lines.append(f"- Breakeven: `{_fmt_rr(c['breakeven_at_rr'])}R` → **{_fmt_rr(p['breakeven_proposal_rr'])}R**")
        lines.append(f"- Max duration: `{_fmt_int(c['max_duration_minutes'])}m` → **{_fmt_int(p['max_duration_proposal'])}m**")
        lines.append(f"- Trailing: `trigger={_fmt_rr(c['trailing_trigger_rr'])}R, offset={_fmt_rr(c['trailing_offset_rr'])}R` (unchanged — B2 grid search)")
        lines.append("")
        if delta:
            lines.append("**YAML delta (`calibration_patch_v1.yml` entry):**")
            lines.append("```yaml")
            lines.append(f"- playbook_name: {pb}")
            lines.append(yaml.safe_dump(delta, sort_keys=False, default_flow_style=False, indent=2).rstrip())
            lines.append("```")
        else:
            lines.append("**No change proposed** (deltas below threshold or confidence too low).")
        lines.append("")
        # Reasoning
        lines.append("**Reasoning:**")
        if p["tp1_proposal_rr"] is not None and c["tp1_rr"] is not None:
            if p["tp1_proposal_rr"] < c["tp1_rr"] - 0.2:
                lines.append(f"- Current TP1={c['tp1_rr']}R rarely hit. Corpus p{p['percentiles_used']['tp_peak']:.0f} of peak_R on non-SL exits = {p['tp1_proposal_rr']}R → lowering TP1 captures MFE that currently expires at time_stop.")
            elif p["tp1_proposal_rr"] > c["tp1_rr"] + 0.2:
                lines.append(f"- Current TP1={c['tp1_rr']}R leaves money on the table. Corpus p{p['percentiles_used']['tp_peak']:.0f} peak_R = {p['tp1_proposal_rr']}R → raising TP1 captures observed extensions.")
        if p["breakeven_proposal_rr"] is not None and (c["breakeven_at_rr"] is None or c["breakeven_at_rr"] > 50):
            lines.append(f"- Breakeven currently disabled/999. Setting to {p['breakeven_proposal_rr']}R (= 0.7×TP1) limits reversal losses after move starts.")
        if p["max_duration_proposal"] is not None and c["max_duration_minutes"] is not None:
            dd = p["max_duration_proposal"] - c["max_duration_minutes"]
            if abs(dd) > 5:
                direction = "increase" if dd > 0 else "decrease"
                lines.append(f"- Max duration p{p['percentiles_used']['duration']:.0f} of wins = {p['max_duration_proposal']}m (current {c['max_duration_minutes']}m) → {direction} aligns cutoff with actual winner duration.")
        lines.append("")
    OUT_REPORT.write_text("\n".join(lines))


def main() -> int:
    print("[B1] Loading corpus...")
    df = _load_corpus()
    print(f"[B1] Loaded {len(df)} trades from {CORPUS_DIR}")
    print("[B1] Loading YAML...")
    raw_yaml, pbs_list = _load_yaml()
    by_name = {pb.get("playbook_name"): pb for pb in pbs_list}

    report_rows: List[Dict[str, Any]] = []
    patches: Dict[str, Dict[str, Any]] = {}
    for pb_name in TARGETS:
        if pb_name not in by_name:
            print(f"[B1] MISSING from YAML: {pb_name}")
            continue
        cur = _current(by_name[pb_name])
        prop = _calibrate_pb(pb_name, df)
        delta = _build_patch_entry(pb_name, cur, prop)
        report_rows.append({"name": pb_name, "current": cur, "proposal": prop, "delta": delta})
        patches[pb_name] = delta
        print(f"[B1] {pb_name}: {len(delta)} delta key(s), conf={prop['confidence']}")

    _write_patch_yaml(patches)
    _write_report(report_rows)
    print(f"[B1] Wrote {OUT_PATCH}")
    print(f"[B1] Wrote {OUT_REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
