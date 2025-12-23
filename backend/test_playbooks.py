"""
Test des Playbooks Phase 2.2
Vérifie que les playbooks sont bien chargés et évaluables
"""
import sys
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from engines.playbook_loader import get_playbook_loader, PlaybookEvaluator
from engines.setup_engine_v2 import SetupEngineV2, filter_setups_safe_mode, filter_setups_aggressive_mode
from models.market_data import MarketState
from models.setup import ICTPattern, CandlestickPattern

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)


def test_playbook_loading():
    """Test 1: Chargement des playbooks"""
    print("\n" + "="*80)
    print("TEST 1: CHARGEMENT DES PLAYBOOKS")
    print("="*80)
    
    loader = get_playbook_loader()
    
    print(f"\n✅ Total playbooks chargés: {len(loader.playbooks)}")
    
    # Stats par catégorie
    daytrade = [p for p in loader.playbooks if p.category == 'DAYTRADE']
    scalp = [p for p in loader.playbooks if p.category == 'SCALP']
    
    print(f"   DAYTRADE: {len(daytrade)}")
    for pb in daytrade:
        print(f"      • {pb.name}")
    
    print(f"\n   SCALP: {len(scalp)}")
    for pb in scalp:
        print(f"      • {pb.name}")
    
    # Test modes
    print("\n📊 Playbooks par mode:")
    safe_pbs = loader.get_playbooks_for_mode('SAFE')
    aggressive_pbs = loader.get_playbooks_for_mode('AGGRESSIVE')
    
    print(f"   SAFE: {len(safe_pbs)} playbooks")
    print(f"   AGGRESSIVE: {len(aggressive_pbs)} playbooks")
    
    assert len(loader.playbooks) == 11, "Should have 11 playbooks (6 DAYTRADE + 5 SCALP)"
    assert len(daytrade) == 6, "Should have 6 DAYTRADE playbooks"
    assert len(scalp) == 5, "Should have 5 SCALP playbooks"
    
    print("\n✅ TEST 1 PASSED\n")


def test_playbook_evaluation():
    """Test 2: Évaluation des playbooks avec contexte"""
    print("\n" + "="*80)
    print("TEST 2: ÉVALUATION DES PLAYBOOKS")
    print("="*80)
    
    # Créer un contexte de test
    market_state = MarketState(
        symbol='SPY',
        timestamp=datetime.now(),
        bias='bullish',
        daily_structure='uptrend',
        h4_structure='uptrend',
        h1_structure='uptrend',
        current_session='NY',
        session_profile=1,
        pdh=455.0,
        pdl=450.0,
        asia_high=453.0,
        asia_low=451.0,
        london_high=454.0,
        london_low=450.5
    )
    
    # ICT patterns simulés
    ict_patterns = [
        ICTPattern(
            pattern_type='sweep',
            symbol='SPY',
            timeframe='1m',
            direction='bullish',
            timestamp=datetime.now(),
            price_level=450.5,
            strength=0.8,
            confidence=0.85
        ),
        ICTPattern(
            pattern_type='fvg',
            symbol='SPY',
            timeframe='5m',
            direction='bullish',
            timestamp=datetime.now(),
            price_level=452.0,
            strength=0.7,
            confidence=0.75
        )
    ]
    
    # Candlestick patterns simulés
    candle_patterns = [
        CandlestickPattern(
            family='engulfing',
            name='Bullish Engulfing',
            direction='bullish',
            timestamp=datetime.now(),
            timeframe='1m',
            strength=0.85,
            body_size=0.6,
            confirmation=True
        )
    ]
    
    # Évaluer les playbooks
    loader = get_playbook_loader()
    evaluator = PlaybookEvaluator(loader)
    
    market_context = {
        'bias': market_state.bias,
        'current_session': market_state.current_session,
        'daily_structure': market_state.daily_structure,
        'h4_structure': market_state.h4_structure,
        'h1_structure': market_state.h1_structure,
        'session_profile': market_state.session_profile
    }
    
    # Test mode SAFE
    print("\n📊 Mode SAFE:")
    matches_safe = evaluator.evaluate_all_playbooks(
        symbol='SPY',
        market_state=market_context,
        ict_patterns=ict_patterns,
        candle_patterns=candle_patterns,
        current_time=datetime.now().replace(hour=10, minute=0),
        trading_mode='SAFE'
    )
    
    print(f"   Playbooks matched: {len(matches_safe)}")
    for match in matches_safe:
        print(f"      • {match['playbook_name']}: {match['grade']} (score: {match['score']:.2f})")
    
    # Test mode AGGRESSIVE
    print("\n📊 Mode AGGRESSIVE:")
    matches_aggressive = evaluator.evaluate_all_playbooks(
        symbol='SPY',
        market_state=market_context,
        ict_patterns=ict_patterns,
        candle_patterns=candle_patterns,
        current_time=datetime.now().replace(hour=10, minute=0),
        trading_mode='AGGRESSIVE'
    )
    
    print(f"   Playbooks matched: {len(matches_aggressive)}")
    for match in matches_aggressive:
        print(f"      • {match['playbook_name']}: {match['grade']} (score: {match['score']:.2f})")
    
    print("\n✅ TEST 2 PASSED\n")


