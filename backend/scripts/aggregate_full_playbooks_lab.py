"""Gate 3: agrégation labo 24m + leaderboard + candidats Wave 1."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from scripts.playbook_lab_utils import (  # noqa: E402
    aggregate_playbook_stats,
    select_wave1_candidates,
    write_wave1_yaml,
)
from utils.path_resolver import results_path  # noqa: E402


def _load_index(index_file: Path) -> Dict[str, Any]:
    with index_file.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aggregate full playbooks lab outputs",
        epilog=(
            "Preset « strict » : resserre PF, trades, stabilité multi-fenêtres et espérance R "
            "(adapté après plusieurs mois de labo). Exemple manuel : "
            "--min-stability 0.4 --min-expectancy-r 0.05 --min-pf 1.15"
        ),
    )
    parser.add_argument("--top-n", type=int, default=8)
    parser.add_argument("--min-trades", type=int, default=25)
    parser.add_argument("--min-pf", type=float, default=1.0)
    parser.add_argument(
        "--min-stability",
        type=float,
        default=0.0,
        help="Part min. de fenêtres avec R>0 (0-1), ex. 0.35",
    )
    parser.add_argument(
        "--min-expectancy-r",
        type=float,
        default=0.0,
        help="Espérance R min. (total_r_net / trades agrégés)",
    )
    parser.add_argument(
        "--min-total-r-net",
        type=float,
        default=0.0,
        help="R net cumulé minimal sur toute la période agrégée",
    )
    parser.add_argument(
        "--preset",
        choices=("default", "strict"),
        default="default",
        help="strict = seuils plus durs (voir code) pour Wave 1 conservative",
    )
    args = parser.parse_args()

    if args.preset == "strict":
        top_n = min(args.top_n, 5)
        min_trades = max(args.min_trades, 40)
        min_pf = max(args.min_pf, 1.12)
        min_stability = max(args.min_stability, 0.35)
        min_expectancy_r = max(args.min_expectancy_r, 0.04)
        min_total_r_net = max(args.min_total_r_net, 3.0)
    else:
        top_n = args.top_n
        min_trades = args.min_trades
        min_pf = args.min_pf
        min_stability = args.min_stability
        min_expectancy_r = args.min_expectancy_r
        min_total_r_net = args.min_total_r_net

    lab_dir = results_path("labs", "full_playbooks_24m")
    index_file = lab_dir / "lab_windows_index.json"
    if not index_file.exists():
        raise FileNotFoundError(f"Index labo introuvable: {index_file}")

    idx = _load_index(index_file)
    files: List[Path] = []
    for w in idx.get("windows", []):
        p = Path(w.get("playbook_stats_file", ""))
        if p.exists():
            files.append(p)
    if not files:
        raise RuntimeError("Aucun playbook_stats trouvé pour l'agrégation Gate 3")

    leaderboard = aggregate_playbook_stats(files)
    candidates = select_wave1_candidates(
        leaderboard=leaderboard,
        top_n=top_n,
        min_trades=min_trades,
        min_pf=min_pf,
        min_stability_score=min_stability,
        min_expectancy_r=min_expectancy_r,
        min_total_r_net=min_total_r_net,
    )

    results_dir = results_path()
    results_dir.mkdir(parents=True, exist_ok=True)
    leaderboard_file = results_dir / "playbooks_leaderboard_24m.json"
    candidates_file = results_dir / "playbooks_wave1_candidates.json"
    with leaderboard_file.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "windows_count": len(files),
                "rows": leaderboard,
            },
            f,
            indent=2,
        )
    with candidates_file.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "top_n": top_n,
                "preset": args.preset,
                "min_trades": min_trades,
                "min_pf": min_pf,
                "min_stability": min_stability,
                "min_expectancy_r": min_expectancy_r,
                "min_total_r_net": min_total_r_net,
                "rows": candidates,
            },
            f,
            indent=2,
        )

    windows = idx.get("windows", [])
    pstart = windows[0]["start"] if windows else ""
    pend = windows[-1]["end"] if windows else ""
    write_wave1_yaml(
        candidates=candidates,
        output_file=backend_dir / "knowledge" / "paper_wave1_playbooks.yaml",
        period_start=pstart,
        period_end=pend,
    )
    print(f"[gate3] leaderboard: {leaderboard_file}")
    print(f"[gate3] candidates: {candidates_file}")


if __name__ == "__main__":
    main()

