"""Top-level 'scripts' package.

This repository stores executable scripts under /app/backend/scripts.
User workflows expect to run:
  python -m scripts.<module>
from the repo root (/app).

To make that work without moving files, we extend this package's module search
path to include /app/backend/scripts.
"""

from __future__ import annotations

from pathlib import Path

# Extend package path to also look inside backend/scripts
_BACKEND_SCRIPTS = Path(__file__).resolve().parents[1] / "backend" / "scripts"
if _BACKEND_SCRIPTS.exists():
    # __path__ is defined by Python for packages.
    __path__.append(str(_BACKEND_SCRIPTS))  # type: ignore[name-defined]
