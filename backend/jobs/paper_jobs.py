"""Sprint 4-lite — Paper jobs skeleton.

Miroir minimal de backtest_jobs.py pour paper runs. Sans stratégie spécifique
câblée — c'est le runtime container qui peut héberger n'importe quelle
stratégie une fois qu'un edge sera validé.

États job : CREATED → RUNNING → STOPPED | KILLED | ERROR
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from engines.execution.broker_interface import Broker
from engines.execution.broker_paper_local import PaperLocalBroker
from engines.execution.paper_logger import PaperLogger


class JobStatus(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    KILLED = "KILLED"
    ERROR = "ERROR"


@dataclass
class PaperJob:
    job_id: str
    name: str
    strategy_name: str
    broker_type: str  # "paper_local" | "ibkr" | "alpaca"
    status: JobStatus = JobStatus.CREATED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    error_msg: Optional[str] = None
    config: dict[str, Any] = field(default_factory=dict)
    log_dir: Optional[Path] = None
    _killed_flag: bool = False
    _thread: Optional[threading.Thread] = None
    _broker: Optional[Broker] = None
    _logger: Optional[PaperLogger] = None


_jobs_registry: dict[str, PaperJob] = {}


def create_job(name: str, strategy_name: str = "none",
                 broker_type: str = "paper_local",
                 config: Optional[dict[str, Any]] = None,
                 log_root: Path = Path("results/paper_runs")) -> PaperJob:
    """Create a paper job (CREATED state). No execution yet."""
    job_id = str(uuid.uuid4())[:8]
    log_dir = log_root / f"{job_id}_{name}"
    job = PaperJob(
        job_id=job_id,
        name=name,
        strategy_name=strategy_name,
        broker_type=broker_type,
        config=config or {},
        log_dir=log_dir,
    )
    _jobs_registry[job_id] = job

    # Init broker + logger
    if broker_type == "paper_local":
        initial_cash = job.config.get("initial_cash", 50_000.0)
        spread_bps = job.config.get("spread_bps", 1.0)
        slippage_pct = job.config.get("slippage_pct", 0.0005)
        job._broker = PaperLocalBroker(
            initial_cash=initial_cash,
            spread_bps=spread_bps,
            slippage_pct=slippage_pct,
        )
    else:
        raise NotImplementedError(f"Broker type {broker_type} not implemented yet "
                                    "(IBKR + Alpaca = post-edge-validated)")

    job._logger = PaperLogger(log_dir)
    job._logger.write_manifest({
        "job_id": job_id,
        "name": name,
        "strategy_name": strategy_name,
        "broker_type": broker_type,
        "config": config or {},
    })
    return job


def get_job(job_id: str) -> Optional[PaperJob]:
    return _jobs_registry.get(job_id)


def list_jobs() -> list[PaperJob]:
    return list(_jobs_registry.values())


def start_job(job_id: str, runner_callable=None) -> bool:
    """Start a job in a background thread.

    runner_callable : callable(job) -> None that implements the strategy loop.
                      If None, job stays in RUNNING state but does nothing
                      (useful for testing kill-switch).
    """
    job = _jobs_registry.get(job_id)
    if job is None:
        return False
    if job.status != JobStatus.CREATED:
        return False
    job.status = JobStatus.RUNNING
    job.started_at = datetime.now(timezone.utc)

    def _run():
        try:
            if runner_callable is not None:
                runner_callable(job)
            else:
                # No-op runner : just sit in RUNNING state until killed
                while not job._killed_flag and job.status == JobStatus.RUNNING:
                    threading.Event().wait(timeout=1.0)
            if job.status == JobStatus.RUNNING:
                job.status = JobStatus.STOPPED
        except Exception as e:
            job.status = JobStatus.ERROR
            job.error_msg = str(e)
        finally:
            job.stopped_at = datetime.now(timezone.utc)

    job._thread = threading.Thread(target=_run, daemon=True)
    job._thread.start()
    return True


def stop_job(job_id: str) -> bool:
    """Graceful stop. Sets killed_flag + status; runner should respect."""
    job = _jobs_registry.get(job_id)
    if job is None or job.status != JobStatus.RUNNING:
        return False
    job._killed_flag = True
    job.status = JobStatus.STOPPED
    return True


def kill_job(job_id: str) -> bool:
    """Hard kill : flush positions to cash via broker, then stop. Idempotent."""
    job = _jobs_registry.get(job_id)
    if job is None:
        return False
    if job.status not in (JobStatus.RUNNING, JobStatus.CREATED):
        return True  # already stopped/killed/error → idempotent OK
    job._killed_flag = True

    # Close all open positions via market orders (kill-switch behavior)
    if job._broker is not None:
        from engines.execution.broker_interface import OrderSide
        for pos in job._broker.get_positions():
            close_side = OrderSide.SELL if pos.quantity > 0 else OrderSide.BUY
            order = job._broker.place_order(
                symbol=pos.symbol,
                side=close_side,
                quantity=abs(pos.quantity),
            )
            if job._logger is not None:
                job._logger.log_execution(order, event="kill_close")
        # Cancel all open orders
        for o in job._broker.get_open_orders():
            job._broker.cancel_order(o.order_id)
            if job._logger is not None:
                job._logger.log_execution(o, event="kill_cancel")

    job.status = JobStatus.KILLED
    job.stopped_at = datetime.now(timezone.utc)
    return True


def get_job_status(job_id: str) -> Optional[dict[str, Any]]:
    job = _jobs_registry.get(job_id)
    if job is None:
        return None
    account = job._broker.get_account() if job._broker else None
    return {
        "job_id": job.job_id,
        "name": job.name,
        "strategy_name": job.strategy_name,
        "broker_type": job.broker_type,
        "status": str(job.status),
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "stopped_at": job.stopped_at.isoformat() if job.stopped_at else None,
        "error_msg": job.error_msg,
        "log_dir": str(job.log_dir),
        "account": {
            "cash": account.cash,
            "equity": account.equity,
            "realized_pnl": account.realized_pnl,
        } if account else None,
        "n_positions": len(job._broker.get_positions()) if job._broker else 0,
        "n_open_orders": len(job._broker.get_open_orders()) if job._broker else 0,
    }


def reset_registry() -> None:
    """Test helper : clear job registry."""
    _jobs_registry.clear()
