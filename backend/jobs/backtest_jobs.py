"""
PHASE C - Backtest Jobs System
File-based job storage with async execution
"""

import json
import uuid
import logging
import os
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Literal
from concurrent.futures import ProcessPoolExecutor
from pydantic import BaseModel

from utils.path_resolver import results_path

logger = logging.getLogger(__name__)

# Allow simple tokens only (no slashes) for on-disk campaign layout names.
_LAYOUT_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,120}$")


def _require_safe_layout_token(name: str, value: str) -> None:
    if not value or not _LAYOUT_TOKEN_RE.match(value):
        raise ValueError(
            f"Invalid {name}: {value!r} (allowed: [A-Za-z0-9][A-Za-z0-9_.-]{{0,120}})"
        )


# Job executor (singleton)
_executor = None
_executor_shutdown = False

def get_executor():
    """Get or create the global executor"""
    global _executor, _executor_shutdown
    if _executor is None or _executor_shutdown:
        # Si shutdown, créer un nouvel executor
        if _executor is not None and _executor_shutdown:
            logger.warning("Creating new executor after shutdown")
        max_w = max(1, int(os.environ.get("BACKTEST_MAX_WORKERS", "2")))
        _executor = ProcessPoolExecutor(max_workers=max_w)
        _executor_shutdown = False
    return _executor


def shutdown_executor():
    """Shutdown the executor properly (P0 Fix #1)"""
    global _executor, _executor_shutdown
    if _executor is not None and not _executor_shutdown:
        try:
            logger.info("Shutting down ProcessPoolExecutor...")
            _executor.shutdown(wait=True, cancel_futures=True)
            logger.info("ProcessPoolExecutor shutdown OK")
        except Exception as e:
            logger.error(f"Error shutting down executor: {e}")
        finally:
            _executor = None
            _executor_shutdown = True


class BacktestJobRequest(BaseModel):
    """Request to run a backtest"""
    protocol: Literal["JOB", "MINI_LAB_WEEK", "MINI_LAB_WALK_FORWARD"] = "JOB"
    symbols: List[str]
    start_date: str  # YYYY-MM-DD
    end_date: str
    trading_mode: str  # SAFE or AGGRESSIVE
    trade_types: List[str]  # DAILY, SCALP
    htf_warmup_days: int = 40
    initial_capital: float = 50000.0

    # Optional (protocol=MINI_LAB_WEEK only): allow writing the run under the canonical ladder layout.
    # Layout: backend/results/labs/mini_week/<output_parent>/<label>/
    output_parent: Optional[str] = None
    label: Optional[str] = None

    # Optional (protocol=MINI_LAB_WALK_FORWARD only): labels are auto-generated as
    #   {label_prefix}_s{0|1}_test (2-split walk-forward OOS).
    label_prefix: Optional[str] = None
    
    # Costs config (PHASE B)
    commission_model: str = "ibkr_fixed"
    enable_reg_fees: bool = True
    slippage_model: str = "pct"
    slippage_cost_pct: float = 0.0005
    spread_model: str = "fixed_bps"
    spread_bps: float = 2.0


class BacktestJobStatus(BaseModel):
    """Job status response"""
    job_id: str
    status: str  # queued, running, done, failed
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    artifact_paths: Optional[Dict[str, str]] = None
    metrics: Optional[Dict[str, Any]] = None


def get_job_dir(job_id: str) -> Path:
    """Get job directory path"""
    job_dir = results_path("jobs") / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    return job_dir


def get_job_file(job_id: str) -> Path:
    """Get job.json path"""
    return get_job_dir(job_id) / "job.json"


def get_job_log(job_id: str) -> Path:
    """Get job.log path"""
    return get_job_dir(job_id) / "job.log"


def create_job(request: BacktestJobRequest) -> str:
    """
    Create a new job (queued state)
    
    Returns:
        job_id
    """
    job_id = str(uuid.uuid4())[:8]  # Short ID
    
    job_data = {
        "job_id": job_id,
        "status": "queued",
        "created_at": datetime.now().isoformat(),
        "started_at": None,
        "completed_at": None,
        "error": None,
        "config": request.dict(),
        "artifact_paths": {},
        "metrics": {}
    }
    
    # Write job.json
    job_file = get_job_file(job_id)
    with open(job_file, 'w', encoding='utf-8') as f:
        json.dump(job_data, f, indent=2, ensure_ascii=False)
    
    # Create empty log
    log_file = get_job_log(job_id)
    log_file.touch()
    
    logger.info(f"Created job {job_id}")
    
    return job_id


