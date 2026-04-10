"""One-shot lab window with explicit job_<uuid> run_name (stdout prints job id)."""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from config.settings import settings
from models.backtest import BacktestConfig
from backtest.engine import BacktestEngine
from utils.path_resolver import historical_data_path, results_path


def main() -> int:
    job = uuid.uuid4().hex[:12]
    run_name = f"job_{job}"

    os.environ["RISK_EVAL_ALLOW_ALL_PLAYBOOKS"] = "false"
    os.environ["RISK_EVAL_RELAX_CAPS"] = "true"
    os.environ["RISK_EVAL_DISABLE_KILL_SWITCH"] = "true"
    os.environ["RISK_BYPASS_DYNAMIC_QUARANTINE_LSS_ONLY"] = "true"

    symbols = ["SPY", "QQQ"]
    data_paths = []
    for sym in symbols:
        p = historical_data_path("1m", f"{sym}.parquet")
        if not p.exists():
            print(f"MISSING_DATA {p}", file=sys.stderr)
            return 1
        data_paths.append(str(p))

    out = results_path("labs", "full_playbooks_24m")
    out.mkdir(parents=True, exist_ok=True)

    config = BacktestConfig(
        run_name=run_name,
        symbols=symbols,
        data_paths=data_paths,
        start_date="2025-11-01",
        end_date="2025-11-30",
        initial_capital=settings.INITIAL_CAPITAL,
        trading_mode="AGGRESSIVE",
        trade_types=["DAILY", "SCALP"],
        output_dir=str(out),
    )
    engine = BacktestEngine(config)
    # Évite lock / chemin global Windows sur trade_journal.parquet (même pattern que run_full_playbooks_lab).
    jpath = out / f"trade_journal_{run_name}.parquet"
    jpath.parent.mkdir(parents=True, exist_ok=True)
    engine.trade_journal.journal_path = str(jpath)
    engine.trade_journal._save = lambda: None  # type: ignore[attr-defined]

    engine.load_data()
    result = engine.run()
    print(f"JOB_ID={job}")
    print(f"RUN_NAME={run_name}")
    print(f"total_trades={result.total_trades}")
    print(f"debug_counts={out / f'debug_counts_{run_name}.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
