"""
PHASE C - Backtest API Routes
Endpoints for UI-triggered backtests
"""

import os
import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import FileResponse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

from jobs.backtest_jobs import (
    BacktestJobRequest,
    submit_job,
    get_job_status,
    list_jobs,
    get_job_dir,
    get_job_log,
)
from security.api_key import require_dexterio_api_key
from security.validation import validate_job_id, assert_safe_job_file
from security.http_errors import safe_http_500_detail

router = APIRouter(
    prefix="/backtests",
    tags=["backtests"],
    dependencies=[Depends(require_dexterio_api_key)],
)

# Limite de taille lue pour éviter saturer la mémoire / la réponse HTTP
_MAX_JOB_LOG_BYTES = int(os.environ.get("MAX_JOB_LOG_BYTES", str(512 * 1024)))


@router.post("/run")
async def run_backtest(request: BacktestJobRequest):
    """
    Launch a backtest job

    Returns:
        {job_id: str}
    """
    try:
        start = datetime.strptime(request.start_date, "%Y-%m-%d")
        end = datetime.strptime(request.end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD")

    if end < start:
        raise HTTPException(400, "end_date must be >= start_date")

    days = (end - start).days
    if days > 31:
        raise HTTPException(400, f"Date range too large: {days} days (max 31)")

    if not request.symbols:
        raise HTTPException(400, "symbols cannot be empty")

    for symbol in request.symbols:
        if symbol not in ["SPY", "QQQ"]:
            raise HTTPException(400, f"Unsupported symbol: {symbol}")

    if request.trading_mode not in ["SAFE", "AGGRESSIVE"]:
        raise HTTPException(400, f"Invalid trading_mode: {request.trading_mode}")

    for tt in request.trade_types:
        if tt not in ["DAILY", "SCALP"]:
            raise HTTPException(400, f"Invalid trade_type: {tt}")

    try:
        job_id = submit_job(request)
        logger.info(f"✅ Job submitted successfully: job_id={job_id}")
    except ValueError as e:
        logger.error(f"❌ Job submission failed: {e}")
        raise HTTPException(409, str(e))
    except Exception as e:
        logger.error(f"❌ Unexpected error in run_backtest: {e}", exc_info=True)
        raise HTTPException(500, safe_http_500_detail(e))

    return {"job_id": job_id}


@router.get("")
async def list_all_jobs(limit: int = Query(20, ge=1, le=500)):
    """List recent jobs (déclaré avant /{job_id} pour éviter ambiguïtés de routage)"""
    jobs = list_jobs(limit=limit)
    return {"jobs": jobs}


@router.post("/reset_stale")
async def reset_stale_jobs():
    """Reset stale jobs (running/queued with no recent activity)"""
    from jobs.backtest_jobs import update_job_status, get_job_log as gj_log

    all_jobs = list_jobs(limit=1000)
    stale_threshold = datetime.now() - timedelta(minutes=10)

    reset_count = 0
    for job in all_jobs:
        if job.status in ["running", "queued"]:
            try:
                created_at = datetime.fromisoformat(job.created_at.replace("Z", "+00:00"))
                if created_at < stale_threshold:
                    log_file = gj_log(job.job_id)
                    has_error = False
                    if log_file.exists():
                        try:
                            log_content = log_file.read_text(encoding="utf-8", errors="replace")
                            if "ERROR:" in log_content:
                                has_error = True
                        except OSError:
                            pass

                    if has_error or created_at < stale_threshold:
                        update_job_status(
                            job.job_id,
                            "failed",
                            error="Stale job reset (no activity for 10+ minutes or contains errors)",
                        )
                        reset_count += 1
            except (ValueError, OSError):
                update_job_status(
                    job.job_id,
                    "failed",
                    error="Stale job reset (unable to verify activity)",
                )
                reset_count += 1

    return {"reset_count": reset_count, "message": f"Reset {reset_count} stale job(s)"}


@router.get("/{job_id}")
async def get_job(job_id: str):
    """Get job status"""
    validate_job_id(job_id)
    status = get_job_status(job_id)

    if not status:
        raise HTTPException(404, f"Job not found: {job_id}")

    return status


@router.get("/{job_id}/results")
async def get_job_results(job_id: str):
    """Get job results (metrics + artifact paths)"""
    validate_job_id(job_id)
    status = get_job_status(job_id)

    if not status:
        raise HTTPException(404, f"Job not found: {job_id}")

    if status.status != "done":
        raise HTTPException(400, f"Job not done yet: {status.status}")

    return {
        "job_id": job_id,
        "metrics": status.metrics,
        "artifact_paths": status.artifact_paths,
        "download_urls": {
            name: f"/api/backtests/{job_id}/download?file={filename}"
            for name, filename in (status.artifact_paths or {}).items()
        },
    }


@router.get("/{job_id}/download")
async def download_artifact(job_id: str, file: str):
    """Download an artifact file"""
    validate_job_id(job_id)
    status = get_job_status(job_id)

    if not status:
        raise HTTPException(404, f"Job not found: {job_id}")

    job_dir = get_job_dir(job_id)
    file_path = assert_safe_job_file(job_dir, file)

    if not file_path.exists():
        raise HTTPException(404, f"File not found: {file}")

    return FileResponse(
        path=str(file_path),
        filename=file,
        media_type="application/octet-stream",
    )


@router.get("/{job_id}/log")
async def get_job_log_content(job_id: str):
    """Get job log content (tronqué si fichier très volumineux)"""
    validate_job_id(job_id)
    status = get_job_status(job_id)

    if not status:
        raise HTTPException(404, f"Job not found: {job_id}")

    log_file = get_job_log(job_id)

    if not log_file.exists():
        return {"log": ""}

    try:
        raw = log_file.read_bytes()
        truncated = len(raw) > _MAX_JOB_LOG_BYTES
        chunk = raw[-_MAX_JOB_LOG_BYTES:] if truncated else raw
        log_content = chunk.decode("utf-8", errors="replace")
        if truncated:
            log_content = (
                f"[… journal tronqué: affichage des {_MAX_JOB_LOG_BYTES} derniers octets …]\n"
                + log_content
            )
    except Exception as e:
        log_content = f"[Error reading log: {e}]"

    return {"log": log_content}


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a running or queued job"""
    validate_job_id(job_id)
    from jobs.backtest_jobs import update_job_status

    status = get_job_status(job_id)
    if not status:
        raise HTTPException(404, f"Job not found: {job_id}")

    if status.status not in ["running", "queued"]:
        raise HTTPException(400, f"Cannot cancel job with status: {status.status}")

    update_job_status(
        job_id,
        "failed",
        error="Canceled by user",
    )

    return {"job_id": job_id, "status": "failed", "message": "Job canceled"}
