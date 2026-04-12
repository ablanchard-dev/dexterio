"""
Preflight paper supervisé — discipline type Freqtrade « config figée » + CORE_PAPER_NOW.

Vérifie : dépôt Git, SHA courant, working tree (propre ou non), présence .venv optionnelle.
Ne touche pas au moteur, NY, NF, Wave 2.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class PreflightResult:
    repo_root: Path
    git_sha: str
    dirty_paths: Tuple[str, ...]
    venv_python: Optional[Path]

    @property
    def is_clean(self) -> bool:
        return len(self.dirty_paths) == 0

    def warnings(self) -> List[str]:
        out: List[str] = []
        if not self.is_clean:
            out.append(
                f"working tree non propre ({len(self.dirty_paths)} chemins) — "
                "voir CORE_PAPER_NOW_LAUNCH.md préchecks ; le manifest du run devrait quand même enregistrer git_sha."
            )
        if self.venv_python is None or not self.venv_python.is_file():
            out.append(
                "backend/.venv/bin/python introuvable — activer le venv attendu pour reproductibilité."
            )
        return out


def find_repo_root(start: Path) -> Optional[Path]:
    cur = start.resolve()
    for _ in range(20):
        if (cur / ".git").is_dir() or (cur / ".git").is_file():
            return cur
        if cur.parent == cur:
            return None
        cur = cur.parent
    return None


def _run_git(args: List[str], cwd: Path) -> str:
    return subprocess.check_output(["git", *args], cwd=str(cwd), text=True, stderr=subprocess.DEVNULL).strip()


def collect_preflight(
    cwd: Optional[Path] = None,
    *,
    backend_dir: Optional[Path] = None,
) -> PreflightResult:
    """
    cwd: répertoire de départ pour remonter jusqu'au .git (défaut : cwd process).
    backend_dir: racine backend pour .venv (défaut : repo_root / 'backend').
    """
    start = (cwd or Path.cwd()).resolve()
    root = find_repo_root(start)
    if root is None:
        raise RuntimeError(f"aucun dépôt Git trouvé depuis {start}")

    sha = _run_git(["rev-parse", "HEAD"], root)
    porcelain = _run_git(["status", "--porcelain"], root)
    dirty = tuple(line for line in porcelain.splitlines() if line.strip())

    bdir = (backend_dir if backend_dir is not None else root / "backend").resolve()
    vpy = bdir / ".venv" / "bin" / "python"
    venv = vpy if vpy.is_file() else None

    return PreflightResult(repo_root=root, git_sha=sha, dirty_paths=dirty, venv_python=venv)
