"""
Snapshot des variables d'environnement pertinentes pour reproductibilité lab / paper.

Inspiré de la discipline Freqtrade (config explicite, séparation dry-run / prod) :
on fige dans le manifest ce qui pilote RiskEngine / mini-lab sans importer Freqtrade.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

_RISK_KEYS: List[str] = [
    "RISK_EVAL_ALLOW_ALL_PLAYBOOKS",
    "RISK_EVAL_RELAX_CAPS",
    "RISK_EVAL_DISABLE_KILL_SWITCH",
    "RISK_BYPASS_DYNAMIC_QUARANTINE_LSS_ONLY",
]


def snapshot_risk_lab_environment(*, extra_keys: Optional[List[str]] = None) -> Dict[str, Any]:
    """Valeurs courantes (ou null si absentes) — sérialisable JSON."""
    keys = list(_RISK_KEYS)
    if extra_keys:
        keys.extend(k for k in extra_keys if k not in keys)
    return {k: os.environ.get(k) for k in keys}
