"""Gate 3: runner labo full-playbooks sur 24 mois (rolling mensuel)."""
from __future__ import annotations

import argparse
import gc
import json
import os
import subprocess
import sys
from calendar import monthrange
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from backtest.engine import BacktestEngine
from config.settings import settings
from models.backtest import BacktestConfig
from utils.path_resolver import historical_data_path, results_path
import pandas as pd


def _month_windows(end_utc: datetime, months: int) -> List[Dict[str, str]]:
    cur_y, cur_m = end_utc.year, end_utc.month
    out: List[Dict[str, str]] = []
    for _ in range(months):
        last_day = monthrange(cur_y, cur_m)[1]
        start = f"{cur_y:04d}-{cur_m:02d}-01"
        end = f"{cur_y:04d}-{cur_m:02d}-{last_day:02d}"
        out.append({"start": start, "end": end, "label": f"{cur_y:04d}{cur_m:02d}"})
        cur_m -= 1
        if cur_m == 0:
            cur_m = 12
            cur_y -= 1
    out.reverse()
    return out


def _build_data_paths(symbols: List[str]) -> List[str]:
    return [str(historical_data_path("1m", f"{sym}.parquet")) for sym in symbols]


def _infer_anchor_end_from_data(symbols: List[str]) -> datetime:
    latest: List[datetime] = []
    for sym in symbols:
        p = Path(historical_data_path("1m", f"{sym}.parquet"))
        if not p.exists():
            continue
        df = pd.read_parquet(p)
        if "datetime" in df.columns:
            t = pd.to_datetime(df["datetime"], utc=True, errors="coerce")
            if len(t):
                latest.append(t.max().to_pydatetime())
        elif isinstance(df.index, pd.DatetimeIndex) and len(df.index):
            idx = pd.to_datetime(df.index, utc=True, errors="coerce")
            latest.append(idx.max().to_pydatetime())
    if not latest:
        return datetime.now(timezone.utc)
    return max(latest)


def _apply_lab_env(
    respect_allowlists: bool,
    *,
    bypass_dynamic_quarantine_lss_only: bool = False,
) -> None:
    os.environ["RISK_EVAL_ALLOW_ALL_PLAYBOOKS"] = "false" if respect_allowlists else "true"
    os.environ["RISK_EVAL_RELAX_CAPS"] = "true"
    os.environ["RISK_EVAL_DISABLE_KILL_SWITCH"] = "true"
    if bypass_dynamic_quarantine_lss_only:
        os.environ["RISK_BYPASS_DYNAMIC_QUARANTINE_LSS_ONLY"] = "true"


