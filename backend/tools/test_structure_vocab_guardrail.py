#!/usr/bin/env python3
"""
GUARDRAIL: Structure Vocabulary Validation
Ensures no test or production code forces wrong vocabulary
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

def test_structure_vocab_guardrail():
    """Test that structure_htf uses correct vocabulary"""
    
    print("\n" + "="*70)
    print("GUARDRAIL: Structure Vocabulary Validation")
    print("="*70)
    
    from engines.market_state import MarketStateEngine
    from models.market_data import Candle
    from datetime import datetime
    
    # Create minimal test data
    candles = [
        Candle(
            symbol='TEST',
            timeframe='1d',
            timestamp=datetime(2025, 6, i+1),
            open=100.0 + i,
            high=101.0 + i,
            low=99.0 + i,
            close=100.5 + i,
            volume=1000
        )
        for i in range(30)
    ]
    
    # Test MarketStateEngine output
    mse = MarketStateEngine()
    
    market_state = mse.create_market_state(
        symbol='TEST',
        multi_tf_data={
            '1m': candles[:10],
            '5m': candles[:10],
            '15m': candles[:10],
            '1h': candles[:20],
            '4h': candles[:25],
            '1d': candles
        },
        session_info={'name': 'NY', 'session_levels': {}}
    )
    
    # VALIDATE VOCABULARY
    valid_vocab = {'uptrend', 'downtrend', 'range', 'unknown'}
    invalid_vocab = {'bullish', 'bearish', 'neutral'}
    
    errors = []
    
    for field in ['daily_structure', 'h4_structure', 'h1_structure']:
        value = getattr(market_state, field, None)
        
        if value in invalid_vocab:
            errors.append(f"FAIL: {field} = '{value}' (invalid vocabulary)")
        elif value not in valid_vocab:
            errors.append(f"FAIL: {field} = '{value}' (unknown value)")
        else:
            print(f"  ✅ {field} = '{value}' (valid)")
    
    if errors:
        print("\n❌ GUARDRAIL FAILED:")
        for error in errors:
            print(f"  {error}")
        print("\n⚠️  FIX REQUIRED: MarketStateEngine must produce ['uptrend', 'downtrend', 'range', 'unknown']")
        return False
    else:
        print("\n✅ GUARDRAIL PASSED: All structure fields use correct vocabulary")
        return True

if __name__ == '__main__':
    success = test_structure_vocab_guardrail()
    sys.exit(0 if success else 1)