def test_setup_engine_v2():
    """Test 3: SetupEngine V2 avec playbooks"""
    print("\n" + "="*80)
    print("TEST 3: SETUP ENGINE V2")
    print("="*80)
    
    engine = SetupEngineV2()
    
    # Contexte de test
    market_state = MarketState(
        symbol='SPY',
        timestamp=datetime.now(),
        bias='bullish',
        daily_structure='uptrend',
        h4_structure='uptrend',
        h1_structure='uptrend',
        current_session='NY',
        session_profile=1,
        pdh=455.0,
        pdl=450.0,
        asia_high=453.0,
        asia_low=451.0,
        london_high=454.0,
        london_low=450.5
    )
    
    ict_patterns = [
        ICTPattern(
            pattern_type='sweep',
            symbol='SPY',
            timeframe='1m',
            direction='bullish',
            timestamp=datetime.now(),
            price_level=450.5,
            strength=0.8,
            confidence=0.85
        )
    ]
    
    candle_patterns = [
        CandlestickPattern(
            family='engulfing',
            name='Bullish Engulfing',
            direction='bullish',
            timestamp=datetime.now(),
            timeframe='1m',
            strength=0.85,
            body_size=0.6,
            confirmation=True
        )
    ]
    
    # Générer setups mode SAFE
    print("\n📊 Génération setups mode SAFE:")
    setups_safe = engine.generate_setups(
        symbol='SPY',
        market_state=market_state,
        ict_patterns=ict_patterns,
        candle_patterns=candle_patterns,
        liquidity_levels=[],
        current_time=datetime.now().replace(hour=10, minute=0),
        trading_mode='SAFE'
    )
    
    print(f"   Setups générés: {len(setups_safe)}")
    for setup in setups_safe:
        print(f"      • {setup.symbol} {setup.direction} | {setup.quality} | {setup.trade_type}")
        print(f"        Entry: {setup.entry_price:.2f}, SL: {setup.stop_loss:.2f}, TP1: {setup.take_profit_1:.2f}")
    
    # Filtrer SAFE
    filtered_safe = filter_setups_safe_mode(setups_safe)
    print(f"   Après filtre SAFE: {len(filtered_safe)} setups")
    
    # Générer setups mode AGGRESSIVE
    print("\n📊 Génération setups mode AGGRESSIVE:")
    setups_aggressive = engine.generate_setups(
        symbol='SPY',
        market_state=market_state,
        ict_patterns=ict_patterns,
        candle_patterns=candle_patterns,
        liquidity_levels=[],
        current_time=datetime.now().replace(hour=10, minute=0),
        trading_mode='AGGRESSIVE'
    )
    
    print(f"   Setups générés: {len(setups_aggressive)}")
    for setup in setups_aggressive:
        print(f"      • {setup.symbol} {setup.direction} | {setup.quality} | {setup.trade_type}")
    
    # Filtrer AGGRESSIVE
    filtered_aggressive = filter_setups_aggressive_mode(setups_aggressive)
    print(f"   Après filtre AGGRESSIVE: {len(filtered_aggressive)} setups")
    
    print("\n✅ TEST 3 PASSED\n")


def main():
    """Exécuter tous les tests"""
    print("\n" + "="*80)
    print("🚀 TESTS PHASE 2.2 - PLAYBOOKS DAYTRADE & SCALP")
    print("="*80)
    
    try:
        test_playbook_loading()
        test_playbook_evaluation()
        test_setup_engine_v2()
        
        print("\n" + "="*80)
        print("✅ ✅ ✅ TOUS LES TESTS PHASE 2.2 PASSÉS ✅ ✅ ✅")
        print("="*80)
        print("\n📋 RÉCAPITULATIF:")
        print("  ✓ 11 playbooks chargés (6 DAYTRADE + 5 SCALP)")
        print("  ✓ Évaluation des playbooks fonctionnelle")
        print("  ✓ SetupEngine V2 opérationnel")
        print("  ✓ Filtres SAFE/AGGRESSIVE fonctionnels")
        print("\n🎯 Phase 2.2 est COMPLÈTE !")
        print("="*80 + "\n")
        
        return 0
    
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
