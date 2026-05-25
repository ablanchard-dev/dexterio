"""Sprint 4-lite tests — broker_paper_local + paper_jobs + paper_logger.

Smoke + intégration de bout en bout sur dummy strategy.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from engines.execution.broker_interface import (
    AccountSnapshot,
    Broker,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
)
from engines.execution.broker_paper_local import PaperLocalBroker
from engines.execution.paper_logger import PaperLogger
from jobs.paper_jobs import (
    JobStatus,
    create_job,
    get_job,
    get_job_status,
    kill_job,
    reset_registry,
    start_job,
    stop_job,
)


@pytest.fixture(autouse=True)
def _reset():
    reset_registry()
    yield
    reset_registry()


# ===== Broker tests =====


def test_broker_paper_local_market_buy_fills_immediately():
    broker = PaperLocalBroker(initial_cash=10_000.0)
    broker.update_market_data({"SPY": 600.0})
    order = broker.place_order("SPY", OrderSide.BUY, 10, OrderType.MARKET)
    assert order.status == OrderStatus.FILLED
    assert order.fill_quantity == 10
    assert order.fill_price > 600.0  # adverse slippage applied (buy higher)
    pos = broker.get_positions()
    assert len(pos) == 1
    assert pos[0].symbol == "SPY"
    assert pos[0].quantity == 10


def test_broker_paper_local_no_market_data_rejects():
    broker = PaperLocalBroker(initial_cash=10_000.0)
    order = broker.place_order("XYZ", OrderSide.BUY, 5)
    assert order.status == OrderStatus.REJECTED
    assert "No market data" in (order.error_msg or "")


def test_broker_paper_local_limit_order_fills_when_price_touches():
    broker = PaperLocalBroker(initial_cash=10_000.0)
    broker.update_market_data({"SPY": 600.0})
    order = broker.place_order("SPY", OrderSide.BUY, 10, OrderType.LIMIT, limit_price=595.0)
    assert order.status == OrderStatus.PENDING
    # Price doesn't touch yet
    broker.update_market_data({"SPY": 597.0})
    assert order.status == OrderStatus.PENDING
    # Price touches limit
    broker.update_market_data({"SPY": 594.0})
    assert order.status == OrderStatus.FILLED


def test_broker_paper_local_cancel_pending_order():
    broker = PaperLocalBroker(initial_cash=10_000.0)
    broker.update_market_data({"SPY": 600.0})
    order = broker.place_order("SPY", OrderSide.BUY, 10, OrderType.LIMIT, limit_price=550.0)
    assert order.status == OrderStatus.PENDING
    cancelled = broker.cancel_order(order.order_id)
    assert cancelled is True
    assert order.status == OrderStatus.CANCELLED
    # Cannot cancel twice
    assert broker.cancel_order(order.order_id) is False


def test_broker_paper_local_get_account_tracks_equity():
    broker = PaperLocalBroker(initial_cash=10_000.0, spread_bps=0, slippage_pct=0)
    broker.update_market_data({"SPY": 600.0})
    broker.place_order("SPY", OrderSide.BUY, 10)
    account = broker.get_account()
    assert account.cash == pytest.approx(10_000.0 - 10 * 600.0, abs=1.0)
    assert account.equity == pytest.approx(10_000.0, abs=1.0)
    # Price moves up
    broker.update_market_data({"SPY": 610.0})
    account = broker.get_account()
    assert account.equity == pytest.approx(10_000.0 + 10 * 10, abs=1.0)


# ===== Logger tests =====


def test_paper_logger_writes_manifest_and_logs(tmp_path):
    logger = PaperLogger(tmp_path / "run1")
    logger.write_manifest({"job_id": "test1", "strategy": "dummy"})
    assert (tmp_path / "run1" / "manifest.json").exists()

    from datetime import datetime, timezone
    logger.log_decision(
        datetime.now(timezone.utc), "SPY", "LONG", "test reason",
        extra={"signal_strength": 0.8},
    )
    assert (tmp_path / "run1" / "decision_log.jsonl").exists()
    with (tmp_path / "run1" / "decision_log.jsonl").open() as f:
        lines = f.readlines()
    assert len(lines) == 1
    assert "SPY" in lines[0]
    assert "test reason" in lines[0]


# ===== Job tests =====


def test_create_job_returns_job_with_id(tmp_path):
    job = create_job(name="test", log_root=tmp_path)
    assert job.job_id is not None
    assert job.status == JobStatus.CREATED
    assert job.log_dir.exists()


def test_start_and_stop_job_with_no_runner(tmp_path):
    job = create_job(name="noop", log_root=tmp_path)
    started = start_job(job.job_id, runner_callable=None)
    assert started is True
    assert job.status == JobStatus.RUNNING
    time.sleep(0.2)
    stopped = stop_job(job.job_id)
    assert stopped is True
    time.sleep(1.5)  # let thread finish
    assert job.status in (JobStatus.STOPPED,)


def test_kill_job_flushes_positions(tmp_path):
    job = create_job(name="kill_test", log_root=tmp_path)
    # Inject some position via broker
    job._broker.update_market_data({"SPY": 600.0})
    job._broker.place_order("SPY", OrderSide.BUY, 5)
    assert len(job._broker.get_positions()) == 1
    # Kill : should close position
    killed = kill_job(job.job_id)
    assert killed is True
    assert job.status == JobStatus.KILLED
    assert len(job._broker.get_positions()) == 0


def test_kill_job_idempotent(tmp_path):
    job = create_job(name="idempotent_kill", log_root=tmp_path)
    assert kill_job(job.job_id) is True
    # Second call returns True (idempotent OK)
    assert kill_job(job.job_id) is True


def test_get_job_status_returns_full_dict(tmp_path):
    job = create_job(name="status_test", log_root=tmp_path)
    status = get_job_status(job.job_id)
    assert status is not None
    assert status["job_id"] == job.job_id
    assert status["status"] == "JobStatus.CREATED"
    assert status["account"]["cash"] == pytest.approx(50_000.0, abs=1.0)


def test_dummy_strategy_runs_via_runner_callable(tmp_path):
    """End-to-end : create job, start with simple runner, verify it ran."""
    job = create_job(name="strat_test", log_root=tmp_path)

    def dummy_runner(j):
        # Simulate a strategy : place 1 buy then exit
        j._broker.update_market_data({"SPY": 600.0})
        order = j._broker.place_order("SPY", OrderSide.BUY, 5)
        j._logger.log_execution(order, event="placed")
        # Move price up, snapshot
        j._broker.update_market_data({"SPY": 605.0})
        j._logger.log_snapshot(j._broker.get_account(), j._broker.get_positions())
        # Exit
        sell_order = j._broker.place_order("SPY", OrderSide.SELL, 5)
        j._logger.log_execution(sell_order, event="placed")

    started = start_job(job.job_id, runner_callable=dummy_runner)
    assert started is True
    time.sleep(1.0)
    status = get_job_status(job.job_id)
    assert status["status"] in ("JobStatus.STOPPED", "JobStatus.RUNNING")
    # Verify logs written
    assert (job.log_dir / "execution_log.jsonl").exists()
    assert (job.log_dir / "account_snapshots.jsonl").exists()
