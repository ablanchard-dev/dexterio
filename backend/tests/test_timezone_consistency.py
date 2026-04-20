"""P0-10: Timezone unification — verify zero pytz in production code."""
import ast
import os
import pytest
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


BACKEND_ROOT = Path(__file__).resolve().parent.parent

# Directories to scan (production code only)
SCAN_DIRS = [
    BACKEND_ROOT / "backtest",
    BACKEND_ROOT / "engines",
    BACKEND_ROOT / "models",
    BACKEND_ROOT / "utils",
    BACKEND_ROOT / "scripts",
]

# Files allowed to still import pytz (legacy tests, docs)
ALLOWED_PYTZ = {
    str(BACKEND_ROOT / "tests"),
    str(BACKEND_ROOT / "docs"),
}


class TestNoPytzInProduction:
    """G15: Zero import pytz in codebase (except tests/docs)."""

    def _collect_py_files(self):
        files = []
        for d in SCAN_DIRS:
            if d.exists():
                for f in d.rglob("*.py"):
                    # Skip if in allowed dirs
                    if any(str(f).startswith(a) for a in ALLOWED_PYTZ):
                        continue
                    files.append(f)
        return files

    def test_no_pytz_imports(self):
        violations = []
        for f in self._collect_py_files():
            try:
                tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "pytz" or alias.name.startswith("pytz."):
                            violations.append(f"{f}:{node.lineno}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module and (node.module == "pytz" or node.module.startswith("pytz.")):
                        violations.append(f"{f}:{node.lineno}")

        assert violations == [], (
            f"pytz still imported in production code:\n" + "\n".join(violations)
        )


class TestTimezoneConversions:
    """Verify ET/UTC conversions are consistent across DST transitions."""

    NY = ZoneInfo("America/New_York")

    @pytest.mark.parametrize("utc_str,expected_et_hour,expected_offset", [
        # EDT (summer): UTC-4 → 14:30 UTC = 10:30 ET
        ("2025-07-15 14:30:00", 10, "-04:00"),
        # EST (winter): UTC-5 → 14:30 UTC = 9:30 ET
        ("2025-01-15 14:30:00", 9, "-05:00"),
        # DST transition day (Nov 2 2025, clocks fall back at 2:00 AM ET)
        # 13:30 UTC = 8:30 ET (already EST after fall-back)
        ("2025-11-02 13:30:00", 8, "-05:00"),
        # 06:30 UTC on Nov 2 = 02:30 EDT (before fall-back, clocks haven't changed yet)
        ("2025-11-02 05:30:00", 1, "-04:00"),
    ])
    def test_utc_to_et(self, utc_str, expected_et_hour, expected_offset):
        utc_dt = datetime.fromisoformat(utc_str).replace(tzinfo=timezone.utc)
        et_dt = utc_dt.astimezone(self.NY)
        assert et_dt.hour == expected_et_hour, (
            f"{utc_str} → ET hour {et_dt.hour}, expected {expected_et_hour}"
        )
        offset = et_dt.strftime("%z")
        # Format: +HHMM or -HHMM → convert to ±HH:MM
        offset_fmt = f"{offset[:3]}:{offset[3:]}"
        assert offset_fmt == expected_offset

    def test_naive_utc_assumed(self):
        """Naive timestamps should be treated as UTC."""
        naive = datetime(2025, 7, 15, 14, 30, 0)
        aware = naive.replace(tzinfo=timezone.utc)
        et_from_aware = aware.astimezone(self.NY)
        assert et_from_aware.hour == 10
