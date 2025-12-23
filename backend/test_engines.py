"""
Script de test des engines DexterioBOT
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from engines.data_feed import DataFeedEngine
from engines.market_state import MarketStateEngine
from engines.liquidity import LiquidityEngine
from config.settings import settings
from datetime import datetime
from utils.timeframes import get_session_info

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_data_feed():
    """Test du Data Feed Engine"""
    logger.info("=" * 60)
    logger.info("Testing Data Feed Engine")
    logger.info("=" * 60)
    
    data_feed = DataFeedEngine(symbols=['SPY'])
    
    # Test 1: Fetch historical data
    logger.info("\n[TEST 1] Fetching historical data for SPY (5m, 5d)...")
    candles = data_feed.fetch_historical_data('SPY', period='5d', interval='5m')
    logger.info(f"✓ Fetched {len(candles)} candles")
    if candles:
        latest = candles[-1]
        logger.info(f"  Latest: {latest.timestamp} O:{latest.open:.2f} H:{latest.high:.2f} L:{latest.low:.2f} C:{latest.close:.2f}")
    
    # Test 2: Multi-timeframe data
    logger.info("\n[TEST 2] Fetching multi-timeframe data...")
    multi_tf_data = data_feed.get_multi_timeframe_data('SPY')
    for tf, candles in multi_tf_data.items():
        logger.info(f"  {tf}: {len(candles)} candles")
    
    # Test 3: Latest price
    logger.info("\n[TEST 3] Getting latest price...")
    price = data_feed.get_latest_price('SPY')
    logger.info(f"✓ Latest price: ${price:.2f}")
    
    return multi_tf_data

async def test_market_state(multi_tf_data):
    """Test du Market State Engine"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Market State Engine")
    logger.info("=" * 60)
    
    market_state_engine = MarketStateEngine()
    
    # Test 1: Analyze structures
    logger.info("\n[TEST 1] Analyzing HTF structures...")
    daily = multi_tf_data.get('1d', [])
    h4 = multi_tf_data.get('4h', [])
    h1 = multi_tf_data.get('1h', [])
    
    structures = market_state_engine.analyze_htf_structure(daily, h4, h1)
    for tf, structure in structures.items():
        logger.info(f"  {tf}: {structure}")
    
    # Test 2: Determine bias
    logger.info("\n[TEST 2] Determining market bias...")
    bias_analysis = market_state_engine.determine_bias(daily, h4, h1, {})
    logger.info(f"  Bias: {bias_analysis['bias']}")
    logger.info(f"  Confidence: {bias_analysis['confidence']:.2%}")
    logger.info(f"  Reasoning: {bias_analysis['reasoning']}")
    
    # Test 3: Create market state
    logger.info("\n[TEST 3] Creating market state...")
    session_info = get_session_info(datetime.utcnow())
    market_state = market_state_engine.create_market_state(
        'SPY',
        multi_tf_data,
        {'current_session': session_info['name'], 'session_levels': {}}
    )
    logger.info(f"  Symbol: {market_state.symbol}")
    logger.info(f"  Bias: {market_state.bias} ({market_state.bias_confidence:.2%})")
    logger.info(f"  Session Profile: {market_state.session_profile}")
    logger.info(f"  Current Session: {market_state.current_session}")
    if market_state.pdh:
        logger.info(f"  PDH: ${market_state.pdh:.2f}")
    if market_state.pdl:
        logger.info(f"  PDL: ${market_state.pdl:.2f}")
    
    return market_state

async def test_liquidity(multi_tf_data, market_state):
    """Test du Liquidity Engine"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Liquidity Engine")
    logger.info("=" * 60)
    
    liquidity_engine = LiquidityEngine()
    
    # Test 1: Identify liquidity levels
    logger.info("\n[TEST 1] Identifying liquidity levels...")
    htf_levels = {
        'pdh': market_state.pdh,
        'pdl': market_state.pdl,
        'asia_high': market_state.asia_high,
        'asia_low': market_state.asia_low
    }
    
    levels = liquidity_engine.identify_liquidity_levels('SPY', multi_tf_data, htf_levels)
    logger.info(f"✓ Identified {len(levels)} liquidity levels")
    
    # Top 5 levels
    logger.info("\n  Top 5 levels by importance:")
    sorted_levels = sorted(levels, key=lambda x: x.importance, reverse=True)[:5]
    for level in sorted_levels:
        logger.info(f"    {level.level_type}: ${level.price:.2f} (importance: {level.importance})")
    
    # Test 2: Detect sweeps
    logger.info("\n[TEST 2] Detecting sweeps on recent candles...")
    candles_m5 = multi_tf_data.get('5m', [])
    if len(candles_m5) >= 2:
        current_candle = candles_m5[-1]
        previous_candles = candles_m5[:-1]
        
        sweeps = liquidity_engine.detect_sweep('SPY', current_candle, previous_candles)
        logger.info(f"✓ Detected {len(sweeps)} sweeps")
        
        for sweep in sweeps:
            logger.info(f"    {sweep['sweep_type']}: {sweep['level'].level_type} at ${sweep['level'].price:.2f}")
    
    # Test 3: Nearest liquidity
    logger.info("\n[TEST 3] Finding nearest liquidity...")
    current_price = candles_m5[-1].close if candles_m5 else 0
    nearest = liquidity_engine.get_nearest_liquidity('SPY', current_price, direction='both')
    
    if nearest['above']:
        logger.info(f"  Above: {nearest['above'].level_type} at ${nearest['above'].price:.2f}")
    if nearest['below']:
        logger.info(f"  Below: {nearest['below'].level_type} at ${nearest['below'].price:.2f}")
    
    return levels

async def main():
    """Test complet"""
    logger.info("\n")
    logger.info("╔" + "=" * 58 + "╗")
    logger.info("║" + " " * 10 + "DexterioBOT ENGINES TEST SUITE" + " " * 17 + "║")
    logger.info("╚" + "=" * 58 + "╝")
    logger.info("")
    
    try:
        # Test Data Feed
        multi_tf_data = await test_data_feed()
        
        # Test Market State
        market_state = await test_market_state(multi_tf_data)
        
        # Test Liquidity
        levels = await test_liquidity(multi_tf_data, market_state)
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("✓ ALL TESTS PASSED")
        logger.info("=" * 60)
        logger.info(f"\nSummary:")
        logger.info(f"  - Data Feed: ✓ Working")
        logger.info(f"  - Market State: ✓ Working")
        logger.info(f"  - Liquidity Engine: ✓ Working")
        logger.info(f"  - Identified {len(levels)} liquidity levels")
        logger.info(f"  - Current bias: {market_state.bias} ({market_state.bias_confidence:.2%})")
        logger.info("")
        logger.info("Ready to proceed with Pattern & Setup Engines!")
        logger.info("")
        
    except Exception as e:
        logger.error(f"\n✗ TEST FAILED: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
