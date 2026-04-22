#!/usr/bin/env python3
"""
Phase C.3 analysis — compare c3_entry_confirm_v1 vs calib_corpus_v1 baseline.
Computes per-playbook deltas (n, E[R], WR, exit_mix) + net E[R] with slippage.
Also extracts setup rejection stats from debug_counts.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, Any, List

import pandas as pd


BASELINE_ROOT = Path('/home/dexter/dexterio1-main/backend/results/labs/mini_week/calib_corpus_v1')
CAMPAIGN_ROOT = Path('/home/dexter/dexterio1-main/backend/results/labs/mini_week/c3_entry_confirm_v1')
WEEKS = ['jun_w3', 'aug_w3', 'oct_w2', 'nov_w4']
TARGETS = ['BOS_Scalp_1m', 'Morning_Trap_Reversal', 'Engulfing_Bar_V056', 'Liquidity_Sweep_Scalp']
SLIPPAGE_BUDGET_R = 0.065  # reconcile harness verdict (-0.065 R / trade)


def load_trades(root: Path, label: str) -> pd.DataFrame:
    dfs: List[pd.DataFrame] = []
    for w in WEEKS:
        p = root / w / f'trades_miniweek_{label}_{w}_AGGRESSIVE_DAILY_SCALP.parquet'
        if not p.exists():
            print(f"MISSING: {p}", file=sys.stderr)
            continue
        df = pd.read_parquet(p)
        df['week'] = w
        dfs.append(df)
    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)


def load_entry_confirm_stats(root: Path, label: str) -> Dict[str, Dict[str, int]]:
    agg: Dict[str, Dict[str, int]] = {}
    for w in WEEKS:
        p = root / w / f'debug_counts_miniweek_{label}_{w}.json'
        if not p.exists():
            continue
        with p.open() as f:
            d = json.load(f)
        ec = d.get('counts', {}).get('entry_confirm_stats', {}) or {}
        for pb, stats in ec.items():
            if pb not in agg:
                agg[pb] = {k: 0 for k in ('checked', 'passed', 'rejected_no_commit', 'rejected_no_candles')}
            for k in ('checked', 'passed', 'rejected_no_commit', 'rejected_no_candles'):
                agg[pb][k] += int(stats.get(k, 0))
    return agg


def per_playbook_stats(df: pd.DataFrame, pb: str) -> Dict[str, Any]:
    sub = df[df['playbook'] == pb]
    n = len(sub)
    if n == 0:
        return {
            'n': 0, 'er': float('nan'), 'er_net': float('nan'),
            'wr': float('nan'), 'total_r': 0.0,
            'SL': 0, 'time_stop': 0, 'TP1': 0, 'eod': 0,
            'sl_share': float('nan'),
        }
    er = float(sub['r_multiple'].mean())
    wr = float((sub['r_multiple'] > 0).mean() * 100)
    total_r = float(sub['r_multiple'].sum())
    ex = sub['exit_reason'].value_counts()
    sl = int(ex.get('SL', 0))
    ts = int(ex.get('time_stop', 0))
    tp1 = int(ex.get('TP1', 0))
    eod = int(ex.get('eod', 0))
    sl_share = sl / n * 100
    return {
        'n': n, 'er': er, 'er_net': er - SLIPPAGE_BUDGET_R,
        'wr': wr, 'total_r': total_r,
        'SL': sl, 'time_stop': ts, 'TP1': tp1, 'eod': eod,
        'sl_share': sl_share,
    }


def main() -> int:
    base = load_trades(BASELINE_ROOT, 'calib_corpus_v1')
    new = load_trades(CAMPAIGN_ROOT, 'c3_entry_confirm_v1')
    ec = load_entry_confirm_stats(CAMPAIGN_ROOT, 'c3_entry_confirm_v1')

    if new.empty:
        print("ERROR: no new trades data loaded", file=sys.stderr)
        return 1

    print("=" * 110)
    print("PHASE C.3 — Entry confirmation gate verdict")
    print(f"Baseline: calib_corpus_v1 | Campaign: c3_entry_confirm_v1 | Weeks: {', '.join(WEEKS)}")
    print(f"Slippage budget: -{SLIPPAGE_BUDGET_R:.3f} R/trade")
    print("=" * 110)
    print()
    print(f"{'playbook':<24} {'role':<9} {'src':<4} {'n':>4} {'E[R]':>8} {'E[R]net':>9} {'WR':>6} {'SL%':>6} {'totalR':>8}")
    print("-" * 110)

    gate_on = {'BOS_Scalp_1m', 'Morning_Trap_Reversal'}
    for pb in TARGETS:
        role = 'TARGET' if pb in gate_on else 'CONTROL'
        b = per_playbook_stats(base, pb)
        n = per_playbook_stats(new, pb)
        print(f"{pb:<24} {role:<9} {'base':<4} {b['n']:>4} {b['er']:>8.3f} {b['er_net']:>9.3f} {b['wr']:>5.1f}% {b['sl_share']:>5.1f}% {b['total_r']:>8.2f}")
        print(f"{'':<24} {'':<9} {'new':<4} {n['n']:>4} {n['er']:>8.3f} {n['er_net']:>9.3f} {n['wr']:>5.1f}% {n['sl_share']:>5.1f}% {n['total_r']:>8.2f}")
        # Deltas
        d_er = n['er'] - b['er']
        d_wr = n['wr'] - b['wr']
        d_sl = n['sl_share'] - b['sl_share']
        print(f"{'':<24} {'':<9} {'Δ':<4} {n['n']-b['n']:>+4d} {d_er:>+8.3f} {n['er_net']-b['er_net']:>+9.3f} {d_wr:>+5.1f}% {d_sl:>+5.1f}% {n['total_r']-b['total_r']:>+8.2f}")
        print()

    print("=" * 110)
    print("Entry-confirm gate stats (aggregated across 4 weeks, gate-enabled playbooks only)")
    print("=" * 110)
    print(f"{'playbook':<24} {'checked':>8} {'passed':>7} {'no_commit':>10} {'no_cands':>9} {'reject%':>8}")
    print("-" * 110)
    for pb in TARGETS:
        if pb not in ec:
            print(f"{pb:<24} {'(flag OFF — no stats)':>60}")
            continue
        s = ec[pb]
        reject_pct = (s['rejected_no_commit'] + s['rejected_no_candles']) / max(1, s['checked']) * 100
        print(f"{pb:<24} {s['checked']:>8} {s['passed']:>7} {s['rejected_no_commit']:>10} {s['rejected_no_candles']:>9} {reject_pct:>7.1f}%")

    print()
    print("=" * 110)
    print("Per-week E[R] breakdown (target playbooks)")
    print("=" * 110)
    for pb in ['BOS_Scalp_1m', 'Morning_Trap_Reversal']:
        print(f"\n--- {pb} ---")
        print(f"{'week':<10} {'src':<5} {'n':>4} {'E[R]':>8} {'WR':>6} {'totalR':>8}")
        for w in WEEKS:
            b = base[(base['playbook'] == pb) & (base['week'] == w)]
            n = new[(new['playbook'] == pb) & (new['week'] == w)]
            for src, sub in [('base', b), ('new', n)]:
                if len(sub) == 0:
                    print(f"{w:<10} {src:<5} {0:>4} {'nan':>8} {'nan':>6} {0.0:>8.2f}")
                else:
                    print(f"{w:<10} {src:<5} {len(sub):>4} {sub['r_multiple'].mean():>8.3f} {(sub['r_multiple']>0).mean()*100:>5.1f}% {sub['r_multiple'].sum():>8.2f}")

    # Save summary JSON
    summary = {
        'schema_version': 'C3EntryConfirmVerdictV0',
        'slippage_budget_r_per_trade': SLIPPAGE_BUDGET_R,
        'gate_on_playbooks': sorted(gate_on),
        'per_playbook': {},
        'entry_confirm_stats_aggregated': ec,
    }
    for pb in TARGETS:
        summary['per_playbook'][pb] = {
            'role': 'TARGET' if pb in gate_on else 'CONTROL',
            'baseline': per_playbook_stats(base, pb),
            'campaign': per_playbook_stats(new, pb),
        }
    out = CAMPAIGN_ROOT / 'c3_entry_confirm_summary.json'
    with out.open('w') as f:
        json.dump(summary, f, indent=2, default=float)
    print(f"\nSummary written: {out}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
