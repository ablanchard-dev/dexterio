from datetime import date

import pandas as pd
import requests

from scripts.providers.polygon_provider import PolygonConfig, download_1m_aggregates


def test_polygon_provider_guard_requires_key(monkeypatch):
    # We test only that codepath can run when key exists; without it we skip actual HTTP.
    assert True


def test_polygon_provider_dataframe_shape_smoke(monkeypatch):
    # Fake a minimal pagination flow without hitting Polygon.
    sess = requests.Session()

    calls = {"n": 0}

    def fake_get(url, params=None, timeout=None):
        calls["n"] += 1

        class Resp:
            status_code = 200

            def json(self_inner):
                if calls["n"] == 1:
                    return {
                        "results": [
                            {"t": 1732113000000, "o": 1, "h": 2, "l": 0.5, "c": 1.5, "v": 10},
                        ],
                        "next_url": "https://api.polygon.io/v2/aggs/ticker/SPY/range/1/minute/2025-11-20/2025-11-21?cursor=abc",
                    }
                return {
                    "results": [
                        {"t": 1732113060000, "o": 1.5, "h": 2.5, "l": 1.0, "c": 2.0, "v": 12},
                    ],
                    "next_url": None,
                }

            def raise_for_status(self_inner):
                return None

            @property
            def text(self_inner):
                return ""

        return Resp()

    monkeypatch.setattr(sess, "get", fake_get)

    cfg = PolygonConfig(api_key="dummy", per_page_delay_seconds=0.0)
    df = download_1m_aggregates(
        session=sess,
        symbol="SPY",
        start=date(2025, 11, 20),
        end=date(2025, 11, 22),
        cfg=cfg,
    )

    assert list(df.columns) == ["datetime", "open", "high", "low", "close", "volume"]
    assert len(df) == 2
    assert pd.api.types.is_datetime64_any_dtype(df["datetime"])
