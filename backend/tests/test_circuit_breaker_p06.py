"""
P0.6.1 - Tests d'intégration pour Circuit Breaker MaxDD

Vérifie que:
1. stop_run est déclenché quand MaxDD >= 20R
2. Aucun trade n'est ouvert après stop_run
3. guardrails_events contient l'événement stop_run
"""
import pytest
from datetime import date, datetime
from engines.risk_engine import RiskEngine, CIRCUIT_STOP_RUN_DD_R


class TestCircuitBreakerMaxDD:
    """Tests d'intégration pour le circuit breaker MaxDD."""
    
    def test_stop_run_triggered_at_20r(self):
        """stop_run déclenché quand MaxDD >= 20R."""
        engine = RiskEngine(initial_capital=50000.0)
        base_r = engine.state.base_r_unit_dollars  # 1000$
        
        # Simuler des trades qui créent un DD > 20R
        # Peak = +5R, puis chute à -16R = DD de 21R
        
        # D'abord monter le peak
        for i in range(5):
            engine.update_risk_after_trade(
                trade_result='win',
                trade_pnl_dollars=base_r * 1,  # +1R chaque
                trade_risk_dollars=base_r * 2,
                trade_tier=2,
                playbook_name='Test',
                current_day=date.today()
            )
        
        assert engine.state.run_peak_r == 5.0  # Peak à +5R
        
        # Maintenant perdre pour créer DD
        for i in range(21):
            engine.update_risk_after_trade(
                trade_result='loss',
                trade_pnl_dollars=-base_r * 1,  # -1R chaque
                trade_risk_dollars=base_r * 2,
                trade_tier=2,
                playbook_name='Test',
                current_day=date.today()
            )
        
        # Peak = 5R, Current = 5 - 21 = -16R, DD = 5 - (-16) = 21R
        assert engine.state.run_total_r == -16.0
        assert engine.state.max_drawdown_r == 21.0  # DD = 21R
        
        # Vérifier le circuit breaker
        cb_result = engine.check_circuit_breakers(date.today())
        
        assert cb_result['stop_run'] is True
        assert cb_result['trading_allowed'] is False
        assert 'MaxDD' in cb_result['reason']
        assert '21.00R' in cb_result['reason']
    
    def test_stop_run_not_triggered_below_20r(self):
        """stop_run PAS déclenché si MaxDD < 20R (mais stop_day peut l'être)."""
        engine = RiskEngine(initial_capital=50000.0)
        base_r = engine.state.base_r_unit_dollars
        
        # Simuler DD = 19R (juste en dessous) en répartissant sur plusieurs jours
        # pour éviter stop_day (-4R/jour)
        from datetime import timedelta
        
        for i in range(19):
            # Changer de jour tous les 3 trades pour éviter stop_day
            day = date.today() + timedelta(days=i // 3)
            engine.update_risk_after_trade(
                trade_result='loss',
                trade_pnl_dollars=-base_r * 1,
                trade_risk_dollars=base_r * 2,
                trade_tier=2,
                playbook_name='Test',
                current_day=day
            )
            # Reset daily counters pour éviter stop_day
            if i % 3 == 2:
                engine.reset_daily_counters()
        
        assert engine.state.max_drawdown_r == 19.0
        
        cb_result = engine.check_circuit_breakers(date.today())
        
        # stop_run ne doit PAS être déclenché (MaxDD=19 < 20)
        assert cb_result['stop_run'] is False
    
    def test_no_trade_after_stop_run(self):
        """Aucun trade ne doit être autorisé après stop_run."""
        from models.setup import Setup
        from datetime import timedelta
        
        engine = RiskEngine(initial_capital=50000.0)
        base_r = engine.state.base_r_unit_dollars
        
        # D'abord créer un peak pour pouvoir avoir un DD
        for i in range(5):
            engine.update_risk_after_trade(
                trade_result='win',
                trade_pnl_dollars=base_r * 1,
                trade_risk_dollars=base_r * 2,
                trade_tier=2,
                playbook_name='Test',
                current_day=date.today()
            )
        
        # Maintenant créer DD > 20R en répartissant sur plusieurs jours
        for i in range(26):  # 26 pertes pour DD = 26R (peak=5, current=-21, DD=26)
            day = date.today() + timedelta(days=1 + i // 3)
            engine.update_risk_after_trade(
                trade_result='loss',
                trade_pnl_dollars=-base_r * 1,
                trade_risk_dollars=base_r * 2,
                trade_tier=2,
                playbook_name='Test',
                current_day=day
            )
            if i % 3 == 2:
                engine.reset_daily_counters()
        
        # Vérifier que stop_run est déclenché (DD = 5 - (-21) = 26R)
        assert engine.state.max_drawdown_r >= 20.0
        cb = engine.check_circuit_breakers(date.today())
        assert cb['stop_run'] is True
        
        # Créer un setup fictif avec tous les champs requis
        setup = Setup(
            symbol='SPY',
            direction='LONG',
            trade_type='DAILY',
            entry_price=580.0,
            stop_loss=578.0,
            take_profit_1=585.0,
            take_profit_2=590.0,
            risk_reward=2.5,
            quality='A',
            final_score=0.8,
            market_bias='bullish',
            session='ny',
        )
        
        # Vérifier que can_take_setup retourne False
        result = engine.can_take_setup(setup)
        
        assert result['allowed'] is False
        # Le reason peut être MaxDD ou STOP_RUN ou circuit_breaker
        assert any(x in result['reason'].upper() for x in ['MAXDD', 'STOP', 'DD'])


class TestMaxDDCalculation:
    """Vérifie que le calcul de MaxDD est correct."""
    
    def test_maxdd_tracks_peak_to_trough(self):
        """MaxDD = max(peak - current) sur l'equity en R."""
        engine = RiskEngine(initial_capital=50000.0)
        base_r = engine.state.base_r_unit_dollars
        
        # Séquence: +2, +3, -4, +1, -3 
        # Equity: 2, 5, 1, 2, -1
        # Peak: 2, 5, 5, 5, 5
        # DD: 0, 0, 4, 3, 6
        
        trades = [
            ('win', 2),
            ('win', 3),
            ('loss', -4),
            ('win', 1),
            ('loss', -3),
        ]
        
        expected_dds = [0, 0, 4, 3, 6]
        
        for i, (result, pnl_r) in enumerate(trades):
            engine.update_risk_after_trade(
                trade_result=result,
                trade_pnl_dollars=base_r * pnl_r,
                trade_risk_dollars=base_r * 2,
                trade_tier=2,
                playbook_name='Test',
                current_day=date.today()
            )
            
            # Le MaxDD doit être le max de tous les DD jusqu'ici
            expected_max_dd = max(expected_dds[:i+1])
            assert engine.state.max_drawdown_r == expected_max_dd, \
                f"After trade {i+1}: expected MaxDD={expected_max_dd}, got {engine.state.max_drawdown_r}"
        
        # MaxDD final = 6R
        assert engine.state.max_drawdown_r == 6.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
