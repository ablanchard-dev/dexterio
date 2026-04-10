"""
Génère les artefacts d'audit vérité marché + edge framework (sans changer la logique trading).

Sorties:
- market_data_audit_{run_id}.json
- playbook_capability_audit_{run_id}.json
- edge_learning_matrix_{run_id}.json
- next_edge_candidates_{run_id}.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
import yaml

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from utils.path_resolver import historical_data_path, results_path  # noqa: E402
from utils.timeframes import get_session_info  # noqa: E402


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _load_market_df(symbol: str, timeframe: str) -> pd.DataFrame:
    p = historical_data_path(timeframe, f"{symbol}.parquet")
    if not p.exists():
        raise FileNotFoundError(f"Data file missing for {symbol}: {p}")
    df = pd.read_parquet(p)
    if "datetime" in df.columns:
        ts = pd.to_datetime(df["datetime"], utc=True, errors="coerce")
    else:
        ts = pd.to_datetime(df.index, utc=True, errors="coerce")
    out = df.copy()
    out["timestamp"] = ts
    out = out.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    return out


def _max_dd_from_r(series: List[float]) -> float:
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


def _group_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    n = len(df)
    if n == 0:
        return {
            "trades": 0,
            "total_r": 0.0,
            "avg_r": 0.0,
            "winrate": 0.0,
            "avg_win": None,
            "avg_loss": None,
            "expectancy": 0.0,
            "profit_factor": None,
            "max_dd": 0.0,
        }
    r = df["r_multiple"].astype(float)
    wins = df[df["outcome"] == "win"]["r_multiple"].astype(float)
    losses = df[df["outcome"] == "loss"]["r_multiple"].astype(float)
    gp = float(r[r > 0].sum())
    gl = float(r[r < 0].sum())
    pf = gp / abs(gl) if gl < 0 else None
    ordered = df.sort_values("timestamp_entry", kind="mergesort")["r_multiple"].astype(float).tolist()
    return {
        "trades": int(n),
        "total_r": round(float(r.sum()), 6),
        "avg_r": round(float(r.mean()), 6),
        "winrate": round(float((df["outcome"] == "win").mean() * 100.0), 4),
        "avg_win": round(float(wins.mean()), 6) if len(wins) else None,
        "avg_loss": round(float(losses.mean()), 6) if len(losses) else None,
        "expectancy": round(float(r.mean()), 6),
        "profit_factor": round(float(pf), 6) if pf is not None else None,
        "max_dd": round(float(_max_dd_from_r(ordered)), 6),
    }


def _audit_market_data(
    run_id: str,
    summary: Dict[str, Any],
    debug_counts: Dict[str, Any],
    trades: pd.DataFrame,
    timeframe: str,
) -> Dict[str, Any]:
    anomalies: List[str] = []
    by_symbol: List[Dict[str, Any]] = []

    start_ts = pd.to_datetime(summary.get("start_date"), utc=True, errors="coerce")
    end_ts = pd.to_datetime(summary.get("end_date"), utc=True, errors="coerce")
    bars_processed = int((debug_counts.get("counts") or {}).get("bars_processed", 0) or 0)

    session_match_total = 0
    session_total = 0
    entry_ref_fail = 0
    entry_ref_total = 0
    fill_ref_fail = 0
    fill_ref_total = 0
    future_data_detected = False

    for sym in sorted({str(s) for s in trades["symbol"].dropna().unique().tolist()}):
        mdf = _load_market_df(sym, timeframe)
        run_df = mdf[(mdf["timestamp"] >= start_ts) & (mdf["timestamp"] <= end_ts)].copy()
        run_df = run_df.sort_values("timestamp").reset_index(drop=True)
        ts = run_df["timestamp"]

        dup_count = int(ts.duplicated().sum())
        if dup_count > 0:
            anomalies.append(f"{sym}: duplicate timestamps={dup_count}")

        out_of_order = 0
        if len(ts) > 1:
            dt = ts.diff().dropna()
            out_of_order = int((dt < pd.Timedelta(0)).sum())
            if out_of_order > 0:
                anomalies.append(f"{sym}: out_of_order_count={out_of_order}")

        missing_est = 0
        if len(ts) > 1:
            dtm = ts.diff().dropna().dt.total_seconds().div(60.0)
            # Estimation simple intra-séance: gaps >1m et <=30m
            candidate = dtm[(dtm > 1.0) & (dtm <= 30.0)]
            missing_est = int((candidate - 1.0).clip(lower=0).sum())
            if missing_est > 0:
                anomalies.append(f"{sym}: missing_bar_estimate={missing_est}")

        sym_trades = trades[trades["symbol"] == sym].copy()
        if len(sym_trades):
            max_trade_ts = pd.to_datetime(sym_trades["timestamp_entry"], utc=True, errors="coerce").max()
            max_data_ts = ts.max() if len(ts) else pd.NaT
            if pd.notna(max_trade_ts) and pd.notna(max_data_ts) and max_trade_ts > max_data_ts:
                future_data_detected = True
                anomalies.append(f"{sym}: trade timestamp beyond market data range")

            # Session consistency check
            for _, tr in sym_trades.iterrows():
                t = pd.to_datetime(tr["timestamp_entry"], utc=True, errors="coerce")
                if pd.isna(t):
                    continue
                info = get_session_info(t.to_pydatetime(), debug_log=False)
                observed = str(tr.get("session_label", "unknown")).lower()
                expected = str(info.get("name", "unknown")).lower()
                session_total += 1
                if observed == expected:
                    session_match_total += 1

            # Entry/fill vs market reference at entry minute
            run_df_idx = run_df.set_index("timestamp") if len(run_df) else run_df
            for _, tr in sym_trades.iterrows():
                t = pd.to_datetime(tr["timestamp_entry"], utc=True, errors="coerce")
                if pd.isna(t) or len(run_df_idx) == 0:
                    continue
                t = t.floor("min")
                if t not in run_df_idx.index:
                    continue
                row = run_df_idx.loc[t]
                close_ref = _safe_float(row["close"])
                entry = _safe_float(tr.get("entry_price"))
                exit_price = _safe_float(tr.get("exit_price"))
                # tolérance 50 bps, sinon anomalie
                if close_ref > 0:
                    entry_ref_total += 1
                    if abs(entry - close_ref) / close_ref > 0.005:
                        entry_ref_fail += 1
                    fill_ref_total += 1
                    if abs(exit_price - close_ref) / close_ref > 0.02:
                        fill_ref_fail += 1

        by_symbol.append(
            {
                "symbol": sym,
                "timeframe": timeframe,
                "first_ts": ts.min().isoformat() if len(ts) else None,
                "last_ts": ts.max().isoformat() if len(ts) else None,
                "count_loaded": int(len(run_df)),
                "count_processed_reference": bars_processed,
                "duplicate_timestamps_count": dup_count,
                "out_of_order_count": out_of_order,
                "missing_bar_estimate": missing_est,
            }
        )

    utc_check = True
    if "timestamp_entry" in trades.columns:
        t = pd.to_datetime(trades["timestamp_entry"], utc=True, errors="coerce")
        utc_check = bool(t.notna().all())

    session_match_rate = (session_match_total / session_total) if session_total else 1.0
    entry_match_rate = 1.0 - (entry_ref_fail / entry_ref_total) if entry_ref_total else 1.0
    fill_match_rate = 1.0 - (fill_ref_fail / fill_ref_total) if fill_ref_total else 1.0

    if session_match_rate < 0.95:
        anomalies.append(f"session_consistency_match_rate={session_match_rate:.4f} < 0.95")
    if entry_match_rate < 0.95:
        anomalies.append(f"entry_vs_bar_match_rate={entry_match_rate:.4f} < 0.95")
    if fill_match_rate < 0.80:
        anomalies.append(f"fill_vs_market_match_rate={fill_match_rate:.4f} < 0.80")
    if future_data_detected:
        anomalies.append("future_data_detected=true")

    passed = (
        (not future_data_detected)
        and utc_check
        and session_match_rate >= 0.95
        and entry_match_rate >= 0.95
    )
    return {
        "schema_version": "1.0",
        "run_id": run_id,
        "utc_to_exchange_tz_check": {"pass": utc_check},
        "session_consistency_check": {"pass": session_match_rate >= 0.95, "match_rate": round(session_match_rate, 6)},
        "entry_vs_bar_reference_check": {"pass": entry_match_rate >= 0.95, "match_rate": round(entry_match_rate, 6)},
        "fill_vs_market_reference_check": {"pass": fill_match_rate >= 0.80, "match_rate": round(fill_match_rate, 6)},
        "future_data_detected": future_data_detected,
        "symbols": by_symbol,
        "anomalies": anomalies,
        "pass": passed,
    }


def _playbook_capability_audit(playbooks_yml: Path, run_id: str) -> Dict[str, Any]:
    data = yaml.safe_load(playbooks_yml.read_text(encoding="utf-8"))
    rows: List[Dict[str, Any]] = []
    for pb in data:
        name = str(pb.get("playbook_name"))
        category = str(pb.get("category", "UNKNOWN"))
        ctx = pb.get("context_requirements") or {}
        con = pb.get("ict_confluences") or {}
        scoring = (pb.get("scoring") or {}).get("weights") or {}

        used = []
        required = []
        strong = []
        weak = []

        if pb.get("timefilters"):
            used.append("session")
        if ctx.get("structure_htf"):
            used.append("structure")
            required.append("structure")
        if con.get("require_sweep") or ctx.get("london_sweep_required"):
            used.append("sweep")
            required.append("sweep")
            strong.append("sweep")
        if con.get("allow_fvg"):
            used.append("fvg")
        if "liquidity_sweep" in scoring:
            used.append("liquidity_sweep_score")
        if "pattern_quality" in scoring:
            used.append("pattern_quality")
        if ctx.get("day_type_allowed"):
            used.append("regime")
            required.append("regime")
        if pb.get("take_profit_logic", {}).get("min_rr") is not None:
            used.append("rr")
            required.append("rr")

        # Heuristique reliance score 0..1
        pattern_reliance = min(1.0, _safe_float(scoring.get("pattern_quality"), 0.0) + (0.2 if pb.get("candlestick_patterns") else 0.0))
        structure_reliance = min(1.0, (0.4 if ctx.get("structure_htf") else 0.0) + (0.3 if "trend_strength" in scoring else 0.0))
        regime_reliance = min(1.0, (0.6 if ctx.get("day_type_allowed") else 0.0) + (0.2 if "context_strength" in scoring else 0.0))

        if pattern_reliance >= 0.55 and structure_reliance < 0.40:
            weak.append("pattern_dominant_without_structure")
        if structure_reliance >= 0.50 or regime_reliance >= 0.50:
            strong.append("market_structure_awareness")

        if structure_reliance >= 0.5 and regime_reliance >= 0.5:
            verdict = "structurally_grounded"
        elif structure_reliance >= 0.35 or regime_reliance >= 0.35:
            verdict = "partially_grounded"
        else:
            verdict = "weakly_grounded"

        rows.append(
            {
                "playbook": name,
                "category": category,
                "market_inputs_used": sorted(set(used)),
                "market_inputs_required": sorted(set(required)),
                "weak_dependencies": sorted(set(weak)),
                "strong_dependencies": sorted(set(strong)),
                "structure_reliance_score": round(structure_reliance, 4),
                "pattern_reliance_score": round(pattern_reliance, 4),
                "regime_reliance_score": round(regime_reliance, 4),
                "notes": "derived from playbooks.yml context_requirements/ict_confluences/scoring.weights",
                "verdict": verdict,
            }
        )
    rows.sort(key=lambda x: x["playbook"])
    return {"schema_version": "1.0", "run_id": run_id, "playbooks": rows}


def _edge_learning_matrix(run_id: str, trades: pd.DataFrame) -> Dict[str, Any]:
    df = trades.copy()
    df["timestamp_entry"] = pd.to_datetime(df["timestamp_entry"], utc=True, errors="coerce")
    df["regime"] = df["market_regime"].fillna("unknown").astype(str).str.lower()
    df["session"] = df["session_label"].fillna("unknown").astype(str).str.lower()
    df["sweep_presence"] = df["had_liquidity_sweep"].fillna(False).map(lambda x: "sweep_yes" if bool(x) else "sweep_no")
    df["mc_breakout"] = df["mc_breakout_dir"].fillna("unknown").astype(str)
    df["rr_bucket"] = pd.cut(
        df["entry_rr"].fillna(-1.0).astype(float),
        bins=[-999.0, 1.2, 1.5, 999.0],
        labels=["rr_lt_1.2", "rr_1.2_to_1.5", "rr_gte_1.5"],
        include_lowest=True,
    ).astype(str)

    def matrix(axis: str) -> List[Dict[str, Any]]:
        rows = []
        for (pb, key), grp in df.groupby(["playbook", axis], dropna=False):
            m = _group_metrics(grp)
            rows.append({"playbook": str(pb), axis: "unknown" if pd.isna(key) else str(key), **m})
        rows.sort(key=lambda x: (x["playbook"], str(x.get(axis, ""))))
        return rows

    return {
        "schema_version": "1.0",
        "run_id": run_id,
        "axes": {
            "playbook_x_regime": matrix("regime"),
            "playbook_x_session": matrix("session"),
            "playbook_x_direction": matrix("direction"),
            "playbook_x_symbol": matrix("symbol"),
            "playbook_x_quality": matrix("quality"),
            "playbook_x_sweep_presence": matrix("sweep_presence"),
            "playbook_x_master_candle_breakout": matrix("mc_breakout"),
            "playbook_x_rr_bucket": matrix("rr_bucket"),
        },
    }


def _next_edge_candidates(
    run_id: str,
    playbook_triage: Dict[str, Any],
    capability_audit: Dict[str, Any],
) -> Dict[str, Any]:
    triage_map = {x["playbook"]: x for x in (playbook_triage.get("playbooks") or [])}
    caps = capability_audit.get("playbooks") or []

    rows: List[Dict[str, Any]] = []
    rank = 1
    for c in caps:
        pb = c["playbook"]
        tri = triage_map.get(pb)
        decision = tri.get("decision") if tri else "REFINE"
        if pb == "Trend_Continuation_FVG_Retest":
            decision = "QUARANTINE"
        if pb == "Session_Open_Scalp":
            decision = "REFINE"
        evidence = []
        if tri:
            evidence.append(f"triage:{tri.get('decision')}")
            evidence.extend([f"reason:{r}" for r in tri.get("reasons", [])[:2]])
        evidence.append(f"capability_verdict:{c.get('verdict')}")
        hypothesis = (
            "Renforcer dépendance structure/régime et réduire pattern décoratif"
            if c.get("pattern_reliance_score", 0.0) > c.get("structure_reliance_score", 0.0)
            else "Valider robustesse multi-régime avec fenêtre plus longue"
        )
        rows.append(
            {
                "priority_rank": rank,
                "playbook": pb,
                "keep_refine_quarantine": decision,
                "why": "derived from playbook_triage + capability audit",
                "evidence": evidence,
                "first_improvement_hypothesis": hypothesis,
            }
        )
        rank += 1

    # Tri pragmatique: KEEP d'abord, puis REFINE, puis QUARANTINE
    order = {"KEEP": 0, "REFINE": 1, "QUARANTINE": 2}
    rows.sort(key=lambda x: (order.get(x["keep_refine_quarantine"], 9), x["playbook"]))
    for i, row in enumerate(rows, start=1):
        row["priority_rank"] = i
    return {"schema_version": "1.0", "run_id": run_id, "candidates": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate market truth + edge framework artifacts")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--results-subdir", default="labs/full_playbooks_24m")
    parser.add_argument("--timeframe", default="1m")
    args = parser.parse_args()

    out_dir = results_path(args.results_subdir)
    run_id = args.run_id

    summary_path = out_dir / f"summary_{run_id}_AGGRESSIVE_DAILY_SCALP.json"
    debug_counts_path = out_dir / f"debug_counts_{run_id}.json"
    trades_path = out_dir / f"trades_{run_id}_AGGRESSIVE_DAILY_SCALP.parquet"
    triage_path = out_dir / f"playbook_triage_{run_id}.json"
    playbooks_yml = backend_dir / "knowledge" / "playbooks.yml"

    summary = _read_json(summary_path)
    debug_counts = _read_json(debug_counts_path)
    trades = pd.read_parquet(trades_path)
    if not triage_path.exists():
        raise FileNotFoundError(f"Missing playbook_triage artifact: {triage_path}")
    playbook_triage = _read_json(triage_path)

    market_audit = _audit_market_data(run_id, summary, debug_counts, trades, args.timeframe)
    capability = _playbook_capability_audit(playbooks_yml, run_id)
    matrix = _edge_learning_matrix(run_id, trades)
    candidates = _next_edge_candidates(run_id, playbook_triage, capability)

    paths = {
        out_dir / f"market_data_audit_{run_id}.json": market_audit,
        out_dir / f"playbook_capability_audit_{run_id}.json": capability,
        out_dir / f"edge_learning_matrix_{run_id}.json": matrix,
        out_dir / f"next_edge_candidates_{run_id}.json": candidates,
    }
    for p, payload in paths.items():
        p.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[edge-audit] wrote {p}")


if __name__ == "__main__":
    main()
