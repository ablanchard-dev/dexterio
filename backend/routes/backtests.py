"""
PHASE C - Backtest API Routes
Endpoints for UI-triggered backtests
"""

import json
import os
import logging
import re
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

_LAYOUT_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,120}$")


def _require_safe_layout_token(name: str, value: str) -> None:
    if not value or not _LAYOUT_TOKEN_RE.match(value):
        raise HTTPException(
            400,
            f"Invalid {name}: {value!r} (allowed: [A-Za-z0-9][A-Za-z0-9_.-]{{0,120}})",
        )


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

    protocol = getattr(request, "protocol", "JOB")

    # Protocol contracts:
    # - JOB: UI job output only (results/jobs/<job_id>/)
    # - MINI_LAB_WEEK: single canonical mini_week run (optional output_parent+label bridge)
    # - MINI_LAB_WALK_FORWARD: canonical 2-split OOS campaign under results/labs/mini_week/<output_parent>/
    if protocol == "MINI_LAB_WEEK":
        if request.trading_mode != "AGGRESSIVE":
            raise HTTPException(400, "protocol=MINI_LAB_WEEK requires trading_mode=AGGRESSIVE")
        if sorted({x.strip().upper() for x in request.trade_types}) != ["DAILY", "SCALP"]:
            raise HTTPException(400, "protocol=MINI_LAB_WEEK requires trade_types=['DAILY','SCALP']")

        if getattr(request, "label_prefix", None) is not None:
            raise HTTPException(400, "label_prefix is only supported for protocol=MINI_LAB_WALK_FORWARD")

        # Optional canonical mini-week layout targeting: must specify both fields together.
        op = getattr(request, "output_parent", None)
        lb = getattr(request, "label", None)
        if (op is None) != (lb is None):
            raise HTTPException(400, "protocol=MINI_LAB_WEEK requires output_parent and label together (or neither)")
        if op is not None:
            _require_safe_layout_token("output_parent", str(op))
            _require_safe_layout_token("label", str(lb))

    elif protocol == "MINI_LAB_WALK_FORWARD":
        if request.trading_mode != "AGGRESSIVE":
            raise HTTPException(400, "protocol=MINI_LAB_WALK_FORWARD requires trading_mode=AGGRESSIVE")
        if sorted({x.strip().upper() for x in request.trade_types}) != ["DAILY", "SCALP"]:
            raise HTTPException(400, "protocol=MINI_LAB_WALK_FORWARD requires trade_types=['DAILY','SCALP']")

        # Walk-forward plan requires at least 8 calendar days (inclusive).
        days_inclusive = (end - start).days + 1
        if days_inclusive < 8:
            raise HTTPException(400, f"protocol=MINI_LAB_WALK_FORWARD requires >= 8 days (inclusive), got {days_inclusive}")

        op = getattr(request, "output_parent", None)
        if not op:
            raise HTTPException(400, "protocol=MINI_LAB_WALK_FORWARD requires output_parent")
        _require_safe_layout_token("output_parent", str(op))

        if getattr(request, "label", None) is not None:
            raise HTTPException(400, "protocol=MINI_LAB_WALK_FORWARD does not accept label (labels are generated)")

        lp = getattr(request, "label_prefix", None)
        if lp is not None:
            _require_safe_layout_token("label_prefix", str(lp))

    else:
        # Keep protocol=JOB simple and unambiguous: it always writes under results/jobs/<job_id>/.
        if getattr(request, "output_parent", None) is not None or getattr(request, "label", None) is not None:
            raise HTTPException(400, "output_parent/label are only supported for protocol=MINI_LAB_WEEK")
        if getattr(request, "label_prefix", None) is not None:
            raise HTTPException(400, "label_prefix is only supported for protocol=MINI_LAB_WALK_FORWARD")

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

    download_urls = {
        name: f"/api/backtests/{job_id}/download?file={filename}"
        for name, filename in (status.artifact_paths or {}).items()
    }

    # Optional: if a walk-forward job wrote `campaign_pointer.json`, expose a cockpit-friendly
    # `campaign` block so the UI can discover canonical paths without downloading/parsing the file.
    campaign = None
    try:
        job_dir = get_job_dir(job_id)
        pointer_path = assert_safe_job_file(job_dir, "campaign_pointer.json")
        if pointer_path.is_file():
            raw = pointer_path.read_text(encoding="utf-8")
            pointer = json.loads(raw)

            job_files: dict[str, str | None] = {"campaign_pointer": "campaign_pointer.json"}
            ja = pointer.get("job_artifacts")
            if isinstance(ja, dict):
                for k, v in ja.items():
                    if isinstance(k, str) and isinstance(v, str):
                        job_files[k] = v

            ap = status.artifact_paths or {}
            for k in ["walk_forward_campaign", "campaign_audit", "campaign_rollup"]:
                if not job_files.get(k) and isinstance(ap.get(k), str):
                    job_files[k] = ap.get(k)

            campaign_root = pointer.get("campaign_root") if isinstance(pointer.get("campaign_root"), str) else None
            root_path = Path(campaign_root) if campaign_root else None

            def _canon_path(key: str, filename: str) -> str | None:
                v = pointer.get(key)
                if isinstance(v, str) and v:
                    return v
                if root_path is not None:
                    cand = root_path / filename
                    if cand.is_file():
                        return str(cand)
                return None

            campaign = {
                "pointer_schema_version": pointer.get("schema_version"),
                "output_parent": pointer.get("output_parent"),
                "label_prefix": pointer.get("label_prefix"),
                "campaign_root": campaign_root,
                "walk_forward_campaign_path": _canon_path("walk_forward_campaign_path", "walk_forward_campaign.json"),
                "campaign_audit_path": _canon_path("campaign_audit_path", "campaign_audit.json"),
                "campaign_rollup_path": _canon_path("campaign_rollup_path", "campaign_rollup.json"),
                "job_files": job_files,
                "job_download_urls": {k: download_urls[k] for k in job_files.keys() if k in download_urls},
            }
    except Exception:
        # Best-effort only: do not fail the endpoint on pointer issues.
        campaign = None

    return {
        "job_id": job_id,
        "metrics": status.metrics,
        "artifact_paths": status.artifact_paths,
        "download_urls": download_urls,
        "campaign": campaign,
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
