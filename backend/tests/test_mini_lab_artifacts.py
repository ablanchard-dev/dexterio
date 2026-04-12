from pathlib import Path

from utils.mini_lab_artifacts import trades_parquet_path


def test_trades_parquet_path_matches_engine_convention() -> None:
    p = trades_parquet_path(
        "/tmp/out",
        "miniweek_x_202509_w01",
        "AGGRESSIVE",
        ["DAILY", "SCALP"],
    )
    assert p == Path("/tmp/out") / "trades_miniweek_x_202509_w01_AGGRESSIVE_DAILY_SCALP.parquet"
