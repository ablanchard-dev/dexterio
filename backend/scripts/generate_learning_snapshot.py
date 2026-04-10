"""
Génère des artefacts de learning auditables depuis un run existant.

Sorties:
- learning_snapshot_{run_id}.json
- playbook_triage_{run_id}.json

Usage:
  python scripts/generate_learning_snapshot.py --run-id labfull_202511 --results-subdir labs/full_playbooks_24m
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from utils.path_resolver import results_path  # noqa: E402


@dataclass
class AxisStats:
    trades: int
    winrate_pct: float
    total_r: float
    avg_r: float
    avg_win_r: float | None
    avg_loss_r: float | None
    expectancy_r: float
    max_drawdown_r: float
    r_p10: float | None
    r_p50: float | None
    r_p90: float | None


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _max_dd_from_r_series(series: List[float]) -> float:
    peak = 0.0
    cur = 0.0
    max_dd = 0.0
    for r in series:
        cur += float(r)
        if cur > peak:
            peak = cur
        dd = peak - cur
        if dd > max_dd:
            max_dd = dd
    return max_dd


def _axis_stats(df: pd.DataFrame) -> AxisStats:
    n = int(len(df))
    if n == 0:
        return AxisStats(0, 0.0, 0.0, 0.0, None, None, 0.0, 0.0, None, None, None)

    r = df["r_multiple"].astype(float)
    wins = df[df["outcome"] == "win"]["r_multiple"].astype(float)
    losses = df[df["outcome"] == "loss"]["r_multiple"].astype(float)
    ordered = df.sort_values("timestamp_entry", kind="mergesort")["r_multiple"].astype(float).tolist()
    total_r = float(r.sum())
    avg_r = float(r.mean())
    winrate = float((df["outcome"] == "win").mean() * 100.0)
    return AxisStats(
        trades=n,
        winrate_pct=winrate,
        total_r=total_r,
        avg_r=avg_r,
        avg_win_r=float(wins.mean()) if len(wins) else None,
        avg_loss_r=float(losses.mean()) if len(losses) else None,
        expectancy_r=avg_r,
        max_drawdown_r=float(_max_dd_from_r_series(ordered)),
        r_p10=float(r.quantile(0.10)) if n >= 2 else None,
        r_p50=float(r.quantile(0.50)) if n >= 2 else None,
        r_p90=float(r.quantile(0.90)) if n >= 2 else None,
    )


def _stats_rows(df: pd.DataFrame, col: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for key, grp in df.groupby(col, dropna=False):
        st = _axis_stats(grp)
        rows.append(
            {
                col: "unknown" if pd.isna(key) else str(key),
                "trades": st.trades,
                "winrate_pct": round(st.winrate_pct, 4),
                "total_r": round(st.total_r, 6),
                "avg_r": round(st.avg_r, 6),
                "avg_win_r": round(st.avg_win_r, 6) if st.avg_win_r is not None else None,
                "avg_loss_r": round(st.avg_loss_r, 6) if st.avg_loss_r is not None else None,
                "expectancy_r": round(st.expectancy_r, 6),
                "max_drawdown_r": round(st.max_drawdown_r, 6),
                "r_p10": round(st.r_p10, 6) if st.r_p10 is not None else None,
                "r_p50": round(st.r_p50, 6) if st.r_p50 is not None else None,
                "r_p90": round(st.r_p90, 6) if st.r_p90 is not None else None,
            }
        )
    rows.sort(key=lambda x: str(x.get(col, "")))
    return rows


def _playbook_triage(playbook_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    triage: List[Dict[str, Any]] = []
    for r in playbook_rows:
        pb = r["playbook"]
        trades = int(r["trades"])
        total_r = _safe_float(r["total_r"])
        avg_r = _safe_float(r["avg_r"])
        wr = _safe_float(r["winrate_pct"])
        mdd = _safe_float(r["max_drawdown_r"])
        regime_note = "edge stable" if avg_r > 0 else "regime sensitivity unclear/negative"

        reasons: List[str] = []
        if trades < 20:
            decision = "REFINE"
            reasons.append("sample_size_too_small")
        elif total_r <= -2.0 or avg_r < -0.03:
            decision = "QUARANTINE"
            reasons.append("negative_edge")
        elif total_r > 0 and avg_r >= 0.03 and wr >= 45.0:
            decision = "KEEP"
            reasons.append("positive_edge_with_volume")
        else:
            decision = "REFINE"
            reasons.append("edge_not_consistent_enough")

        if mdd > 10.0:
            reasons.append("high_drawdown_profile")
            if decision == "KEEP":
                decision = "REFINE"

        triage.append(
            {
                "playbook": pb,
                "decision": decision,
                "metrics": {
                    "trades": trades,
                    "total_r": round(total_r, 6),
                    "avg_r": round(avg_r, 6),
                    "winrate_pct": round(wr, 4),
                    "max_drawdown_r": round(mdd, 6),
                },
                "regime_sensitivity_note": regime_note,
                "reasons": reasons,
            }
        )
    triage.sort(key=lambda x: (x["decision"], x["playbook"]))
    return triage


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate learning snapshot + playbook triage")
    parser.add_argument("--run-id", required=True, help="Run id (ex: labfull_202511)")
    parser.add_argument(
        "--results-subdir",
        default="labs/full_playbooks_24m",
        help="Subdir under results/ where artifacts live",
    )
    args = parser.parse_args()

    out_dir = results_path(args.results_subdir)
    run_id = args.run_id
    trades_path = out_dir / f"trades_{run_id}_AGGRESSIVE_DAILY_SCALP.parquet"
    if not trades_path.exists():
        raise FileNotFoundError(f"Trades file not found: {trades_path}")

    df = pd.read_parquet(trades_path)
    if len(df) == 0:
        raise ValueError(f"No trades in {trades_path}")

    for col in ("playbook", "symbol", "quality", "direction", "session_label", "market_regime", "r_multiple"):
        if col not in df.columns:
            raise ValueError(f"Missing required column '{col}' in {trades_path.name}")

    df["timestamp_entry"] = pd.to_datetime(df["timestamp_entry"], errors="coerce", utc=True)

    # Reuse explicit regime from propagated field, fallback unknown.
    df["regime"] = df["market_regime"].fillna("unknown").astype(str).str.lower()
    df["session_slice"] = df["session_label"].fillna("unknown").astype(str).str.lower()
    df["rr_bucket"] = pd.cut(
        df["entry_rr"].fillna(-1.0).astype(float),
        bins=[-999.0, 1.2, 1.5, 999.0],
        labels=["rr_lt_1.2", "rr_1.2_to_1.5", "rr_gte_1.5"],
        include_lowest=True,
    ).astype(str)

    by_playbook = _stats_rows(df, "playbook")
    by_symbol = _stats_rows(df, "symbol")
    by_regime = _stats_rows(df, "regime")
    by_session = _stats_rows(df, "session_slice")
    by_quality = _stats_rows(df, "quality")
    by_direction = _stats_rows(df, "direction")
    by_rr_bucket = _stats_rows(df, "rr_bucket")

    snapshot = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "source_trades_file": str(trades_path),
        "summary": {
            "total_trades": int(len(df)),
            "total_r": round(float(df["r_multiple"].astype(float).sum()), 6),
            "expectancy_r": round(float(df["r_multiple"].astype(float).mean()), 6),
            "winrate_pct": round(float((df["outcome"] == "win").mean() * 100.0), 4),
            "r_distribution": {
                "min": round(float(df["r_multiple"].min()), 6),
                "p10": round(float(df["r_multiple"].quantile(0.10)), 6),
                "p50": round(float(df["r_multiple"].quantile(0.50)), 6),
                "p90": round(float(df["r_multiple"].quantile(0.90)), 6),
                "max": round(float(df["r_multiple"].max()), 6),
            },
        },
        "where_bot_wins": [r for r in by_playbook if _safe_float(r["avg_r"]) > 0][:10],
        "where_bot_loses": [r for r in by_playbook if _safe_float(r["avg_r"]) <= 0][:10],
        "axes": {
            "playbook": by_playbook,
            "symbol": by_symbol,
            "regime": by_regime,
            "session_slice": by_session,
            "quality": by_quality,
            "direction": by_direction,
            "rr_bucket": by_rr_bucket,
        },
    }

    triage = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "policy_guardrails": {
            "ny_open_reversal_unchanged": True,
            "session_open_scalp_lab_only": True,
            "trend_continuation_quarantined": True,
        },
        "playbooks": _playbook_triage(by_playbook),
    }

    snap_path = out_dir / f"learning_snapshot_{run_id}.json"
    triage_path = out_dir / f"playbook_triage_{run_id}.json"
    snap_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    triage_path.write_text(json.dumps(triage, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[learning] wrote {snap_path}")
    print(f"[learning] wrote {triage_path}")


if __name__ == "__main__":
    main()