def _run_window(window: Dict[str, str], output_dir: Path, symbols: List[str]) -> Dict[str, str]:
    run_name = f"labfull_{window['label']}"
    config = BacktestConfig(
        run_name=run_name,
        symbols=symbols,
        data_paths=_build_data_paths(symbols),
        start_date=window["start"],
        end_date=window["end"],
        initial_capital=settings.INITIAL_CAPITAL,
        trading_mode="AGGRESSIVE",
        trade_types=["DAILY", "SCALP"],
        output_dir=str(output_dir),
    )
    engine = BacktestEngine(config)
    # Evite les conflits/locks sur le journal global pendant les runs labo.
    engine.trade_journal.journal_path = str(output_dir / f"trade_journal_{run_name}.parquet")
    os.makedirs(os.path.dirname(engine.trade_journal.journal_path), exist_ok=True)
    # Perf labo: éviter l'écriture parquet à chaque trade fermé.
    engine.trade_journal._save = lambda: None  # type: ignore[attr-defined]
    engine.load_data()
    result = engine.run()
    meta = {
        "run_name": run_name,
        "start": window["start"],
        "end": window["end"],
        "total_trades": str(result.total_trades),
        "final_capital": str(result.final_capital),
        "playbook_stats_file": str(output_dir / f"playbook_stats_{run_name}.json"),
        "summary_file": str(output_dir / f"summary_{run_name}_{config.trading_mode}_DAILY_SCALP.json"),
    }
    meta_path = output_dir / f"lab_window_meta_{run_name}.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def _run_window_subprocess(
    window: Dict[str, str],
    output_dir: Path,
    symbols: List[str],
    respect_allowlists: bool,
    bypass_lss_quarantine: bool,
    script_path: Path,
) -> Dict[str, str]:
    """Un processus Python par fenêtre : évite fuites d'état (singletons, buffers debug)."""
    cmd: List[str] = [
        sys.executable,
        str(script_path),
        "--child-window",
        "--window-start",
        window["start"],
        "--window-end",
        window["end"],
        "--window-label",
        window["label"],
        "--output-dir",
        str(output_dir),
        "--symbols",
        ",".join(symbols),
    ]
    if respect_allowlists:
        cmd.append("--respect-allowlists")
    if bypass_lss_quarantine:
        cmd.append("--risk-bypass-dynamic-quarantine-lss-only")
    proc = subprocess.run(
        cmd,
        cwd=str(backend_dir),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        err = (proc.stderr or "") + (proc.stdout or "")
        raise RuntimeError(
            f"Fenêtre {window['label']} échouée (code {proc.returncode}): {err[-4000:]}"
        )
    run_name = f"labfull_{window['label']}"
    meta_path = output_dir / f"lab_window_meta_{run_name}.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"Métadonnées fenêtre absentes: {meta_path}")
    return json.loads(meta_path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run full-playbooks lab (rolling monthly)")
    parser.add_argument("--months", type=int, default=24, help="Nombre de fenêtres mensuelles")
    parser.add_argument("--top-n", type=int, default=8, help="Top-N cible pour Wave 1 (métadonnée)")
    parser.add_argument(
        "--anchor-end",
        type=str,
        default="data_max",
        help="Date d'ancrage YYYY-MM-DD ou 'data_max' (défaut)",
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default=",".join(settings.SYMBOLS),
        help="Liste symboles séparés par virgule (ex: SPY,QQQ)",
    )
    parser.add_argument(
        "--respect-allowlists",
        action="store_true",
        help="Respecte denylist/quarantaine (n'active pas allow-all playbooks)",
    )
    parser.add_argument(
        "--risk-bypass-dynamic-quarantine-lss-only",
        action="store_true",
        help="P2 lab: retire Liquidity_Sweep_Scalp de la quarantaine YAML uniquement (équiv. env RISK_BYPASS_DYNAMIC_QUARANTINE_LSS_ONLY)",
    )
    parser.add_argument(
        "--isolate-windows",
        action="store_true",
        help="Force un sous-processus par fenêtre (défaut: auto si --months > 1)",
    )
    parser.add_argument(
        "--no-isolate-windows",
        action="store_true",
        help="Désactive l'isolation: tout dans le même processus (plus rapide, risque de blocage)",
    )
    parser.add_argument(
        "--child-window",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--window-start", type=str, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--window-end", type=str, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--window-label", type=str, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--output-dir", type=str, default=None, help=argparse.SUPPRESS)
    args = parser.parse_args()
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    script_path = Path(__file__).resolve()

    if args.child_window:
        if not args.window_start or not args.window_end or not args.window_label or not args.output_dir:
            parser.error("--child-window requiert --window-start, --window-end, --window-label, --output-dir")
        _apply_lab_env(
            args.respect_allowlists,
            bypass_dynamic_quarantine_lss_only=args.risk_bypass_dynamic_quarantine_lss_only,
        )
        w = {"start": args.window_start, "end": args.window_end, "label": args.window_label}
        _run_window(w, Path(args.output_dir), symbols)
        print(f"[gate3] child OK {w['label']}", flush=True)
        return

    if args.no_isolate_windows:
        isolate = False
    elif args.isolate_windows:
        isolate = True
    else:
        isolate = max(1, args.months) > 1

    out = results_path("labs", "full_playbooks_24m")
    out.mkdir(parents=True, exist_ok=True)

    old_env = {
        "RISK_EVAL_ALLOW_ALL_PLAYBOOKS": os.environ.get("RISK_EVAL_ALLOW_ALL_PLAYBOOKS"),
        "RISK_EVAL_RELAX_CAPS": os.environ.get("RISK_EVAL_RELAX_CAPS"),
        "RISK_EVAL_DISABLE_KILL_SWITCH": os.environ.get("RISK_EVAL_DISABLE_KILL_SWITCH"),
        "RISK_BYPASS_DYNAMIC_QUARANTINE_LSS_ONLY": os.environ.get(
            "RISK_BYPASS_DYNAMIC_QUARANTINE_LSS_ONLY"
        ),
    }
    _apply_lab_env(
        args.respect_allowlists,
        bypass_dynamic_quarantine_lss_only=args.risk_bypass_dynamic_quarantine_lss_only,
    )

    if args.anchor_end == "data_max":
        anchor_end = _infer_anchor_end_from_data(symbols)
    else:
        anchor_end = datetime.strptime(args.anchor_end, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    windows = _month_windows(anchor_end, max(1, args.months))
    run_index: List[Dict[str, str]] = []
    nwin = len(windows)
    try:
        for i, w in enumerate(windows, start=1):
            mode = "subprocess" if isolate else "in-process"
            print(f"[gate3] fenêtre {i}/{nwin} {w['label']} ({mode})", flush=True)
            if isolate:
                run_index.append(
                    _run_window_subprocess(
                        w,
                        out,
                        symbols,
                        args.respect_allowlists,
                        args.risk_bypass_dynamic_quarantine_lss_only,
                        script_path,
                    )
                )
            else:
                run_index.append(_run_window(w, out, symbols))
                gc.collect()
    finally:
        for k, v in old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    payload = {
        "lab": "full_playbooks_24m",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "months": args.months,
        "selection_policy": "aggressive",
        "wave1_top_n": args.top_n,
        "isolate_windows": isolate,
        "windows": run_index,
    }
    index_file = out / "lab_windows_index.json"
    with index_file.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"[gate3] index écrit: {index_file}")


if __name__ == "__main__":
    main()

