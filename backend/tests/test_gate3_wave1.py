import json
from pathlib import Path

from scripts.playbook_lab_utils import (
    aggregate_playbook_stats,
    select_wave1_candidates,
    write_wave1_yaml,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_aggregate_and_rank_is_deterministic(tmp_path: Path):
    f1 = tmp_path / "playbook_stats_labfull_202501.json"
    f2 = tmp_path / "playbook_stats_labfull_202502.json"

    _write_json(
        f1,
        {
            "PB_A": {"trades": 10, "wins": 6, "losses": 4, "total_r": 4.0, "gross_profit_r": 7.0, "gross_loss_r": -3.0, "winrate": 0.6},
            "PB_B": {"trades": 10, "wins": 5, "losses": 5, "total_r": 1.0, "gross_profit_r": 4.0, "gross_loss_r": -3.0, "winrate": 0.5},
        },
    )
    _write_json(
        f2,
        {
            "PB_A": {"trades": 10, "wins": 5, "losses": 5, "total_r": 2.0, "gross_profit_r": 5.0, "gross_loss_r": -3.0, "winrate": 0.5},
            "PB_B": {"trades": 10, "wins": 4, "losses": 6, "total_r": -1.0, "gross_profit_r": 3.0, "gross_loss_r": -4.0, "winrate": 0.4},
        },
    )

    rows1 = aggregate_playbook_stats([f1, f2])
    rows2 = aggregate_playbook_stats([f1, f2])

    assert [r["playbook"] for r in rows1] == [r["playbook"] for r in rows2]
    assert rows1[0]["playbook"] == "PB_A"
    assert rows1[0]["rank"] == 1


def test_wave1_generation_with_guardrails(tmp_path: Path):
    leaderboard = [
        {"playbook": "PB_A", "trades": 40, "profit_factor": 1.5, "total_r_net": 8.0, "winrate": 0.55, "stability_score": 0.8, "expectancy_r": 0.2},
        {"playbook": "PB_B", "trades": 8, "profit_factor": 2.5, "total_r_net": 7.0, "winrate": 0.6, "stability_score": 0.9, "expectancy_r": 0.875},
        {"playbook": "PB_C", "trades": 35, "profit_factor": 0.9, "total_r_net": 6.0, "winrate": 0.5, "stability_score": 0.7, "expectancy_r": 6.0 / 35},
    ]
    candidates = select_wave1_candidates(leaderboard, top_n=2, min_trades=20, min_pf=1.0)
    assert len(candidates) == 1
    assert candidates[0]["playbook"] == "PB_A"
    assert candidates[0]["wave1_rank"] == 1

    out = tmp_path / "paper_wave1_playbooks.yaml"
    write_wave1_yaml(candidates, out, "2024-01-01", "2025-12-31")
    content = out.read_text(encoding="utf-8")
    assert "paper_wave1" in content
    assert "PB_A" in content


def test_wave1_tight_stability_excludes_inconsistent_playbook():
    leaderboard = [
        {
            "playbook": "Stable",
            "trades": 30,
            "profit_factor": 1.2,
            "total_r_net": 6.0,
            "stability_score": 0.5,
            "expectancy_r": 0.2,
        },
        {
            "playbook": "Lucky_spike",
            "trades": 30,
            "profit_factor": 1.25,
            "total_r_net": 10.0,
            "stability_score": 0.15,
            "expectancy_r": 10.0 / 30,
        },
    ]
    loose = select_wave1_candidates(leaderboard, top_n=5, min_trades=25, min_pf=1.0)
    assert len(loose) == 2
    tight = select_wave1_candidates(
        leaderboard,
        top_n=5,
        min_trades=25,
        min_pf=1.0,
        min_stability_score=0.35,
    )
    assert len(tight) == 1
    assert tight[0]["playbook"] == "Stable"

