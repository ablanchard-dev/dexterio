"""P0-9: Data dedup + OHLCV validation pre-flight tests.

G14: No duplicate bars after load.
G16: OHLCV bounds respected (high >= low, price > 0).
"""
import pandas as pd
import pytest
from datetime import datetime, timezone


def _make_bars(n=5, symbol="SPY", start_hour=14, start_minute=30):
    """Create a clean DataFrame of n 1m bars."""
    rows = []
    for i in range(n):
        ts = datetime(2025, 7, 15, start_hour, start_minute + i, 0, tzinfo=timezone.utc)
        rows.append({
            "datetime": ts,
            "symbol": symbol,
            "open": 450.0 + i * 0.1,
            "high": 450.5 + i * 0.1,
            "low": 449.5 + i * 0.1,
            "close": 450.2 + i * 0.1,
            "volume": 1000 + i * 100,
        })
    return pd.DataFrame(rows)


class TestDedup:
    """G14: Dedup removes exact duplicate timestamps per symbol."""

    def test_dedup_drops_exact_duplicates(self):
        df = _make_bars(3)
        # Duplicate the second bar
        dup = df.iloc[[1]].copy()
        df_with_dups = pd.concat([df, dup], ignore_index=True)
        assert len(df_with_dups) == 4

        # Simulate the dedup logic from engine.py
        before = len(df_with_dups)
        subset_cols = ['datetime', 'symbol']
        df_clean = df_with_dups.drop_duplicates(subset=subset_cols, keep='first').reset_index(drop=True)
        assert len(df_clean) == 3
        assert before - len(df_clean) == 1

    def test_no_dedup_when_clean(self):
        df = _make_bars(5)
        before = len(df)
        df_clean = df.drop_duplicates(subset=['datetime', 'symbol'], keep='first')
        assert len(df_clean) == before

    def test_dedup_keeps_different_symbols(self):
        df1 = _make_bars(3, symbol="SPY")
        df2 = _make_bars(3, symbol="QQQ")
        df_combined = pd.concat([df1, df2], ignore_index=True)
        df_clean = df_combined.drop_duplicates(subset=['datetime', 'symbol'], keep='first')
        assert len(df_clean) == 6  # All kept — different symbols


class TestOHLCVBounds:
    """G16: OHLCV bounds respected."""

    def test_high_ge_low_swap(self):
        df = _make_bars(3)
        # Corrupt: swap high and low on row 1
        df.loc[1, 'high'] = 449.0
        df.loc[1, 'low'] = 451.0

        # Simulate the fix logic
        bad_hl = df['high'] < df['low']
        assert bad_hl.sum() == 1
        idx = df.loc[bad_hl].index
        h = df.loc[idx, 'high'].copy()
        df.loc[idx, 'high'] = df.loc[idx, 'low']
        df.loc[idx, 'low'] = h
        # Now high >= low everywhere
        assert (df['high'] >= df['low']).all()

    def test_price_positive(self):
        df = _make_bars(3)
        # Corrupt: negative price
        df.loc[0, 'open'] = -1.0

        price_cols = ['open', 'high', 'low', 'close']
        neg_mask = (df[price_cols] <= 0).any(axis=1)
        assert neg_mask.sum() == 1
        df_clean = df[~neg_mask].reset_index(drop=True)
        assert len(df_clean) == 2
        assert (df_clean[price_cols] > 0).all().all()

    def test_negative_volume_zeroed(self):
        df = _make_bars(3)
        df.loc[2, 'volume'] = -500

        neg_vol = df['volume'] < 0
        assert neg_vol.sum() == 1
        df.loc[neg_vol, 'volume'] = 0
        assert (df['volume'] >= 0).all()

    def test_clean_data_passes(self):
        df = _make_bars(10)
        assert (df['high'] >= df['low']).all()
        assert (df[['open', 'high', 'low', 'close']] > 0).all().all()
        assert (df['volume'] >= 0).all()
