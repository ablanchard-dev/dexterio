"""Bloc C: mesure drift entre un résumé backtest et un résumé paper."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from utils.path_resolver import results_path


def _load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _num(d: Dict[str, Any], *keys: str) -> float:
    for k in keys:
        if k in d and d[k] is not None:
            try:
                return float(d[k])
            except Exception:
                pass
    return 0.0


def main() -> None:
    p = argparse.ArgumentParser(description="Compute backtest vs paper drift")
    p.add_argument("--backtest-summary", required=True, help="Path JSON summary backtest")
    p.add_argument("--paper-summary", required=True, help="Path JSON summary paper")
    args = p.parse_args()

    b = _load(Path(args.backtest_summary))
    q = _load(Path(args.paper_summary))

    b_r = _num(b, "total_pnl_r", "total_R_net", "total_r_net")
    q_r = _num(q, "total_pnl_r", "total_R_net", "total_r_net")
    b_wr = _num(b, "winrate")
    q_wr = _num(q, "winrate")
    b_dd = _num(b, "max_drawdown_r", "max_dd_r")
    q_dd = _num(q, "max_drawdown_r", "max_dd_r")

    r_drift_pct = abs(q_r - b_r) / max(1e-9, abs(b_r) if abs(b_r) > 0 else 1.0)
    wr_drift = abs(q_wr - b_wr)
    dd_delta = q_dd - b_dd

    out = {
        "backtest_summary": str(Path(args.backtest_summary)),
        "paper_summary": str(Path(args.paper_summary)),
        "metrics": {
            "backtest_total_r": b_r,
            "paper_total_r": q_r,
            "r_drift_pct": r_drift_pct,
            "backtest_winrate": b_wr,
            "paper_winrate": q_wr,
            "winrate_drift_abs": wr_drift,
            "backtest_max_dd_r": b_dd,
            "paper_max_dd_r": q_dd,
            "dd_delta_r": dd_delta,
        },
        "gate_checks": {
            "r_drift_pct_le_0_35": r_drift_pct <= 0.35,
            "winrate_drift_le_12pts": wr_drift <= 12.0,
            "paper_dd_not_worse_by_3r": dd_delta <= 3.0,
        },
    }
    out["passed"] = all(out["gate_checks"].values())
    out_file = results_path("perf_backtest_paper_drift.json")
    out_file.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"[perf] drift report: {out_file}")


if __name__ == "__main__":
    main()

