"""
Shadow probe script — run TradingPipeline with use_v2_shadow=True and print a
compact summary of what legacy vs V2 produced.

Usage:
    cd backend
    .venv/bin/python scripts/run_shadow_probe.py [--symbols SPY,QQQ] [--label probe_YYYYMMDD]

Output:
    - Prints a compact per-symbol summary to stdout
    - Writes shadow artifacts under results/debug/shadow_compare/ (gitignored)
    - Does NOT modify any trading state or backtest artifacts

Constraints:
    - Activates use_v2_shadow=True ONLY — legacy decision is never changed
    - Non-blocking: any V2/shadow error is reported but pipeline continues
    - Safe to run at any time (paper/live unaffected)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.WARNING)

from engines.pipeline import TradingPipeline  # noqa: E402
from config.settings import settings  # noqa: E402


def _compact_setup(s: dict) -> str:
    return (
        f"quality={s.get('quality')} score={s.get('final_score',0):.3f} "
        f"dir={s.get('direction')} pb={s.get('playbook_name','')} "
        f"ict={s.get('ict_score',0):.2f} pat={s.get('pattern_score',0):.2f} "
        f"pbscore={s.get('playbook_score',0):.2f}"
    )


def run_probe(symbols: list[str], label: str) -> int:
    print(f"[probe] time_utc={datetime.now(timezone.utc).isoformat()}")
    print(f"[probe] trading_mode={settings.TRADING_MODE} symbols={symbols} label={label}")
    print()

    pipeline = TradingPipeline()
    results = pipeline.run_full_analysis(
        symbols=symbols,
        use_v2_shadow=True,
        v2_shadow_label=label,
    )

    # Find written artifacts
    shadow_dir = Path("results/debug/shadow_compare")
    artifacts = sorted(shadow_dir.glob(f"shadow_compare_*_{label}.json")) if shadow_dir.exists() else []

    for sym in symbols:
        art = next((a for a in artifacts if f"_{sym}_" in a.name), None)
        if art is None:
            print(f"[{sym}] NO artifact written")
            continue

        d = json.loads(art.read_text(encoding="utf-8"))
        inp = next(
            (json.loads(Path(a).read_text()) for a in sorted(shadow_dir.glob(f"shadow_input_snapshot_{sym}_*_{label}.json"))),
            {},
        ).get("input", {})

        ms = inp.get("market_state", {})
        counts = d.get("counts", {})
        leg = d.get("legacy", {})
        v2 = d.get("v2_shadow", {})
        diff = d.get("diff", {})

        print(f"[{sym}] price={d.get('current_price'):.2f} session={ms.get('current_session','?')} bias={ms.get('bias','?')}")
        print(f"  counts: ict={counts.get('ict_patterns')} candle={counts.get('candlestick_patterns_legacy')} liq={counts.get('liquidity_levels')} pb_matches={counts.get('legacy_playbook_matches')}")

        leg_raw = leg.get("raw")
        if leg_raw:
            print(f"  legacy.raw  : {_compact_setup(leg_raw)}")
        else:
            print(f"  legacy.raw  : None")
        print(f"  legacy.final: {counts.get('legacy_final_setups',0)} setup(s)")

        v2_err = v2.get("error")
        if v2_err:
            print(f"  v2.error    : {v2_err[:120]}")
        v2_raw = v2.get("raw_setups", [])
        v2_final = v2.get("final_setups", [])
        print(f"  v2.raw  ({len(v2_raw)}): " + (", ".join(_compact_setup(s) for s in v2_raw[:3]) or "—"))
        print(f"  v2.final({len(v2_final)}): " + (", ".join(_compact_setup(s) for s in v2_final[:3]) or "—"))

        reasons = diff.get("divergence_reasons", [])
        print(f"  divergence_reasons: {reasons if reasons else '[]'}")
        print(f"  artifact: {art.name}")
        print()

    # Legacy final setups
    total_legacy = sum(len(s) for s in results.values())
    print(f"[probe] legacy_final_total={total_legacy}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default=",".join(settings.SYMBOLS))
    ap.add_argument("--label", default=f"probe_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}")
    args = ap.parse_args()
    syms = [s.strip() for s in args.symbols.split(",") if s.strip()]
    return run_probe(syms, args.label)


if __name__ == "__main__":
    raise SystemExit(main())
