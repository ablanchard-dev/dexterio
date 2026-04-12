"""Découpage walk-forward minimal (calendrier uniquement — pas d’appel moteur)."""
from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd


def walk_forward_two_splits_expanding(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Deux fenêtres de test OOS disjointes, avec train **expanding**.

    Jours calendaires inclusifs [start_date, end_date]. Soit ``q = max(n // 4, 1)`` :

    - **split 0** : train indices ``[0, 2q)``, test ``[2q, 3q)``
    - **split 1** : train indices ``[0, 3q)``, test ``[3q, n)``

    Nécessite au moins 8 jours et ``3q <= n`` (sinon ValueError).
    """
    s = pd.Timestamp(start_date).normalize()
    e = pd.Timestamp(end_date).normalize()
    if e < s:
        raise ValueError("end_date doit être >= start_date")
    days = pd.date_range(s, e, freq="D")
    n = len(days)
    if n < 8:
        raise ValueError(f"au moins 8 jours requis, got {n}")

    q = max(n // 4, 1)
    if 3 * q > n:
        raise ValueError(f"découpe impossible: n={n}, q={q}")

    def _iso(i: int) -> str:
        return days[i].strftime("%Y-%m-%d")

    splits: List[Dict[str, Any]] = [
        {
            "id": 0,
            "train": {"start_date": _iso(0), "end_date": _iso(2 * q - 1)},
            "test": {"start_date": _iso(2 * q), "end_date": _iso(3 * q - 1)},
            "train_days": 2 * q,
            "test_days": q,
        },
        {
            "id": 1,
            "train": {"start_date": _iso(0), "end_date": _iso(3 * q - 1)},
            "test": {"start_date": _iso(3 * q), "end_date": _iso(n - 1)},
            "train_days": 3 * q,
            "test_days": n - 3 * q,
        },
    ]

    return {
        "schema_version": "WalkForwardLightV0",
        "start_date": s.strftime("%Y-%m-%d"),
        "end_date": e.strftime("%Y-%m-%d"),
        "calendar_days": n,
        "q_calendar_blocks": q,
        "splits": splits,
        "note": "Train/test en jours calendaires (minuit UTC) — dates inclusives pour enchaîner run_mini_lab_week / backtest.",
    }
