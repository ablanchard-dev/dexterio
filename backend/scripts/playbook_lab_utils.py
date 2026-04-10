"""Utilitaires Gate 3: agrégation labo full-playbooks et sélection Wave 1."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List
import json
import yaml


@dataclass
class PlaybookAggregate:
    playbook: str
    trades: int = 0
    wins: int = 0
    losses: int = 0
    total_r_net: float = 0.0
    gross_profit_r: float = 0.0
    gross_loss_r: float = 0.0
    windows: int = 0
    win_windows: int = 0
    avg_winrate: float = 0.0

    def add_window_row(self, row: Dict[str, Any]) -> None:
        self.windows += 1
        trades = int(row.get("trades", 0) or 0)
        wins = int(row.get("wins", 0) or 0)
        losses = int(row.get("losses", 0) or 0)
        total_r = float(row.get("total_r", 0.0) or 0.0)
        pf_r_profit = float(row.get("gross_profit_r", 0.0) or 0.0)
        pf_r_loss = float(row.get("gross_loss_r", 0.0) or 0.0)
        winrate = float(row.get("winrate", 0.0) or 0.0)
        if total_r > 0:
            self.win_windows += 1

        self.trades += trades
        self.wins += wins
        self.losses += losses
        self.total_r_net += total_r
        self.gross_profit_r += pf_r_profit
        self.gross_loss_r += pf_r_loss
        self.avg_winrate += winrate

    def finalize(self) -> Dict[str, Any]:
        avg_winrate = self.avg_winrate / self.windows if self.windows else 0.0
        abs_loss = abs(self.gross_loss_r)
        profit_factor = (
            self.gross_profit_r / abs_loss
            if abs_loss > 0
            else (float("inf") if self.gross_profit_r > 0 else 0.0)
        )
        stability = self.win_windows / self.windows if self.windows else 0.0
        expectancy_r = (self.total_r_net / self.trades) if self.trades else 0.0
        return {
            "playbook": self.playbook,
            "trades": self.trades,
            "wins": self.wins,
            "losses": self.losses,
            "winrate": avg_winrate,
            "total_r_net": self.total_r_net,
            "expectancy_r": expectancy_r,
            "profit_factor": profit_factor,
            "windows": self.windows,
            "win_windows": self.win_windows,
            "stability_score": stability,
        }


def aggregate_playbook_stats(files: Iterable[Path]) -> List[Dict[str, Any]]:
    by_pb: Dict[str, PlaybookAggregate] = {}
    for fp in files:
        with fp.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        if not isinstance(payload, dict):
            continue
        for playbook, row in payload.items():
            if playbook not in by_pb:
                by_pb[playbook] = PlaybookAggregate(playbook=playbook)
            by_pb[playbook].add_window_row(row if isinstance(row, dict) else {})
    agg = [v.finalize() for v in by_pb.values()]
    agg.sort(key=lambda x: (x["total_r_net"], x["profit_factor"], x["trades"]), reverse=True)
    for i, row in enumerate(agg, start=1):
        row["rank"] = i
    return agg


def select_wave1_candidates(
    leaderboard: List[Dict[str, Any]],
    top_n: int = 8,
    min_trades: int = 25,
    min_pf: float = 1.0,
    *,
    min_stability_score: float = 0.0,
    min_expectancy_r: float = 0.0,
    min_total_r_net: float = 0.0,
) -> List[Dict[str, Any]]:
    """
    Filtre Wave 1. Pour resserrer sans ML : exiger stabilité multi-fenêtres + espérance R + R net minimum.

    - min_stability_score: part des fenêtres mensuelles avec total_r > 0 (0–1).
    - min_expectancy_r: total_r_net / trades sur l'agrégat.
    """
    kept: List[Dict[str, Any]] = []
    for x in leaderboard:
        if int(x.get("trades", 0)) < min_trades:
            continue
        if float(x.get("profit_factor", 0.0)) <= min_pf:
            continue
        if float(x.get("stability_score", 0.0)) < min_stability_score:
            continue
        ex = float(x.get("expectancy_r", 0.0))
        if ex < min_expectancy_r:
            continue
        if float(x.get("total_r_net", 0.0)) < min_total_r_net:
            continue
        kept.append(x)
    kept = kept[: max(1, top_n)]
    for i, row in enumerate(kept, start=1):
        row["wave1_rank"] = i
    return kept


def write_wave1_yaml(
    candidates: List[Dict[str, Any]],
    output_file: Path,
    period_start: str,
    period_end: str,
    selection_mode: str = "aggressive_total_r_net",
) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "wave": "paper_wave1",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "selection_mode": selection_mode,
        "period": {"start": period_start, "end": period_end},
        "playbooks": [
            {
                "name": x["playbook"],
                "rank": x["wave1_rank"],
                "metrics": {
                    "trades": x["trades"],
                    "winrate": x["winrate"],
                    "profit_factor": x["profit_factor"],
                    "total_r_net": x["total_r_net"],
                    "expectancy_r": x.get("expectancy_r"),
                    "stability_score": x["stability_score"],
                },
            }
            for x in candidates
        ],
    }
    with output_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=False)