def update_job_status(
    job_id: str,
    status: str,
    error: Optional[str] = None,
    artifact_paths: Optional[Dict[str, str]] = None,
    metrics: Optional[Dict[str, Any]] = None
):
    """Update job status"""
    job_file = get_job_file(job_id)
    
    with open(job_file, 'r', encoding='utf-8') as f:
        job_data = json.load(f)
    
    job_data["status"] = status
    
    if status == "running" and not job_data["started_at"]:
        job_data["started_at"] = datetime.now().isoformat()
    
    if status in ["done", "failed"]:
        job_data["completed_at"] = datetime.now().isoformat()
    
    if error:
        job_data["error"] = error
    
    if artifact_paths:
        job_data["artifact_paths"] = artifact_paths
    
    if metrics:
        job_data["metrics"] = metrics
    
    with open(job_file, 'w', encoding='utf-8') as f:
        json.dump(job_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Job {job_id} status: {status}")


def get_job_status(job_id: str) -> Optional[BacktestJobStatus]:
    """Get job status"""
    job_file = get_job_file(job_id)
    
    if not job_file.exists():
        return None
    
    try:
        with open(job_file, 'r', encoding='utf-8') as f:
            job_data = json.load(f)
        return BacktestJobStatus(**job_data)
    except Exception as e:
        logger.error(f"Failed to read job status for {job_id}: {e}")
        return None


def load_jobs_from_disk() -> Dict[str, Dict[str, Any]]:
    """
    Scan disk for all jobs and return as dict (job_id -> job_data).
    This ensures jobs persist across server restarts.
    """
    jobs_dir = results_path("jobs")
    
    if not jobs_dir.exists():
        return {}
    
    jobs_dict = {}
    for job_dir in jobs_dir.iterdir():
        if job_dir.is_dir():
            job_file = job_dir / "job.json"
            if job_file.exists():
                try:
                    with open(job_file, 'r', encoding='utf-8') as f:
                        job_data = json.load(f)
                    job_id = job_data.get("job_id") or job_dir.name
                    jobs_dict[job_id] = job_data
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"Failed to load job from {job_file}: {e}")
                    continue
    
    return jobs_dict


def list_jobs(limit: int = 20) -> List[BacktestJobStatus]:
    """
    List recent jobs (persisted from disk).
    Uses load_jobs_from_disk() to ensure jobs persist across server restarts.
    """
    jobs_dict = load_jobs_from_disk()
    
    if not jobs_dict:
        return []
    
    # Convert to list with metadata for sorting
    jobs_list = []
    jobs_dir = results_path("jobs")
    
    for job_id, job_data in jobs_dict.items():
        job_file = get_job_file(job_id)
        if job_file.exists():
            # Use file mtime as fallback if created_at is missing
            try:
                mtime = job_file.stat().st_mtime
            except OSError:
                mtime = 0
            created_at = job_data.get("created_at", "")
            jobs_list.append((job_data, mtime, created_at))
    
    # Sort by created_at (descending), fallback to mtime
    jobs_list.sort(key=lambda x: (x[2] if x[2] else "", x[1]), reverse=True)
    
    # Convert to BacktestJobStatus and limit
    jobs = []
    for job_data, _, _ in jobs_list[:limit]:
        try:
            jobs.append(BacktestJobStatus(**job_data))
        except Exception as e:
            logger.warning(f"Failed to parse job data: {e}")
            continue
    
    return jobs


