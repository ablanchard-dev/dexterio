#!/usr/bin/env python3
"""
Mini-lab : une fenêtre courte (ex. 1 semaine) SPY+QQQ, protocole proche de `run_full_playbooks_lab.py`.

Usage (depuis backend/) :
  .venv/bin/python scripts/run_mini_lab_week.py
  .venv/bin/python scripts/run_mini_lab_week.py --start 2025-11-03 --end 2025-11-09 --label 202511_w01

Par défaut : allowlists respectées + bypass quarantaine LSS (aligné audit D27 / labfull_202511).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from backtest.engine import BacktestEngine
from config.settings import settings
from models.backtest import BacktestConfig
from utils.path_resolver import historical_data_path, results_path


def _build_data_paths(symbols: List[str]) -> List[str]:
    return [str(historical_data_path("1m", f"{sym}.parquet")) for sym in symbols]


def _apply_lab_env(respect_allowlists: bool, *, bypass_dynamic_quarantine_lss_only: bool) -> None:
    os.environ["RISK_EVAL_ALLOW_ALL_PLAYBOOKS"] = "false" if respect_allowlists else "true"
    os.environ["RISK_EVAL_RELAX_CAPS"] = "true"
    os.environ["RISK_EVAL_DISABLE_KILL_SWITCH"] = "true"
    if bypass_dynamic_quarantine_lss_only:
        os.environ["RISK_BYPASS_DYNAMIC_QUARANTINE_LSS_ONLY"] = "true"
    else:
        os.environ.pop("RISK_BYPASS_DYNAMIC_QUARANTINE_LSS_ONLY", None)


def _git_sha() -> str:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(backend_dir), text=True)
            .strip()
        )
    except Exception:
        return "unknown"


def _funnel_excerpt(counts: Dict[str, Any], playbook: str) -> Dict[str, Any]:
    return {
        "matches": counts.get("matches_by_playbook", {}).get(playbook, 0),
        "setups_created": counts.get("setups_created_by_playbook", {}).get(playbook, 0),
        "after_risk": counts.get("setups_after_risk_filter_by_playbook", {}).get(playbook, 0),
        "trades": counts.get("trades_opened_by_playbook", {}).get(playbook, 0),
    }


# Ordre multi-week / Wave 2 : funnel standardisé dans chaque `mini_lab_summary_*.json`
MINI_LAB_FUNNEL_PLAYBOOKS: List[str] = [
    "NY_Open_Reversal",
    "News_Fade",
    "Liquidity_Sweep_Scalp",
    "FVG_Fill_Scalp",
    "Session_Open_Scalp",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Mini-lab 1 semaine (SPY+QQQ, AGGRESSIVE)")
    parser.add_argument("--start", type=str, default="2025-11-03", help="YYYY-MM-DD (inclus)")
    parser.add_argument("--end", type=str, default="2025-11-09", help="YYYY-MM-DD (inclus)")
    parser.add_argument(
        "--label",
        type=str,
        default="202511_w01",
        help="Suffixe run_id (fichiers debug_counts_miniweek_<label>)",
    )
    parser.add_argument("--symbols", type=str, default="SPY,QQQ")
    parser.add_argument(
        "--no-respect-allowlists",
        action="store_true",
        help="Allow-all playbooks (défaut: respect allowlists, comme labfull D27)",
    )
    parser.add_argument(
        "--no-bypass-lss-quarantine",
        action="store_true",
        help="Ne pas bypass la quarantaine LSS (défaut: bypass actif)",
    )
    parser.add_argument(
        "--playbooks-yaml",
        type=str,
        default=None,
        help="Chemin absolu/relatif vers un playbooks.yml dérivé (singleton loader remplacé le temps du run)",
    )
    parser.add_argument(
        "--output-parent",
        type=str,
        default=None,
        help="Sous-dossier sous labs/mini_week/<output-parent>/<label>/ (évite d'écraser mini_week/<label> baseline)",
    )
    parser.add_argument(
        "--nf-tp1-rr",
        type=float,
        default=None,
        help="Métadonnée PHASE B (écrite dans mini_lab_summary) — n'affecte pas le moteur",
    )
    args = parser.parse_args()
    respect = not args.no_respect_allowlists
    bypass_lss = not args.no_bypass_lss_quarantine

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    for sym in symbols:
        p = historical_data_path("1m", f"{sym}.parquet")
        if not p.exists():
            print(f"ERROR: missing data {p}", file=sys.stderr)
            return 2

    if args.output_parent:
        out = results_path("labs", "mini_week", args.output_parent, args.label)
        run_id = f"miniweek_{args.output_parent}_{args.label}"
    else:
        out = results_path("labs", "mini_week", args.label)
        run_id = f"miniweek_{args.label}"
    out.mkdir(parents=True, exist_ok=True)

    playbooks_yaml_path: Path | None = None
    pl_mod: Any = None
    prev_loader: Any = None
    if args.playbooks_yaml:
        playbooks_yaml_path = Path(args.playbooks_yaml).expanduser().resolve()
        if not playbooks_yaml_path.is_file():
            print(f"ERROR: playbooks-yaml not found: {playbooks_yaml_path}", file=sys.stderr)
            return 2
        import engines.playbook_loader as pl_mod  # type: ignore[no-redef]

        prev_loader = pl_mod._playbook_loader
        pl_mod._playbook_loader = pl_mod.PlaybookLoader(playbooks_path=playbooks_yaml_path)
    old_env = {k: os.environ.get(k) for k in (
        "RISK_EVAL_ALLOW_ALL_PLAYBOOKS",
        "RISK_EVAL_RELAX_CAPS",
        "RISK_EVAL_DISABLE_KILL_SWITCH",
        "RISK_BYPASS_DYNAMIC_QUARANTINE_LSS_ONLY",
    )}
    try:
        run_started_at_utc = datetime.now(timezone.utc).isoformat()
        _apply_lab_env(respect, bypass_dynamic_quarantine_lss_only=bypass_lss)
        config = BacktestConfig(
            run_name=run_id,
            symbols=symbols,
            data_paths=_build_data_paths(symbols),
            start_date=args.start,
            end_date=args.end,
            initial_capital=settings.INITIAL_CAPITAL,
            trading_mode="AGGRESSIVE",
            trade_types=["DAILY", "SCALP"],
            output_dir=str(out),
            htf_warmup_days=30,
            commission_model="ibkr_fixed",
            enable_reg_fees=True,
            slippage_model="pct",
            slippage_cost_pct=0.0005,
            spread_model="fixed_bps",
            spread_bps=2.0,
        )
        engine = BacktestEngine(config)
        engine.trade_journal.journal_path = str(out / f"trade_journal_{run_id}.parquet")
        os.makedirs(os.path.dirname(engine.trade_journal.journal_path), exist_ok=True)
        engine.trade_journal._save = lambda: None  # type: ignore[attr-defined]

        print(f"[mini_lab] run_id={run_id} {args.start}..{args.end} symbols={symbols}", flush=True)
        print(f"[mini_lab] respect_allowlists={respect} bypass_lss_quarantine={bypass_lss}", flush=True)
        if playbooks_yaml_path is not None:
            print(f"[mini_lab] playbooks_yaml={playbooks_yaml_path}", flush=True)
        if args.nf_tp1_rr is not None:
            print(f"[mini_lab] nf_tp1_rr(meta)={args.nf_tp1_rr}", flush=True)
        engine.load_data()
        result = engine.run()
        counts = getattr(engine, "debug_counts", {}) or {}

        summary: Dict[str, Any] = {
            "protocol": "MINI_LAB_WEEK",
            "runner": "run_mini_lab_week.py",
            "contract_version": "RunSummaryV0",
            "run_started_at_utc": run_started_at_utc,
            "git_sha": _git_sha(),
            "run_id": run_id,
            "start_date": args.start,
            "end_date": args.end,
            "symbols": symbols,
            "respect_allowlists": respect,
            "bypass_lss_quarantine": bypass_lss,
            "output_parent": args.output_parent,
            "playbooks_yaml": str(playbooks_yaml_path) if playbooks_yaml_path else None,
            "nf_tp1_rr_meta": args.nf_tp1_rr,
            "total_trades": result.total_trades,
            "final_capital": str(result.final_capital),
            "playbooks_registered_count": counts.get("playbooks_registered_count"),
            "funnel": {name: _funnel_excerpt(counts, name) for name in MINI_LAB_FUNNEL_PLAYBOOKS},
        }
        summary_path = out / f"mini_lab_summary_{args.label}.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        manifest: Dict[str, Any] = {
            "schema_version": "CampaignManifestV0",
            "contract_version": "RunSummaryV0",
            "run_id": run_id,
            "runner": "run_mini_lab_week.py",
            "argv": sys.argv,
            "cwd": str(Path.cwd().resolve()),
            "git_sha": summary["git_sha"],
            "run_started_at_utc": run_started_at_utc,
            "symbols": symbols,
            "start_date": args.start,
            "end_date": args.end,
            "label": args.label,
            "output_parent": args.output_parent,
            "respect_allowlists": respect,
            "bypass_lss_quarantine": bypass_lss,
        }
        (out / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"[mini_lab] wrote {summary_path}", flush=True)
        print(json.dumps(summary["funnel"], indent=2), flush=True)
        return 0
    finally:
        if pl_mod is not None:
            pl_mod._playbook_loader = prev_loader
        for k, v in old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


if __name__ == "__main__":
    raise SystemExit(main())
