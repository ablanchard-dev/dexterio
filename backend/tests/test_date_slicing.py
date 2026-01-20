"""
P2-1.B Test - Date Slicing

Vérifie que le date slicing fonctionne correctement dans BacktestEngine.
"""
import sys
from pathlib import Path
from datetime import datetime

# Bootstrap
_current_file = Path(__file__).resolve()
_backend_dir = _current_file.parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from models.backtest import BacktestConfig
from backtest.engine import BacktestEngine
from utils.path_resolver import historical_data_path
import pandas as pd


def test_date_slicing():
    """Test que le date slicing réduit correctement le dataset."""
    
    print("=" * 80)
    print("P2-1.B TEST - Date Slicing")
    print("=" * 80)
    
    # Test 1: No slicing (full dataset)
    print("\n📊 Test 1: No date filter (baseline)")
    config_full = BacktestConfig(
        run_name="test_full",
        symbols=["SPY"],
        data_paths=[str(historical_data_path("1m", "SPY.parquet"))],
        trading_mode="AGGRESSIVE"
    )
    
    engine_full = BacktestEngine(config_full)
    engine_full.load_data()
    
    full_bars = len(engine_full.combined_data)
    full_start = engine_full.combined_data['datetime'].min()
    full_end = engine_full.combined_data['datetime'].max()
    
    print(f"  Total bars: {full_bars}")
    print(f"  Date range: {full_start.date()} → {full_end.date()}")
    
    # Test 2: Slice 1 day
    print("\n📊 Test 2: Slice 1 day (2025-06-03)")
    config_1d = BacktestConfig(
        run_name="test_1d",
        symbols=["SPY"],
        data_paths=[str(historical_data_path("1m", "SPY.parquet"))],
        trading_mode="AGGRESSIVE",
        start_date="2025-06-03",
        end_date="2025-06-03"
    )
    
    engine_1d = BacktestEngine(config_1d)
    engine_1d.load_data()
    
    bars_1d = len(engine_1d.combined_data)
    start_1d = engine_1d.combined_data['datetime'].min()
    end_1d = engine_1d.combined_data['datetime'].max()
    
    print(f"  Total bars: {bars_1d}")
    print(f"  Date range: {start_1d.date()} → {end_1d.date()}")
    
    # Assertions
    assert bars_1d < full_bars, "1-day slice should have fewer bars than full dataset"
    assert bars_1d > 0, "1-day slice should have some bars"
    assert start_1d.date() == pd.Timestamp("2025-06-03").date(), "Start date should match"
    assert end_1d.date() == pd.Timestamp("2025-06-03").date(), "End date should match"
    
    # Expected: ~800 bars for 1 trading day (extended hours 08:00-21:00 = 13h * 60min)
    expected_range = (600, 1000)  # Allow flexibility for extended hours
    assert expected_range[0] <= bars_1d <= expected_range[1], \
        f"1-day bars should be in range {expected_range}, got {bars_1d}"
    
    print(f"  ✅ Bars in expected range: {expected_range}")
    
    # Test 3: Slice 1 week (5 trading days)
    print("\n📊 Test 3: Slice 1 week (2025-06-03 → 2025-06-09)")
    config_5d = BacktestConfig(
        run_name="test_5d",
        symbols=["SPY"],
        data_paths=[str(historical_data_path("1m", "SPY.parquet"))],
        trading_mode="AGGRESSIVE",
        start_date="2025-06-03",
        end_date="2025-06-09"
    )
    
    engine_5d = BacktestEngine(config_5d)
    engine_5d.load_data()
    
    bars_5d = len(engine_5d.combined_data)
    start_5d = engine_5d.combined_data['datetime'].min()
    end_5d = engine_5d.combined_data['datetime'].max()
    
    print(f"  Total bars: {bars_5d}")
    print(f"  Date range: {start_5d.date()} → {end_5d.date()}")
    
    # Assertions
    assert bars_5d > bars_1d, "5-day slice should have more bars than 1-day"
    assert bars_5d < full_bars, "5-day slice should have fewer bars than full dataset"
    
    # Expected: ~4000 bars for 5 trading days
    expected_range_5d = (3000, 5000)
    assert expected_range_5d[0] <= bars_5d <= expected_range_5d[1], \
        f"5-day bars should be in range {expected_range_5d}, got {bars_5d}"
    
    print(f"  ✅ Bars in expected range: {expected_range_5d}")
    
    # Test 4: Ratio check
    print("\n📊 Test 4: Ratio check")
    ratio = bars_5d / bars_1d
    print(f"  5d / 1d ratio: {ratio:.2f}")
    
    # Should be ~5x for 5 trading days (allowing for partial days/weekends)
    assert 3 < ratio < 7, f"5d/1d ratio should be ~5, got {ratio:.2f}"
    print(f"  ✅ Ratio is reasonable")
    
    # Summary
    print("\n" + "=" * 80)
    print("✅ ALL DATE SLICING TESTS PASSED")
    print("=" * 80)
    print(f"\nResults Summary:")
    print(f"  Full dataset:  {full_bars} bars")
    print(f"  1-day slice:   {bars_1d} bars ({bars_1d/full_bars*100:.2f}%)")
    print(f"  5-day slice:   {bars_5d} bars ({bars_5d/full_bars*100:.2f}%)")
    print(f"  Speedup ratio: {full_bars/bars_1d:.1f}x faster for 1-day tests")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    try:
        test_date_slicing()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
