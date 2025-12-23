#!/usr/bin/env python3
"""
Test Unitaire - Validation bugfix ExecutionEngine
Vérifie que TP2 > TP1 et qu'il n'y a pas de double close
"""
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.execution.paper_trading import ExecutionEngine
from engines.risk_engine import RiskEngine
from models.setup import Setup
from models.market_data import Candle

print("="*80)
print("TEST UNITAIRE - ExecutionEngine Bugfix (TP1/TP2)")
print("="*80)

# Setup minimal
risk_engine = RiskEngine(initial_capital=10000.0)
exec_engine = ExecutionEngine(risk_engine)

# Créer un setup mock
setup = Setup(
    symbol='SPY',
    direction='LONG',
    entry_price=100.0,
    stop_loss=98.0,
    take_profit_1=102.0,
    take_profit_2=104.0,
    risk_reward=2.0,
    quality='A',
    final_score=0.8,
    confluences_count=3,
    playbook_matches=[],
    timestamp=datetime.now(timezone.utc),
    trade_type='DAILY',
    market_bias='bullish',
    session='NY'
)

# Placer l'ordre avec position_calc mock
from models.risk import PositionSizingResult

position_calc = PositionSizingResult(
    risk_amount=100.0,
    position_size=50.0,  # 50 shares
    risk_tier=1.0,
    distance_stop=2.0,
    multiplier=1.0,
    valid=True
)

risk_allocation = {
    'risk_pct': 1.0,
    'risk_tier': 1.0,
    'risk_dollars': 100.0,
    'position_calc': position_calc
}

print("\n1️⃣ Placing order...")
result = exec_engine.place_order(setup, risk_allocation, current_time=datetime.now(timezone.utc))
print(f"   Order result: {result}")

if not result['success']:
    print(f"   ❌ Order failed: {result.get('reason', 'Unknown')}")
    sys.exit(1)

print(f"   Order placed: {result['success']}")
trade_id = result['trade_id']

# Vérifier qu'il y a 1 trade ouvert
assert len(exec_engine.open_trades) == 1, "Should have 1 open trade"
print(f"   ✅ 1 trade open (ID: {trade_id[:8]}...)")

# Test 1: Prix atteint TP2 (qui implique TP1 aussi pour un LONG)
print("\n2️⃣ Simulating price hitting TP2 (104.0)...")
market_data = {
    'SPY': 104.5  # Prix actuel dépasse TP2
}

# Update trades (devrait fermer sur TP2)
events = exec_engine.update_open_trades(market_data)
print(f"   Events: {[e['event_type'] for e in events]}")

# Vérifier qu'on a fermé sur TP2 uniquement
tp2_events = [e for e in events if e['event_type'] == 'TP2_HIT']
tp1_events = [e for e in events if e['event_type'] == 'TP1_HIT']

assert len(tp2_events) == 1, f"Expected 1 TP2_HIT event, got {len(tp2_events)}"
assert len(tp1_events) == 0, f"Expected 0 TP1_HIT events (skipped), got {len(tp1_events)}"
print(f"   ✅ TP2 triggered, TP1 skipped (priority logic OK)")

# Vérifier qu'il n'y a plus de trades ouverts
assert len(exec_engine.open_trades) == 0, f"Should have 0 open trades, got {len(exec_engine.open_trades)}"
print(f"   ✅ Trade closed (no double close)")

# Test 2: Nouveau trade, prix atteint seulement TP1
print("\n3️⃣ Placing new order...")
result2 = exec_engine.place_order(setup, risk_allocation, current_time=datetime.now(timezone.utc))
trade_id2 = result2['trade_id']
print(f"   Order placed: {result2['success']} (ID: {trade_id2[:8]}...)")

print("\n4️⃣ Simulating price hitting TP1 only (102.0)...")
market_data2 = {
    'SPY': 102.2  # Prix atteint TP1 mais pas TP2
}

events2 = exec_engine.update_open_trades(market_data2)
print(f"   Events: {[e['event_type'] for e in events2]}")

tp2_events2 = [e for e in events2 if e['event_type'] == 'TP2_HIT']
tp1_events2 = [e for e in events2 if e['event_type'] == 'TP1_HIT']

assert len(tp1_events2) == 1, f"Expected 1 TP1_HIT event, got {len(tp1_events2)}"
assert len(tp2_events2) == 0, f"Expected 0 TP2_HIT events, got {len(tp2_events2)}"
print(f"   ✅ TP1 triggered correctly")

assert len(exec_engine.open_trades) == 0, "Should have 0 open trades"
print(f"   ✅ Trade closed (no double close)")

print("\n" + "="*80)
print("✅ BUGFIX VALIDATION PASSED")
print("="*80)
print("Summary:")
print("  - TP2 priority over TP1: ✅")
print("  - No double close: ✅")
print("  - TP1 works when TP2 not hit: ✅")
