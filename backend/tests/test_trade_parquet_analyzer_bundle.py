"""Registre analyzers post-parquet."""
from __future__ import annotations

import pandas as pd
import pytest

from backtest.trade_parquet_analyzer_bundle import (
    ANALYZER_REGISTRY,
    list_analyzers,
    run_parquet_analyzer_bundle,
)
from backtest.trade_parquet_analysis import summarize_trades_parquet


def test_bundle_summary_matches_standalone(tmp_path) -> None:
    df = pd.DataFrame(
        {
            "playbook": ["News_Fade", "X"],
            "outcome": ["win", "loss"],
            "r_multiple": [1.0, -1.0],
            "exit_reason": ["TP1", "SL"],
        }
    )
    p = tmp_path / "t.parquet"
    df.to_parquet(p, index=False)
    bundle = run_parquet_analyzer_bundle(p, names=["summary_r"])
    solo = summarize_trades_parquet(p)
    assert bundle["results"]["summary_r"] == solo


def test_bundle_filtered_playbook(tmp_path) -> None:
    df = pd.DataFrame(
        {
            "playbook": ["News_Fade", "News_Fade"],
            "outcome": ["win", "win"],
            "r_multiple": [0.5, 0.5],
            "exit_reason": ["session_end", "TP1"],
        }
    )
    p = tmp_path / "t.parquet"
    df.to_parquet(p, index=False)
    out = run_parquet_analyzer_bundle(p, playbook="News_Fade", names=["exit_reason_mix"])
    counts = out["results"]["exit_reason_mix"]["exit_reason_counts"]
    assert counts.get("session_end") == 1 and counts.get("TP1") == 1


def test_playbook_counts_global(tmp_path) -> None:
    df = pd.DataFrame(
        {
            "playbook": ["A", "A", "B"],
            "outcome": ["win", "win", "loss"],
            "r_multiple": [1.0, 1.0, -1.0],
            "exit_reason": ["TP1", "TP1", "SL"],
        }
    )
    p = tmp_path / "t.parquet"
    df.to_parquet(p, index=False)
    out = run_parquet_analyzer_bundle(p, playbook="A", names=["playbook_counts"])
    pc = out["results"]["playbook_counts"]["playbook_counts"]
    assert pc.get("A") == 2 and pc.get("B") == 1


def test_unknown_analyzer_raises(tmp_path) -> None:
    p = tmp_path / "empty.parquet"
    pd.DataFrame({"playbook": [], "outcome": [], "r_multiple": [], "exit_reason": []}).to_parquet(
        p, index=False
    )
    with pytest.raises(KeyError, match="nope"):
        run_parquet_analyzer_bundle(p, names=["nope"])


def test_list_analyzers_covers_registry() -> None:
    assert set(list_analyzers()) == set(ANALYZER_REGISTRY.keys())
