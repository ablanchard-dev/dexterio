"""
PHASE C - Backtest API Routes
Endpoints for UI-triggered backtests
"""

import os
from fastapi import APIRouter, HTTPException, Response, Header, Depends
from fastapi.responses import FileResponse
from datetime import datetime
from pathlib import Path
from typing import Optional

from jobs.backtest_jobs import (
    BacktestJobRequest,
    BacktestJobStatus,
    submit_job,
    get_job_status,
    list_jobs,
    get_job_dir,
    get_job_log
)

router = APIRouter(prefix="/backtests", tags=["backtests"])


def verify_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-KEY")) -> bool:
    """
    Verify API key from X-API-KEY header.
    
    - If DEXTERIO_API_KEY env var is set: key must match
    - If DEXTERIO_API_KEY is not set: allow all (dev mode)
    """
    expected_key = os.getenv("DEXTERIO_API_KEY")
    
    # Dev mode: no key required if env var not set
    if not expected_key:
        return True
    
    # Production mode: key must be provided and match
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-KEY header")
    
    if x_api_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    return True


@router.post("/run", dependencies=[Depends(verify_api_key)])
async def run_backtest(request: BacktestJobRequest):
    """
    Launch a backtest job
    
    Returns:
        {job_id: str}
    """
    # Validate dates
    try:
        start = datetime.strptime(request.start_date, "%Y-%m-%d")
        end = datetime.strptime(request.end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD")
    
    if end < start:
        raise HTTPException(400, "end_date must be >= start_date")
    
    # Validate window (max 31 days)
    days = (end - start).days
    if days > 31:
        raise HTTPException(400, f"Date range too large: {days} days (max 31)")
    
    # Validate symbols
    if not request.symbols:
        raise HTTPException(400, "symbols cannot be empty")
    
    for symbol in request.symbols:
        if symbol not in ["SPY", "QQQ"]:  # Extend as needed
            raise HTTPException(400, f"Unsupported symbol: {symbol}")
    
    # Validate mode
    if request.trading_mode not in ["SAFE", "AGGRESSIVE"]:
        raise HTTPException(400, f"Invalid trading_mode: {request.trading_mode}")
    
    # Validate trade types
    for tt in request.trade_types:
        if tt not in ["DAILY", "SCALP"]:
            raise HTTPException(400, f"Invalid trade_type: {tt}")
    
    # Submit job
    try:
        job_id = submit_job(request)
    except ValueError as e:
        raise HTTPException(409, str(e))  # 409 Conflict
    
    return {"job_id": job_id}


@router.get("/{job_id}", dependencies=[Depends(verify_api_key)])
async def get_job(job_id: str):
    """Get job status"""
    status = get_job_status(job_id)
    
    if not status:
        raise HTTPException(404, f"Job not found: {job_id}")
    
    return status


@router.get("/{job_id}/results", dependencies=[Depends(verify_api_key)])
async def get_job_results(job_id: str):
    """Get job results (metrics + artifact paths)"""
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
        }
    }


@router.get("/{job_id}/download", dependencies=[Depends(verify_api_key)])
async def download_artifact(job_id: str, file: str):
    """Download an artifact file"""
    status = get_job_status(job_id)
    
    if not status:
        raise HTTPException(404, f"Job not found: {job_id}")
    
    # Validate filename (security)
    if not file or ".." in file or "/" in file:
        raise HTTPException(400, "Invalid filename")
    
    job_dir = get_job_dir(job_id)
    file_path = job_dir / file
    
    if not file_path.exists():
        raise HTTPException(404, f"File not found: {file}")
    
    return FileResponse(
        path=str(file_path),
        filename=file,
        media_type="application/octet-stream"
    )


@router.get("/{job_id}/log", dependencies=[Depends(verify_api_key)])
async def get_job_log_content(job_id: str):
    """Get job log content"""
    status = get_job_status(job_id)
    
    if not status:
        raise HTTPException(404, f"Job not found: {job_id}")
    
    log_file = get_job_log(job_id)
    
    if not log_file.exists():
        return {"log": ""}
    
    try:
        log_content = log_file.read_text(encoding='utf-8', errors='replace')
    except Exception as e:
        log_content = f"[Error reading log: {e}]"
    
    return {"log": log_content}


@router.get("", dependencies=[Depends(verify_api_key)])
async def list_all_jobs(limit: int = 20):
    """List recent jobs"""
    jobs = list_jobs(limit=limit)
    return {"jobs": jobs}


@router.post("/{job_id}/cancel", dependencies=[Depends(verify_api_key)])
async def cancel_job(job_id: str):
    """Cancel a running or queued job"""
    from jobs.backtest_jobs import get_job_status, update_job_status
    
    status = get_job_status(job_id)
    if not status:
        raise HTTPException(404, f"Job not found: {job_id}")
    
    if status.status not in ["running", "queued"]:
        raise HTTPException(400, f"Cannot cancel job with status: {status.status}")
    
    update_job_status(
        job_id,
        "failed",
        error="Canceled by user"
    )
    
    return {"job_id": job_id, "status": "failed", "message": "Job canceled"}


@router.post("/reset_stale", dependencies=[Depends(verify_api_key)])
async def reset_stale_jobs():
    """Reset stale jobs (running/queued with no recent activity)"""
    from jobs.backtest_jobs import list_jobs, update_job_status, get_job_status
    from datetime import datetime, timedelta
    
    all_jobs = list_jobs(limit=1000)  # Get all jobs
    stale_threshold = datetime.now() - timedelta(minutes=10)  # 10 minutes
    
    reset_count = 0
    for job in all_jobs:
        if job.status in ["running", "queued"]:
            # Check if job is stale
            try:
                created_at = datetime.fromisoformat(job.created_at.replace('Z', '+00:00'))
                if created_at < stale_threshold:
                    # Check log for ERROR
                    from jobs.backtest_jobs import get_job_log
                    log_file = get_job_log(job.job_id)
                    has_error = False
                    if log_file.exists():
                        try:
                            log_content = log_file.read_text(encoding='utf-8', errors='replace')
                            if "ERROR:" in log_content:
                                has_error = True
                        except:
                            pass
                    
                    if has_error or created_at < stale_threshold:
                        update_job_status(
                            job.job_id,
                            "failed",
                            error="Stale job reset (no activity for 10+ minutes or contains errors)"
                        )
                        reset_count += 1
            except:
                # If we can't parse dates, mark as stale anyway
                update_job_status(
                    job.job_id,
                    "failed",
                    error="Stale job reset (unable to verify activity)"
                )
                reset_count += 1
    
    return {"reset_count": reset_count, "message": f"Reset {reset_count} stale job(s)"}
