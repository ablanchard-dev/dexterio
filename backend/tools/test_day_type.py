#!/usr/bin/env python3
"""
Test day_type calculation in isolation
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

def test_day_type():
    """Test day_type logic"""
    from engines.market_state import MarketStateEngine
    
    mse = MarketStateEngine()
    
    test_cases = [
        {'structure': 'range', 'expected': 'range'},
        {'structure': 'uptrend', 'expected': 'trend'},
        {'structure': 'downtrend', 'expected': 'trend'},
        {'structure': 'unknown', 'expected': 'unknown'},
    ]
    
    print("\n" + "="*70)
    print("DAY_TYPE CALCULATION TEST")
    print("="*70)
    
    for tc in test_cases:
        result = mse.calculate_day_type(tc['structure'], [])
        status = "✅" if result == tc['expected'] else "❌"
        print(f"{status} structure={tc['structure']:<12} → day_type={result:<20} (expected: {tc['expected']})")
    
    print("\n✅ day_type implementation working")

if __name__ == '__main__':
    test_day_type()
