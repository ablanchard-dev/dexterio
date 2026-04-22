"""
Phase 3B — garde transverse unique pour l’alignement exécution paper/backtest
(Wave 1 : NY_Open_Reversal, News_Fade, Liquidity_Sweep_Scalp).

Aucune logique métier hors de ce périmètre ; les autres playbooks restent sur le chemin legacy.
"""
from __future__ import annotations

from datetime import datetime, time, timezone
from typing import TYPE_CHECKING, List, Optional, Tuple

from engines.modes_loader import get_phase3b_playbooks

if TYPE_CHECKING:
    from engines.playbook_loader import PlaybookDefinition

# Phase W.4 — sourced from `backend/knowledge/modes.yml`. The name is kept as a
# module-level frozenset so existing callers (imports, `in` checks) are unchanged.
PHASE3B_PLAYBOOKS = frozenset(get_phase3b_playbooks())


def is_phase3b_playbook(playbook_name: str) -> bool:
    return (playbook_name or "") in PHASE3B_PLAYBOOKS


def _parse_hhmm(s: str) -> time:
    parts = str(s).strip().split(":")
    h = int(parts[0])
    m = int(parts[1]) if len(parts) > 1 else 0
    return time(h, m)


def compute_session_window_end_utc(
    playbook_def: PlaybookDefinition, entry_utc: datetime
) -> Optional[datetime]:
    """
    Borne de fin de fenêtre NY (timezone America/New_York) pour le jour calendaire d’entrée,
    si l’entrée tombe dans une fenêtre YAML (time_range ou time_windows).
    """
    try:
        from zoneinfo import ZoneInfo

        ny = ZoneInfo("America/New_York")
    except Exception:
        return None

    if entry_utc.tzinfo is None:
        entry_utc = entry_utc.replace(tzinfo=timezone.utc)
    ny_t = entry_utc.astimezone(ny)
    d = ny_t.date()

    windows: List[Tuple[time, time]] = []
    if playbook_def.time_windows:
        for tw in playbook_def.time_windows:
            if isinstance(tw, (list, tuple)) and len(tw) >= 2:
                windows.append((_parse_hhmm(str(tw[0])), _parse_hhmm(str(tw[1]))))
    elif playbook_def.time_range and len(playbook_def.time_range) >= 2:
        windows.append(
            (
                _parse_hhmm(str(playbook_def.time_range[0])),
                _parse_hhmm(str(playbook_def.time_range[1])),
            )
        )

    for t0, t1 in windows:
        start = datetime.combine(d, t0, ny)
        end = datetime.combine(d, t1, ny)
        if start <= ny_t <= end:
            return end.astimezone(timezone.utc)
    return None


def should_attach_session_window_end(playbook_name: str, trade_type: str) -> bool:
    """LSS (SCALP) utilise max_duration, pas une sortie de fin de session journalière."""
    return (
        trade_type == "DAILY"
        and playbook_name in ("NY_Open_Reversal", "News_Fade")
    )