def run_backtest_worker(job_id: str, request_dict: dict):
    """
    Worker function to run backtest (executed in separate process)
    
    Args:
        job_id: Job ID
        request_dict: BacktestJobRequest as dict
    """
    import sys
    import traceback
    import subprocess
    from pathlib import Path
    
    # Setup paths
    backend_dir = Path(__file__).parent.parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    
    from models.backtest import BacktestConfig
    from backtest.engine import BacktestEngine
    from utils.backtest_data_coverage import check_backtest_data_coverage
    from utils.lab_environment_snapshot import build_lab_environment_for_manifest
    from utils.mini_lab_trade_metrics_parquet import summarize_trades_parquet
    from utils.path_resolver import historical_data_path, results_path
    
    log_file = get_job_log(job_id)
    
    def log(msg):
        try:
            with open(log_file, 'a', encoding='utf-8', errors='replace') as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] {msg}\n")
                f.flush()  # Force write to disk
        except Exception as log_err:
            # Fallback: try to log to stderr if file write fails
            import sys
            print(f"[LOG ERROR] Failed to write log: {log_err}", file=sys.stderr)
            print(f"[LOG] {msg}", file=sys.stderr)

    _risk_env_keys = [
        "RISK_EVAL_ALLOW_ALL_PLAYBOOKS",
        "RISK_EVAL_RELAX_CAPS",
        "RISK_EVAL_DISABLE_KILL_SWITCH",
        "RISK_BYPASS_DYNAMIC_QUARANTINE_LSS_ONLY",
    ]
    _old_env: Optional[Dict[str, Optional[str]]] = None
    
    try:
        run_started_at_utc = datetime.now(timezone.utc).isoformat()
        log("Starting backtest worker...")
        update_job_status(job_id, "running")
        
        # Build config
        request = BacktestJobRequest(**request_dict)

        protocol = request.protocol

        # Protocol env: apply per-run, then restore (ProcessPoolExecutor workers can be reused)
        _old_env = {k: os.environ.get(k) for k in _risk_env_keys}
        if protocol == "MINI_LAB_WEEK":
            # Align with scripts/run_mini_lab_week.py defaults (respect allowlists + relax caps + disable kill-switch)
            os.environ["RISK_EVAL_ALLOW_ALL_PLAYBOOKS"] = "false"
            os.environ["RISK_EVAL_RELAX_CAPS"] = "true"
            os.environ["RISK_EVAL_DISABLE_KILL_SWITCH"] = "true"
            os.environ["RISK_BYPASS_DYNAMIC_QUARANTINE_LSS_ONLY"] = "true"

        effective_trading_mode = request.trading_mode
        effective_trade_types = list(request.trade_types)
        effective_htf_warmup_days = int(request.htf_warmup_days)
        protocol_overrides: Dict[str, Any] = {}

        if protocol == "MINI_LAB_WEEK":
            # Mini-lab week is an AGGRESSIVE protocol (same as scripts/run_mini_lab_week.py).
            if effective_trading_mode != "AGGRESSIVE":
                raise ValueError("protocol=MINI_LAB_WEEK requires trading_mode=AGGRESSIVE")

            # Mini-lab week runs both DAILY + SCALP.
            if sorted({x.strip().upper() for x in effective_trade_types}) != ["DAILY", "SCALP"]:
                raise ValueError("protocol=MINI_LAB_WEEK requires trade_types=['DAILY','SCALP']")

            # Mini-lab default warmup in manifests is 30 days.
            effective_htf_warmup_days = 30
            protocol_overrides["htf_warmup_days"] = 30
        
        # Log full config (JSON compact)
        import json
        config_dict = request.dict()
        log(f"Config received: {json.dumps(config_dict, separators=(',', ':'))}")

        log(f"Protocol: {protocol}")
        
        log(f"Symbols: {request.symbols}")
        log(f"Period: {request.start_date} -> {request.end_date}")
        log(f"Mode: {effective_trading_mode}")
        log(f"HTF Warmup: {effective_htf_warmup_days} days")
        log(f"Trade Types: {effective_trade_types}")
        
        # Write job_config.json
        job_dir = get_job_dir(job_id)
        config_file = job_dir / "job_config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)
        log(f"Config saved to: {config_file}")
        
        # Build data paths
        data_paths = []
        for symbol in request.symbols:
            path = historical_data_path("1m", f"{symbol}.parquet")
            if not path.exists():
                raise FileNotFoundError(f"Data file not found: {path}")
            data_paths.append(str(path))
            log(f"Data: {path}")

        # Ladder-compatible: compute data coverage contract (does not block the run)
        dc_report = check_backtest_data_coverage(
            data_paths=list(data_paths),
            symbols=list(request.symbols),
            start_date=request.start_date,
            end_date=request.end_date,
            htf_warmup_days=int(effective_htf_warmup_days),
            max_gap_warn_minutes=None,
            ignore_warmup_check=False,
        )

        def _git_sha() -> str:
            try:
                return (
                    subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(backend_dir), text=True)
                    .strip()
                )
            except Exception:
                return "unknown"

        git_sha = _git_sha()

        # Output layout:
        # - protocol=JOB: always stays under results/jobs/<job_id>/ (current UI contract).
        # - protocol=MINI_LAB_WEEK: may optionally also write ladder artifacts under
        #   results/labs/mini_week/<output_parent>/<label>/ (canonical mini-lab layout).
        mini_week_output_parent = None
        mini_week_label = None
        mini_week_run_dir: Optional[Path] = None

        engine_output_dir = results_path()

        # Create config
        run_name = f"job_{job_id}"
        if protocol == "MINI_LAB_WEEK" and request.output_parent and request.label:
            _require_safe_layout_token("output_parent", request.output_parent)
            _require_safe_layout_token("label", request.label)
            mini_week_output_parent = request.output_parent
            mini_week_label = request.label
            mini_week_run_dir = results_path("labs", "mini_week", mini_week_output_parent, mini_week_label)
            mini_week_run_dir.mkdir(parents=True, exist_ok=True)
            engine_output_dir = mini_week_run_dir
            run_name = f"miniweek_{mini_week_output_parent}_{mini_week_label}"

        config = BacktestConfig(
            run_name=run_name,
            symbols=request.symbols,
            data_paths=data_paths,
            start_date=request.start_date,
            end_date=request.end_date,
            trading_mode=effective_trading_mode,
            trade_types=effective_trade_types,
            htf_warmup_days=effective_htf_warmup_days,
            initial_capital=request.initial_capital,
            commission_model=request.commission_model,
            enable_reg_fees=request.enable_reg_fees,
            slippage_model=request.slippage_model,
            slippage_cost_pct=request.slippage_cost_pct,
            spread_model=request.spread_model,
            spread_bps=request.spread_bps,
            output_dir=str(engine_output_dir)  # absolute output dir
        )
        
        log("Running backtest...")
        engine = BacktestEngine(config)

        if protocol == "MINI_LAB_WEEK":
            # Align with mini-lab: avoid mutating the global trade journal outside this job directory.
            try:
                engine.trade_journal.journal_path = str(job_dir / f"trade_journal_{run_name}.parquet")
                os.makedirs(os.path.dirname(engine.trade_journal.journal_path), exist_ok=True)
                engine.trade_journal._save = lambda: None  # type: ignore[attr-defined]
            except Exception:
                pass  # instrumentation only; non-blocking
        engine.load_data()  # Load data first to populate debug_counts
        
        # DIAGNOSTIC: Log data shape after load
        if engine.combined_data is not None and len(engine.combined_data) > 0:
            log(f"Data loaded: {len(engine.combined_data)} bars")
            log(f"  Date range: {engine.combined_data['datetime'].min()} to {engine.combined_data['datetime'].max()}")
        else:
            log("⚠️  WARNING: No data loaded or empty after slicing!")
        
        result = engine.run()
        
        log(f"Backtest complete: {result.total_trades} trades")
        
        # Move artifacts to job directory
        job_dir = get_job_dir(job_id)
        
        # Build expected artifact names
        mode = effective_trading_mode
        types = "_".join(effective_trade_types)
        
        summary_name = f"summary_{run_name}_{mode}_{types}.json"
        trades_name = f"trades_{run_name}_{mode}_{types}.parquet"
        equity_name = f"equity_{run_name}_{mode}_{types}.parquet"
        
        # Copy artifacts
        artifact_paths = {}
        
        artifact_root = Path(config.output_dir)

        summary_src = artifact_root / summary_name
        if summary_src.exists():
            summary_dst = job_dir / "summary.json"
            summary_dst.write_bytes(summary_src.read_bytes())
            artifact_paths["summary"] = "summary.json"
            log(f"Summary: {summary_dst}")
        
        trades_src = artifact_root / trades_name
        if trades_src.exists():
            trades_dst = job_dir / "trades.parquet"
            trades_dst.write_bytes(trades_src.read_bytes())
            artifact_paths["trades"] = "trades.parquet"
            log(f"Trades: {trades_dst}")
        
        equity_src = artifact_root / equity_name
        if equity_src.exists():
            equity_dst = job_dir / "equity.parquet"
            equity_dst.write_bytes(equity_src.read_bytes())
            artifact_paths["equity"] = "equity.parquet"
            log(f"Equity: {equity_dst}")
        
        # DIAGNOSTIC: Copy debug_counts.json to job directory
        debug_counts_name = f"debug_counts_{run_name}.json"
        debug_counts_src = artifact_root / debug_counts_name
        if debug_counts_src.exists():
            debug_counts_dst = job_dir / "debug_counts.json"
            debug_counts_dst.write_bytes(debug_counts_src.read_bytes())
            log(f"Debug counts: {debug_counts_dst}")

        # Ladder-compatible artifacts (minimal):
        # - Always write into results/jobs/<job_id>/ (UI contract).
        # - Additionally, when MINI_LAB_WEEK + (output_parent,label) are provided,
        #   also write into results/labs/mini_week/<output_parent>/<label>/ so the run is
        #   natively consumable by audit/rollup as a canonical mini-week campaign.
        allow_all = os.environ.get("RISK_EVAL_ALLOW_ALL_PLAYBOOKS", "false").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        bypass_lss = os.environ.get("RISK_BYPASS_DYNAMIC_QUARANTINE_LSS_ONLY", "false").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        respect_allowlists = not allow_all
        mini_week_block = None
        if mini_week_run_dir is not None:
            mini_week_block = {
                "output_parent": mini_week_output_parent,
                "label": mini_week_label,
                "run_dir": str(mini_week_run_dir.resolve()),
            }

        job_manifest: Dict[str, Any] = {}
        try:
            job_manifest = {
                "schema_version": "CampaignManifestV0",
                "contract_version": "RunSummaryV0",
                "run_id": run_name,
                "runner": "jobs/backtest_jobs.py",
                "protocol": protocol,
                "job_id": job_id,
                "argv": [
                    "jobs/backtest_jobs.py",
                    "run_backtest_worker",
                    f"--job-id={job_id}",
                    f"--start={request.start_date}",
                    f"--end={request.end_date}",
                    f"--symbols={','.join(request.symbols)}",
                    f"--mode={effective_trading_mode}",
                    f"--trade-types={','.join(effective_trade_types)}",
                ],
                "cwd": str(Path.cwd().resolve()),
                "git_sha": git_sha,
                "run_started_at_utc": run_started_at_utc,
                "symbols": list(request.symbols),
                "start_date": request.start_date,
                "end_date": request.end_date,
                # Keep fields for parity with mini-lab, but do not pretend we had a playbooks YAML override.
                "label": run_name,
                "output_parent": f"jobs/{job_id}",
                "respect_allowlists": respect_allowlists,
                "bypass_lss_quarantine": bypass_lss,
                "playbooks_yaml": None,
                "nf_tp1_rr_meta": None,
                "run_clock_mode": "BACKTEST",
                "lab_environment": build_lab_environment_for_manifest(request.symbols),
                "data_coverage": {
                    "schema_version": "DataCoverageV0",
                    "coverage_ok": bool(dc_report["ok"]),
                    "warmup_start_utc": dc_report.get("warmup_start_utc"),
                    "start_utc": dc_report.get("start_utc"),
                    "end_exclusive_utc": dc_report.get("end_exclusive_utc"),
                    "htf_warmup_days": dc_report.get("htf_warmup_days", int(effective_htf_warmup_days)),
                    "ignore_warmup_check": False,
                    "errors": dc_report.get("errors") or [],
                    "warnings": dc_report.get("warnings") or [],
                    "by_path": dc_report.get("by_path") or [],
                },
            }
            if mini_week_block is not None:
                job_manifest["mini_week"] = mini_week_block
            if protocol_overrides:
                job_manifest["protocol_overrides"] = protocol_overrides

            manifest_path = job_dir / "run_manifest.json"
            manifest_path.write_text(json.dumps(job_manifest, indent=2, ensure_ascii=False), encoding="utf-8")
            artifact_paths["run_manifest"] = "run_manifest.json"
            log(f"Run manifest: {manifest_path}")
        except Exception as e:
            log(f"WARNING: failed to write run_manifest.json: {e}")

        # Job-local summary (flat layout) for UI + `--path results/jobs/<job_id>`
        base_mini_lab_summary: Dict[str, Any] = {
            "protocol": protocol,
            "runner": "jobs/backtest_jobs.py",
            "contract_version": "RunSummaryV0",
            "run_started_at_utc": run_started_at_utc,
            "git_sha": git_sha,
            "run_id": run_name,
            "job_id": job_id,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "symbols": list(request.symbols),
            "respect_allowlists": respect_allowlists,
            "bypass_lss_quarantine": bypass_lss,
            "output_parent": f"jobs/{job_id}",
            "playbooks_yaml": None,
            "nf_tp1_rr_meta": None,
            "data_coverage_ok": bool(dc_report["ok"]),
            "data_coverage_error_count": len(dc_report.get("errors") or []),
            "total_trades": int(result.total_trades),
            "final_capital": str(result.final_capital),
            "profit_factor": float(result.profit_factor) if result.profit_factor is not None else None,
            "expectancy_r": float(result.expectancy_r) if result.expectancy_r is not None else None,
            "winrate": float(result.winrate) if result.winrate is not None else None,
        }
        if mini_week_block is not None:
            base_mini_lab_summary["mini_week"] = mini_week_block
        if protocol_overrides:
            base_mini_lab_summary["protocol_overrides"] = protocol_overrides

        try:
            trade_metrics = summarize_trades_parquet(job_dir / "trades.parquet")
            mini_lab_summary = dict(base_mini_lab_summary)
            if trade_metrics:
                mini_lab_summary["trade_metrics_parquet"] = trade_metrics

            summary_filename = f"mini_lab_summary_job_{job_id}.json"
            summary_path = job_dir / summary_filename
            summary_path.write_text(
                json.dumps(mini_lab_summary, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            artifact_paths["mini_lab_summary"] = summary_filename
            log(f"Mini-lab summary: {summary_path}")
        except Exception as e:
            log(f"WARNING: failed to write mini_lab_summary*.json: {e}")

        # Canonical mini-week layout bridge (nested layout) when requested.
        if mini_week_run_dir is not None:
            try:
                mini_week_manifest = dict(job_manifest)
                mini_week_manifest["label"] = str(mini_week_label)
                mini_week_manifest["output_parent"] = str(mini_week_output_parent)
                mini_week_manifest["mini_week_bridge_source"] = {
                    "job_id": job_id,
                    "job_dir": str(job_dir.resolve()),
                }
                (mini_week_run_dir / "run_manifest.json").write_text(
                    json.dumps(mini_week_manifest, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                log(f"Mini-week manifest: {mini_week_run_dir / 'run_manifest.json'}")
            except Exception as e:
                log(f"WARNING: failed to write mini_week run_manifest.json: {e}")

            try:
                # Prefer the engine-written trades parquet (so parquet_path points at the canonical location).
                canonical_trade_metrics = summarize_trades_parquet(trades_src)
                mini_week_summary = dict(base_mini_lab_summary)
                mini_week_summary["output_parent"] = str(mini_week_output_parent)
                if canonical_trade_metrics:
                    mini_week_summary["trade_metrics_parquet"] = canonical_trade_metrics
                summary_path = mini_week_run_dir / f"mini_lab_summary_{mini_week_label}.json"
                summary_path.write_text(
                    json.dumps(mini_week_summary, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                log(f"Mini-week summary: {summary_path}")
            except Exception as e:
                log(f"WARNING: failed to write mini_week mini_lab_summary*.json: {e}")
        
        # Extract key metrics
        metrics = {
            "total_trades": result.total_trades,
            "total_R_gross": float(result.total_pnl_gross_R),
            "total_R_net": float(result.total_pnl_net_R),
            "total_costs_dollars": float(result.total_costs_dollars),
            "winrate": float(result.winrate),
            "profit_factor": float(result.profit_factor),
            "expectancy_r": float(result.expectancy_r),
            "max_drawdown_r": float(result.max_drawdown_r)
        }
        
        log(f"Metrics: {metrics}")
        
        # Update job
        update_job_status(
            job_id,
            "done",
            artifact_paths=artifact_paths,
            metrics=metrics
        )
        
        log("Job completed successfully")
        
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        try:
            log(f"ERROR: {error_msg}")
            log(traceback.format_exc())
        except:
            # If logging fails, at least try to update status
            pass
        
        # CRITICAL: Always update status to failed on exception
        try:
            update_job_status(
                job_id,
                "failed",
                error=error_msg
            )
        except Exception as update_err:
            # Last resort: try to write directly
            try:
                job_file = get_job_file(job_id)
                with open(job_file, 'r', encoding='utf-8') as f:
                    job_data = json.load(f)
                job_data["status"] = "failed"
                job_data["completed_at"] = datetime.now().isoformat()
                job_data["error"] = f"{error_msg} (status update error: {update_err})"
                with open(job_file, 'w', encoding='utf-8') as f:
                    json.dump(job_data, f, indent=2, ensure_ascii=False)
            except:
                # If everything fails, at least log to stderr
                import sys
                print(f"[CRITICAL] Job {job_id} failed but could not update status", file=sys.stderr)
    
    finally:
        # GUARANTEE: Job must exit "running" state
        try:
            job_file = get_job_file(job_id)
            with open(job_file, 'r', encoding='utf-8') as f:
                job_data = json.load(f)
            if job_data.get("status") == "running":
                # If still running, mark as failed (worker crashed)
                job_data["status"] = "failed"
                job_data["completed_at"] = datetime.now().isoformat()
                if not job_data.get("error"):
                    job_data["error"] = "Worker crashed or exited unexpectedly"
                with open(job_file, 'w', encoding='utf-8') as f:
                    json.dump(job_data, f, indent=2, ensure_ascii=False)
        except:
            pass  # If we can't update, at least we tried

        # Restore protocol env flags (worker processes can be reused across jobs).
        try:
            if _old_env is not None:
                for k, v in _old_env.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v
        except Exception:
            pass


def run_mini_lab_walk_forward_worker(job_id: str, request_dict: dict):
    """
    UI job worker: canonical mini walk-forward (2 splits OOS) under results/labs/mini_week/<output_parent>/.

    Implementation choice (minimal divergence vs campaigns):
    - Reuses the canonical orchestrator `scripts/run_walk_forward_mini_lab.py`, which itself
      spawns `scripts/run_mini_lab_week.py` per split window.
    - Writes `walk_forward_campaign.json` under the canonical campaign root, plus a small pointer
      file under the UI job directory for traceability.
    """
    import sys
    import traceback
    import subprocess
    from pathlib import Path

    backend_dir = Path(__file__).parent.parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    from utils.path_resolver import results_path
    from utils.campaign_rollup import rollup_summaries_under_base

    log_file = get_job_log(job_id)

    def log(msg: str) -> None:
        try:
            with open(log_file, "a", encoding="utf-8", errors="replace") as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] {msg}\n")
                f.flush()
        except Exception:
            pass

    try:
        run_started_at_utc = datetime.now(timezone.utc).isoformat()
        log("Starting mini-lab walk-forward worker...")
        update_job_status(job_id, "running")

        request = BacktestJobRequest(**request_dict)
        if request.protocol != "MINI_LAB_WALK_FORWARD":
            raise ValueError(f"Invalid protocol for walk-forward worker: {request.protocol}")

        if not request.output_parent:
            raise ValueError("protocol=MINI_LAB_WALK_FORWARD requires output_parent")
        _require_safe_layout_token("output_parent", request.output_parent)

        if request.label is not None:
            raise ValueError("protocol=MINI_LAB_WALK_FORWARD does not accept label (labels are generated)")

        label_prefix = (request.label_prefix or "wf").strip()
        _require_safe_layout_token("label_prefix", label_prefix)

        # Align contract with mini-lab week: AGGRESSIVE + DAILY+SCALP.
        if request.trading_mode != "AGGRESSIVE":
            raise ValueError("protocol=MINI_LAB_WALK_FORWARD requires trading_mode=AGGRESSIVE")
        if sorted({x.strip().upper() for x in request.trade_types}) != ["DAILY", "SCALP"]:
            raise ValueError("protocol=MINI_LAB_WALK_FORWARD requires trade_types=['DAILY','SCALP']")

        symbols = [s.strip().upper() for s in (request.symbols or []) if s and s.strip()]
        if not symbols:
            raise ValueError("symbols cannot be empty")
        symbols_arg = ",".join(symbols)

        campaign_root = results_path("labs", "mini_week", request.output_parent)
        wf_script = backend_dir / "scripts" / "run_walk_forward_mini_lab.py"
        cmd = [
            sys.executable,
            str(wf_script),
            "--start",
            request.start_date,
            "--end",
            request.end_date,
            "--output-parent",
            request.output_parent,
            "--label-prefix",
            label_prefix,
            "--symbols",
            symbols_arg,
        ]

        log(f"Launching canonical WF script: {' '.join(cmd)}")
        with open(log_file, "a", encoding="utf-8", errors="replace") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] SUBPROCESS {' '.join(cmd)}\n")
            f.flush()
            proc = subprocess.run(cmd, cwd=str(backend_dir), stdout=f, stderr=subprocess.STDOUT)
        rc = int(proc.returncode)
        log(f"WF subprocess returncode: {rc}")

        wf_meta_src = campaign_root / "walk_forward_campaign.json"
        if not wf_meta_src.is_file():
            raise RuntimeError(f"Expected walk_forward_campaign.json missing: {wf_meta_src}")

        artifact_paths: Dict[str, str] = {}
        job_dir = get_job_dir(job_id)

        # Copy WF meta into job dir for UI download/debugging (canonical source stays under labs/mini_week).
        try:
            wf_meta_dst = job_dir / "walk_forward_campaign.json"
            wf_meta_dst.write_bytes(wf_meta_src.read_bytes())
            artifact_paths["walk_forward_campaign"] = wf_meta_dst.name
        except Exception as e:
            log(f"WARNING: failed to copy walk_forward_campaign.json into job dir: {e}")

        # Pointer to canonical campaign root (downloadable, small).
        try:
            pointer = {
                "schema_version": "MiniLabWalkForwardJobPointerV0",
                "job_id": job_id,
                "run_started_at_utc": run_started_at_utc,
                "output_parent": request.output_parent,
                "label_prefix": label_prefix,
                "campaign_root": str(campaign_root.resolve()),
                "walk_forward_campaign_path": str(wf_meta_src.resolve()),
            }
            pth = job_dir / "campaign_pointer.json"
            pth.write_text(json.dumps(pointer, indent=2, ensure_ascii=False), encoding="utf-8")
            artifact_paths["campaign_pointer"] = pth.name
        except Exception as e:
            log(f"WARNING: failed to write campaign_pointer.json: {e}")

        # Post-processing: produce cockpit-ready artefacts directly under the canonical campaign root.
        # Reuse scripts (no re-implementation): audit + rollup => campaign_audit.json / campaign_rollup.json
        if rc == 0:
            audit_script = backend_dir / "scripts" / "audit_campaign_output_parent.py"
            rollup_script = backend_dir / "scripts" / "rollup_campaign_summaries.py"
            audit_out = campaign_root / "campaign_audit.json"
            rollup_out = campaign_root / "campaign_rollup.json"
            for script_path, out_path, name in [
                (audit_script, audit_out, "audit"),
                (rollup_script, rollup_out, "rollup"),
            ]:
                cmd2 = [
                    sys.executable,
                    str(script_path),
                    "--output-parent",
                    request.output_parent,
                    "--out",
                    str(out_path),
                ]
                log(f"Launching campaign {name}: {' '.join(cmd2)}")
                with open(log_file, "a", encoding="utf-8", errors="replace") as f:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"[{timestamp}] SUBPROCESS {' '.join(cmd2)}\n")
                    f.flush()
                    proc2 = subprocess.run(cmd2, cwd=str(backend_dir), stdout=f, stderr=subprocess.STDOUT)
                rc2 = int(proc2.returncode)
                log(f"{name} subprocess returncode: {rc2}")
                if not out_path.is_file():
                    raise RuntimeError(f"Expected {name} output missing: {out_path}")
                if rc2 != 0:
                    log(f"WARNING: {name} returned {rc2} (file written: {out_path.name})")

            # Expose final campaign artefacts under the job directory (UI entrypoint) without duplicating the run dirs.
            # Canonical source stays under results/labs/mini_week/<output_parent>/.
            for src, key in [
                (audit_out, "campaign_audit"),
                (rollup_out, "campaign_rollup"),
            ]:
                try:
                    dst = job_dir / src.name
                    dst.write_bytes(src.read_bytes())
                    artifact_paths[key] = dst.name
                except Exception as e:
                    log(f"WARNING: failed to copy {src.name} into job dir: {e}")

            # Enrich pointer (best-effort) with canonical paths and job-facing filenames.
            try:
                pth = job_dir / "campaign_pointer.json"
                if pth.is_file():
                    pointer = json.loads(pth.read_text(encoding="utf-8"))
                    pointer.update(
                        {
                            "campaign_audit_path": str(audit_out.resolve()),
                            "campaign_rollup_path": str(rollup_out.resolve()),
                            "job_artifacts": {
                                "walk_forward_campaign": artifact_paths.get("walk_forward_campaign"),
                                "campaign_audit": artifact_paths.get("campaign_audit"),
                                "campaign_rollup": artifact_paths.get("campaign_rollup"),
                            },
                        }
                    )
                    pth.write_text(json.dumps(pointer, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception as e:
                log(f"WARNING: failed to enrich campaign_pointer.json: {e}")

        # Best-effort rollup for job metrics.
        metrics: Dict[str, Any] = {
            "protocol": request.protocol,
            "output_parent": request.output_parent,
            "label_prefix": label_prefix,
        }
        try:
            rep = rollup_summaries_under_base(campaign_root, logical_name=request.output_parent)
            metrics.update(
                {
                    "campaign_run_count": rep.get("run_count"),
                    "total_trades_sum": rep.get("total_trades_sum"),
                    "expectancy_r_weighted_by_trades": rep.get("expectancy_r_weighted_by_trades"),
                }
            )
        except Exception as e:
            log(f"WARNING: rollup failed: {e}")

        if rc == 0:
            update_job_status(job_id, "done", artifact_paths=artifact_paths, metrics=metrics)
            log("Walk-forward job completed successfully")
        else:
            update_job_status(
                job_id,
                "failed",
                error=f"Walk-forward subprocess returned {rc}",
                artifact_paths=artifact_paths,
                metrics=metrics,
            )
            log("Walk-forward job failed (non-zero returncode)")

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        try:
            log(f"ERROR: {error_msg}")
            log(traceback.format_exc())
        except Exception:
            pass
        try:
            update_job_status(job_id, "failed", error=error_msg)
        except Exception:
            pass


def submit_job(request: BacktestJobRequest) -> str:
    """
    Submit job for async execution
    
    Returns:
        job_id
    
    Raises:
        ValueError: If a job is already running or queued
    """
    # Check for running or queued jobs (limit: 1 job max)
    existing_jobs = list_jobs(limit=100)  # Check all jobs to find active ones
    for job in existing_jobs:
        if job.status in ["running", "queued"]:
            raise ValueError(f"Un job est déjà en cours. Veuillez patienter. (Job {job.job_id}: {job.status})")
    
    job_id = create_job(request)
    
    # Submit to executor (P0 Fix #1: vérifier executor actif)
    executor = get_executor()
    if executor is None:
        raise RuntimeError("Executor not available")
    
    try:
        if request.protocol == "MINI_LAB_WALK_FORWARD":
            executor.submit(run_mini_lab_walk_forward_worker, job_id, request.dict())
        else:
            executor.submit(run_backtest_worker, job_id, request.dict())
        logger.info(f"Submitted job {job_id} to executor (protocol={request.protocol})")
    except RuntimeError as e:
        # Si executor shutdown, recréer et réessayer
        if "cannot schedule new futures after shutdown" in str(e).lower():
            logger.warning("Executor was shutdown, recreating...")
            global _executor
            _executor = None
            executor = get_executor()
            if request.protocol == "MINI_LAB_WALK_FORWARD":
                executor.submit(run_mini_lab_walk_forward_worker, job_id, request.dict())
            else:
                executor.submit(run_backtest_worker, job_id, request.dict())
            logger.info(f"Submitted job {job_id} to new executor (protocol={request.protocol})")
        else:
            raise
    
    return job_id
