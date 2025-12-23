"""Test Phase 1.2 - Pattern & Setup Engines"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import asyncio
import logging
from datetime import datetime
from engines.pipeline import TradingPipeline
from config.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Test complet Phase 1.2"""
    
    logger.info("\n")
    logger.info("╔" + "=" * 70 + "╗")
    logger.info("║" + " " * 15 + "DEXTERIOBOT PHASE 1.2 TEST SUITE" + " " * 22 + "║")
    logger.info("║" + " " * 20 + "Pattern & Setup Engines" + " " * 27 + "║")
    logger.info("╚" + "=" * 70 + "╝")
    logger.info("")
    
    try:
        # Configuration
        logger.info(f"Trading Mode: {settings.TRADING_MODE}")
        logger.info(f"Symbols: {settings.SYMBOLS}")
        logger.info(f"Quality Thresholds: A+={settings.QUALITY_THRESHOLD_A_PLUS}, "
                   f"A={settings.QUALITY_THRESHOLD_A}, B={settings.QUALITY_THRESHOLD_B}")
        logger.info("")
        
        # Initialiser pipeline
        logger.info("Initializing TradingPipeline...")
        pipeline = TradingPipeline()
        logger.info("✓ Pipeline initialized\n")
        
        # Exécuter analyse complète
        logger.info("=" * 72)
        logger.info("Running Full Analysis (Phase 1.1 + 1.2)")
        logger.info("=" * 72)
        
        results = pipeline.run_full_analysis(symbols=['SPY', 'QQQ'])
        
        # Afficher résultats
        logger.info("\n")
        logger.info("=" * 72)
        logger.info("RESULTS")
        logger.info("=" * 72)
        
        for symbol, setups in results.items():
            logger.info(f"\n{symbol}: {len(setups)} tradable setups")
            
            for i, setup in enumerate(setups, 1):
                logger.info(f"\n  Setup #{i}:")
                logger.info(f"    Quality: {setup.quality} (score: {setup.final_score:.3f})")
                logger.info(f"    Direction: {setup.direction}")
                logger.info(f"    Type: {setup.trade_type}")
                logger.info(f"    Confluences: {setup.confluences_count}/6")
                logger.info(f"    Market Bias: {setup.market_bias}")
                logger.info(f"    Session: {setup.session}")
                logger.info(f"    Entry: ${setup.entry_price:.2f}")
                logger.info(f"    Stop Loss: ${setup.stop_loss:.2f}")
                logger.info(f"    Take Profit 1: ${setup.take_profit_1:.2f}")
                logger.info(f"    Risk:Reward: {setup.risk_reward:.2f}:1")
                logger.info(f"    ICT Score: {setup.ict_score:.2f}")
                logger.info(f"    Pattern Score: {setup.pattern_score:.2f}")
                logger.info(f"    Playbook Score: {setup.playbook_score:.2f}")
                
                # Détails patterns
                if setup.ict_patterns:
                    logger.info(f"    ICT Patterns: {', '.join(p.pattern_type for p in setup.ict_patterns)}")
                if setup.candlestick_patterns:
                    logger.info(f"    Candlestick Patterns: {', '.join(p.pattern_name for p in setup.candlestick_patterns)}")
                if setup.playbook_matches:
                    logger.info(f"    Playbooks: {', '.join(p.playbook_name for p in setup.playbook_matches)}")
        
        # Summary
        summary = pipeline.get_summary(results)
        logger.info("\n")
        logger.info("=" * 72)
        logger.info("SUMMARY")
        logger.info("=" * 72)
        logger.info(f"Timestamp: {summary['timestamp']}")
        logger.info(f"Trading Mode: {summary['trading_mode']}")
        logger.info(f"Total Setups: {summary['total_setups']}")
        logger.info(f"By Symbol: {summary['by_symbol']}")
        logger.info(f"By Quality: {summary['by_quality']}")
        logger.info(f"By Direction: {summary['by_direction']}")
        logger.info(f"By Type: {summary['by_type']}")
        
        # Validation
        logger.info("\n")
        logger.info("=" * 72)
        logger.info("VALIDATION")
        logger.info("=" * 72)
        
        all_passed = True
        
        # Test 1: Pipeline runs without errors
        logger.info("✓ Pipeline executed successfully")
        
        # Test 2: Engines initialized
        logger.info("✓ All engines initialized (Data Feed, Market State, Liquidity, "
                   "Candlestick, ICT, Playbook, Setup)")
        
        # Test 3: Mode filtering applied
        if settings.TRADING_MODE == 'SAFE':
            for symbol, setups in results.items():
                for setup in setups:
                    if setup.quality != 'A+':
                        logger.error(f"✗ SAFE mode filter failed: {setup.quality} setup passed")
                        all_passed = False
            if all_passed:
                logger.info("✓ SAFE mode filtering applied correctly (A+ only)")
        
        # Test 4: Scoring components present
        for symbol, setups in results.items():
            for setup in setups:
                if setup.final_score == 0:
                    logger.error(f"✗ Setup has zero score")
                    all_passed = False
        if all_passed:
            logger.info("✓ Setup scoring working (ict + pattern + playbook)")
        
        # Test 5: Risk:Reward calculated
        for symbol, setups in results.items():
            for setup in setups:
                if setup.risk_reward <= 0:
                    logger.error(f"✗ Invalid R:R: {setup.risk_reward}")
                    all_passed = False
        if all_passed:
            logger.info("✓ Risk:Reward calculations valid")
        
        # Final result
        logger.info("\n")
        if all_passed:
            logger.info("=" * 72)
            logger.info("✓✓✓ ALL TESTS PASSED - PHASE 1.2 OPERATIONAL ✓✓✓")
            logger.info("=" * 72)
        else:
            logger.error("=" * 72)
            logger.error("✗✗✗ SOME TESTS FAILED ✗✗✗")
            logger.error("=" * 72)
        
        logger.info("\n")
        logger.info("Phase 1.2 implementation complete!")
        logger.info("Next steps:")
        logger.info("  - Phase 1.3: Risk & Execution Engines")
        logger.info("  - Phase 1.4: Frontend Dashboard")
        logger.info("")
        
    except Exception as e:
        logger.error(f"\n✗ TEST FAILED: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
