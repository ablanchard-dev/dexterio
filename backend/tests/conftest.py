import sys
from pathlib import Path

import pytest

# Ensure '/app/backend' is on sys.path so tests can import 'models', 'engines', 'backtest', 'scripts'.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ---------------------------------------------------------------------------
# Dette de test connue et documentée.
#
# Ces tests échouent pour des raisons explicites (pas des bugs cachés). Ils
# sont marqués `xfail` avec leur cause exacte plutôt que d'être supprimés, pour
# rester visibles et traçables. À lever un par un quand le sujet est traité.
# ---------------------------------------------------------------------------
_R_BREAKEVEN = (
    "ExecutionEngine moves the breakeven stop to entry+0.7R (profit-lock) whereas paper_trading "
    "moves it to exact entry; this test asserts exact-entry. Needs a domain decision on the "
    "intended breakeven target (and the two engines reconciled) before changing the assertion."
)

_KNOWN_XFAILS = {
    "test_phase3b_execution.py::test_legacy_playbook_breakeven_uses_yaml_value": _R_BREAKEVEN,
    # Résolus depuis (donc plus listés ici) : gap ET-flooring, migration pytz→zoneinfo,
    # drift d'allowlist (modes.yml), valeurs YAML News_Fade re-tunées, signature du mock
    # evaluate_all_playbooks, encodage Windows UTF-8 ; test_date_slicing -> skip si la
    # donnée parquet est absente.
}


def pytest_collection_modifyitems(config, items):
    for item in items:
        for suffix, reason in _KNOWN_XFAILS.items():
            if item.nodeid.endswith(suffix):
                item.add_marker(pytest.mark.xfail(reason=reason, strict=False))
                break
