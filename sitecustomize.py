"""Repository convenience: make /app/backend importable as a top-level module path.

This enables running CLI modules like:
  python -m scripts.download_intraday_windowed ...
from the repo root (/app) without needing to set PYTHONPATH manually.

It is intentionally minimal and only affects module resolution.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent / "backend"
if BACKEND_DIR.exists() and str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
