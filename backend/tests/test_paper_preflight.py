"""Tests preflight paper (Git + venv) — sans modifier le moteur."""
from __future__ import annotations

from pathlib import Path

import pytest

from utils.paper_preflight import collect_preflight, find_repo_root

_BACKEND = Path(__file__).resolve().parent.parent
_REPO = _BACKEND.parent


def test_find_repo_root_from_backend() -> None:
    r = find_repo_root(_BACKEND)
    assert r is not None
    assert (r / ".git").exists()


def test_collect_preflight_from_backend_dir() -> None:
    r = collect_preflight(cwd=_BACKEND)
    assert len(r.git_sha) == 40
    assert r.repo_root == _REPO.resolve()


@pytest.mark.skipif(
    not (_BACKEND / ".venv" / "bin" / "python").is_file(),
    reason=".venv absent sur cette machine CI",
)
def test_venv_detected_when_present() -> None:
    r = collect_preflight(cwd=_BACKEND)
    assert r.venv_python is not None
    assert r.venv_python.is_file()
