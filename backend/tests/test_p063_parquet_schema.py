import pandas as pd
import pytz

from scripts.quality_gates import normalize_datetime_to_utc, run_quality_gates


def test_parquet_schema_roundtrip(tmp_path):
    df = pd.DataFrame(
        {
            "datetime": [
                pd.Timestamp("2025-11-03 14:30:00", tz=pytz.UTC),
                pd.Timestamp("2025-11-03 14:31:00", tz=pytz.UTC),
            ],
            "open": [1.0, 1.1],
            "high": [1.2, 1.3],
            "low": [0.9, 1.0],
            "close": [1.1, 1.2],
            "volume": [100, 200],
        }
    )

    df2 = normalize_datetime_to_utc(df)
    report = run_quality_gates(
        df2,
        symbol="SPY",
        start=pd.Timestamp("2025-11-03").date(),
        end=pd.Timestamp("2025-11-04").date(),
    )
    assert "gates" in report

    out = tmp_path / "SPY.parquet"
    df2.to_parquet(out, index=False)

    loaded = pd.read_parquet(out)
    assert set(loaded.columns) == {"datetime", "open", "high", "low", "close", "volume"}
    assert len(loaded) == 2
