"""Validation chemins et identifiants pour l'API jobs."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import HTTPException, status

# Job IDs générés par backtest_jobs (8 premiers caractères d'un UUID hex)
_JOB_ID_RE = re.compile(r"^[a-f0-9]{8}$")


def validate_job_id(job_id: str) -> str:
    if not job_id or not _JOB_ID_RE.match(job_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job id",
        )
    return job_id


def assert_safe_job_file(job_dir: Path, file_name: str) -> Path:
    """
    Retourne le chemin résolu du fichier sous job_dir, ou lève 400 si hors racine.
    Bloque .., chemins absolus détournés, et noms suspects.
    """
    if not file_name or file_name.strip() != file_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename")
    if ".." in file_name or "/" in file_name or "\\" in file_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename")
    if file_name.startswith("."):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename")

    root = job_dir.resolve()
    candidate = (root / file_name).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename")
    return candidate
