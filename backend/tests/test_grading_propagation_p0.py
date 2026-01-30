"""
P0 Test: Grading Propagation Pipeline
Vérifie que match_score/match_grade/grade_thresholds/score_scale_hint
sont correctement propagés de Trade vers TradeResult.
"""
import sys
from pathlib import Path
from datetime import datetime

# Ajouter le chemin backend au PYTHONPATH
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from models.trade import Trade
from models.backtest import TradeResult


def test_grading_propagation_trade_to_traderesult():
    """Test que les champs grading sont propagés de Trade vers TradeResult"""
    
    # Créer un Trade mock avec tous les champs grading
    trade = Trade(
        date=datetime.now().date(),
        time_entry=datetime.now(),
        symbol="SPY",
        direction="LONG",
        bias_htf="bullish",
        session_profile=0,
        session="ny",
        market_conditions="test",
        playbook="Liquidity_Sweep_Scalp",
        setup_quality="C",
        setup_score=0.45,
        trade_type="SCALP",
        entry_price=500.0,
        stop_loss=499.0,
        take_profit_1=501.0,
        exit_price=500.5,
        position_size=100.0,
        risk_amount=100.0,
        risk_pct=0.02,
        pnl_dollars=50.0,
        pnl_pct=0.01,
        r_multiple=0.5,
        outcome="win",
        exit_reason="tp1",
        # P0: Champs grading
        match_score=0.45,
        match_grade="C",
        grade_thresholds={"A_plus": 0.8, "A": 0.6, "B": 0.5},
        score_scale_hint="0-1"
    )
    
    # Simuler la création d'un TradeResult depuis Trade (comme dans _ingest_closed_trades)
    match_score = getattr(trade, 'match_score', None)
    match_grade = getattr(trade, 'match_grade', None)
    grade_thresholds = getattr(trade, 'grade_thresholds', None)
    score_scale_hint = getattr(trade, 'score_scale_hint', None)
    
    trade_result = TradeResult(
        trade_id=trade.id,
        timestamp_entry=trade.time_entry,
        timestamp_exit=trade.time_entry,  # Simplifié pour le test
        duration_minutes=60.0,
        symbol=trade.symbol,
        direction=trade.direction,
        trade_type=trade.trade_type,
        playbook=trade.playbook,
        quality=trade.get_quality(),
        entry_price=trade.entry_price,
        exit_price=trade.exit_price,
        stop_loss=trade.stop_loss,
        take_profit_1=trade.take_profit_1,
        position_size=trade.position_size,
        risk_pct=trade.risk_pct,
        risk_amount=trade.risk_amount,
        pnl_dollars=trade.pnl_dollars,
        pnl_r=trade.r_multiple,
        outcome=trade.outcome,
        exit_reason=trade.exit_reason,
        # P0: Propagation grading debug info
        match_score=match_score,
        match_grade=match_grade,
        grade_thresholds=grade_thresholds,
        score_scale_hint=score_scale_hint,
    )
    
    # Vérifications
    assert trade_result.match_score == 0.45, "match_score doit être propagé"
    assert trade_result.match_grade == "C", "match_grade doit être propagé"
    assert trade_result.grade_thresholds == {"A_plus": 0.8, "A": 0.6, "B": 0.5}, "grade_thresholds doit être propagé"
    assert trade_result.score_scale_hint == "0-1", "score_scale_hint doit être propagé"
    
    print("✓ Test grading propagation: OK")

if __name__ == "__main__":
    test_grading_propagation_trade_to_traderesult()
    print("All tests passed!")
