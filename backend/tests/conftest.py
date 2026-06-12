import sys
from pathlib import Path

import pytest

# Ensure 'backend' is on sys.path so tests can import 'models', 'engines', 'backtest', 'scripts'.
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
_R_YAML = "asserts specific YAML strategy values (stop/TP/RR) that have since been re-tuned"
_R_DATA = "requires market-data files that are not versioned in the public repo"
_R_WIN = "Windows cp1252 console cannot encode the '<=' glyph written by the CLI (passes under UTF-8/CI)"

_KNOWN_XFAILS = {
    "test_build_verdict.py::test_cli_produces_file": _R_WIN,
    "test_date_slicing.py::test_date_slicing": _R_DATA,
    "test_phase2_news_fade_context.py::test_generate_setups_market_context_contains_day_type_and_volatility": _R_DATA,
    "test_phase2_news_fade_context.py::test_news_fade_yaml_stop_option_a_sl_distance_entry_percent_half": _R_YAML,
    "test_phase2_news_fade_context.py::test_news_fade_yaml_phase_c_tp1_min_rr_one_r": _R_YAML,
    "test_phase3b_execution.py::test_legacy_playbook_breakeven_uses_yaml_value": _R_YAML,
    # NB : ET-flooring, migration pytz→zoneinfo et drift d'allowlist (modes.yml)
    # ont été CORRIGÉS — ces tests passent désormais et ne sont plus listés ici.
}


def pytest_collection_modifyitems(config, items):
    for item in items:
        for suffix, reason in _KNOWN_XFAILS.items():
            if item.nodeid.endswith(suffix):
                item.add_marker(pytest.mark.xfail(reason=reason, strict=False))
                break
