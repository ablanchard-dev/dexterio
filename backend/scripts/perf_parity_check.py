"""Sprint perf: checks de parité backtest <-> paper (config/runtime)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from config.settings import settings  # noqa: E402
from utils.path_resolver import results_path  # noqa: E402


def main() -> None:
    checks: List[Dict[str, Any]] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    add(
        "execution_backend_safe_default",
        settings.EXECUTION_BACKEND in {"paper", "ibkr"},
        f"EXECUTION_BACKEND={settings.EXECUTION_BACKEND}",
    )
    add(
        "live_disabled_for_perf_phase",
        not settings.LIVE_TRADING_ENABLED,
        f"LIVE_TRADING_ENABLED={settings.LIVE_TRADING_ENABLED}",
    )
    add(
        "paper_wave1_toggle_present",
        hasattr(settings, "PAPER_USE_WAVE1_PLAYBOOKS"),
        f"PAPER_USE_WAVE1_PLAYBOOKS={getattr(settings, 'PAPER_USE_WAVE1_PLAYBOOKS', None)}",
    )
    add(
        "data_feed_cache_reasonable",
        float(settings.DATA_FEED_CACHE_SECONDS) >= 10.0,
        f"DATA_FEED_CACHE_SECONDS={settings.DATA_FEED_CACHE_SECONDS}",
    )
    add(
        "trading_mode_defined",
        settings.TRADING_MODE in {"SAFE", "AGGRESSIVE"},
        f"TRADING_MODE={settings.TRADING_MODE}",
    )

    passed = all(c["passed"] for c in checks)
    payload = {"passed": passed, "checks": checks}
    out_file = results_path("perf_parity_check.json")
    out_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[perf] parity check: {out_file}")


if __name__ == "__main__":
    main()

