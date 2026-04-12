from __future__ import annotations

import pandas as pd
import pytest

from backtest.trade_parquet_analysis import summarize_trades_parquet


def test_summarize_empty_playbook_filter(tmp_path) -> None:
    df = pd.DataFrame(
        {
            "playbook": ["News_Fade", "News_Fade"],
            "outcome": ["win", "loss"],
            "r_multiple": [1.0, -1.0],
        }
    )
    p = tmp_path / "t.parquet"
    df.to_parquet(p, index=False)
    s = summarize_trades_parquet(p, playbook="News_Fade")
    assert s["trades"] == 2
    assert s["sum_r"] == 0.0
    assert abs(s["expectancy_r"]) < 1e-9
