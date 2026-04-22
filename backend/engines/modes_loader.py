"""Phase W.4 — load playbook mode constants from knowledge/modes.yml.

The loader is resilient by design: if the YAML file is missing, malformed, or
contains the wrong types, the caller gets a hardcoded fallback that mirrors
the pre-W.4 literal lists. This guarantees zero breaking change at boot.

Consumers:
- `risk_engine.py` reads `aggressive_allowlist` and `aggressive_denylist`.
- `execution/phase3b_execution.py` reads `phase3b_playbooks`.

Returning plain lists (not frozensets) so callers pick the data structure
that fits their use-site. `phase3b_execution.py` wraps in frozenset explicitly.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

# Snapshot of the pre-W.4 literal values. If YAML parsing fails for any reason
# we fall back to these so the engine boots with known-good defaults.
_FALLBACK_AGGRESSIVE_ALLOWLIST: List[str] = [
    "FVG_Fill_V065",
    "Range_FVG_V054",
    "Asia_Sweep_V051",
    "Engulfing_Bar_V056",
    "London_Fakeout_V066",
    "OB_Retest_V004",
    "FVG_Scalp_1m",
    "BOS_Scalp_1m",
    "EMA_Cross_5m",
    "VWAP_Bounce_5m",
    "RSI_MeanRev_5m",
    "News_Fade",
]

_FALLBACK_AGGRESSIVE_DENYLIST: List[str] = [
    "London_Sweep_NY_Continuation",
    "BOS_Momentum_Scalp",
    "Power_Hour_Expansion",
    "Lunch_Range_Scalp",
    "Trend_Continuation_FVG_Retest",
    "DAY_Aplus_1_Liquidity_Sweep_OB_Retest",
    "SCALP_Aplus_1_Mini_FVG_Retest_NY_Open",
    "NY_Open_Reversal",
    "ORB_Breakout_5m",
    "Liquidity_Raid_V056",
    "FVG_Fill_Scalp",
    "Session_Open_Scalp",
    "IFVG_5m_Sweep",
    "HTF_Bias_15m_BOS",
    "Morning_Trap_Reversal",
    "Liquidity_Sweep_Scalp",
]

_FALLBACK_PHASE3B_PLAYBOOKS: List[str] = [
    "NY_Open_Reversal",
    "News_Fade",
    "Liquidity_Sweep_Scalp",
    "BOS_Scalp_1m",
]

_YAML_PATH = Path(__file__).resolve().parent.parent / "knowledge" / "modes.yml"

_cache: Optional[Dict[str, List[str]]] = None


def _default_lists() -> Dict[str, List[str]]:
    return {
        "aggressive_allowlist": list(_FALLBACK_AGGRESSIVE_ALLOWLIST),
        "aggressive_denylist": list(_FALLBACK_AGGRESSIVE_DENYLIST),
        "phase3b_playbooks": list(_FALLBACK_PHASE3B_PLAYBOOKS),
    }


def _load() -> Dict[str, List[str]]:
    global _cache
    if _cache is not None:
        return _cache

    if not _YAML_PATH.exists():
        logger.warning(
            f"[modes_loader] {_YAML_PATH} missing — using hardcoded fallbacks."
        )
        _cache = _default_lists()
        return _cache

    try:
        with open(_YAML_PATH, "r") as f:
            data = yaml.safe_load(f) or {}
    except Exception as exc:
        logger.error(
            f"[modes_loader] parse error on {_YAML_PATH}: {exc} — falling back."
        )
        _cache = _default_lists()
        return _cache

    result = _default_lists()
    for key in ("aggressive_allowlist", "aggressive_denylist", "phase3b_playbooks"):
        value = data.get(key)
        if isinstance(value, list) and all(isinstance(x, str) for x in value):
            result[key] = list(value)
        else:
            logger.warning(
                f"[modes_loader] key '{key}' missing or malformed in {_YAML_PATH.name}; "
                f"using fallback."
            )

    _cache = result
    return _cache


def get_aggressive_allowlist() -> List[str]:
    return list(_load()["aggressive_allowlist"])


def get_aggressive_denylist() -> List[str]:
    return list(_load()["aggressive_denylist"])


def get_phase3b_playbooks() -> List[str]:
    return list(_load()["phase3b_playbooks"])


def reset_cache() -> None:
    """Test hook — force the next call to re-read the YAML."""
    global _cache
    _cache = None
