"""
Tests P0 pour RiskEngine - Money Management 2R/1R + Guardrails

Commit 3: Tests unitaires pour TwoTierRiskState + sizing + wiring
"""
import pytest
from datetime import date
from models.risk import TwoTierRiskState, PlaybookStats, RiskEngineState
from engines.risk_engine import (
    RiskEngine, 
    AGGRESSIVE_ALLOWLIST, 
    AGGRESSIVE_DENYLIST,
    KILLSWITCH_MIN_TRADES,
    KILLSWITCH_MAX_LOSS_R,
    KILLSWITCH_MIN_PF,
    KILLSWITCH_HARD_STOP_R,
    CIRCUIT_STOP_DAY_R,
    CIRCUIT_STOP_RUN_DD_R,
)


class TestTwoTierRiskState:
    """Tests A) State machine 2R/1R (pur)"""
    
    def test_initial_tier_is_2(self):
        """Start tier=2"""
        state = TwoTierRiskState()
        assert state.current_tier == 2
    
    def test_win_at_2r_stays_2r(self):
        """(tier=2, win) → reste 2"""
        state = TwoTierRiskState()
        state.current_tier = 2
        new_tier = state.on_trade_closed(r_multiple=1.5, trade_tier=2)
        assert new_tier == 2
        assert state.current_tier == 2
    
    def test_loss_at_2r_goes_to_1r(self):
        """(tier=2, loss) → passe 1"""
        state = TwoTierRiskState()
        state.current_tier = 2
        new_tier = state.on_trade_closed(r_multiple=-1.0, trade_tier=2)
        assert new_tier == 1
        assert state.current_tier == 1
    
    def test_loss_at_1r_stays_1r(self):
        """(tier=1, loss) → reste 1"""
        state = TwoTierRiskState()
        state.current_tier = 1
        new_tier = state.on_trade_closed(r_multiple=-1.0, trade_tier=1)
        assert new_tier == 1
        assert state.current_tier == 1
    
    def test_win_at_1r_goes_to_2r(self):
        """(tier=1, win) → remonte 2"""
        state = TwoTierRiskState()
        state.current_tier = 1
        new_tier = state.on_trade_closed(r_multiple=2.0, trade_tier=1)
        assert new_tier == 2
        assert state.current_tier == 2
    
    def test_breakeven_unchanged(self):
        """(tier=?, BE) → inchangé"""
        # Tier 2 + BE
        state = TwoTierRiskState()
        state.current_tier = 2
        new_tier = state.on_trade_closed(r_multiple=0.0, trade_tier=2)
        assert new_tier == 2
        
        # Tier 1 + BE
        state.current_tier = 1
        new_tier = state.on_trade_closed(r_multiple=0.0, trade_tier=1)
        assert new_tier == 1


class TestRiskEngineSizing:
    """Tests B) Sizing (intégration légère RiskEngine)"""
    
    def test_base_r_unit_calculation(self):
        """Fixer base_R_unit_$ = 100 (2% de 5000)"""
        engine = RiskEngine(initial_capital=5000.0)
        assert engine.state.base_r_unit_dollars == 100.0
    
    def test_risk_dollars_at_tier_2(self):
        """Ouvrir trade avec tier=2 → risk_$ == 200"""
        engine = RiskEngine(initial_capital=5000.0)
        engine.state.risk_tier_state.current_tier = 2
        risk_dollars = engine.get_risk_dollars()
        assert risk_dollars == 200.0
    
    def test_risk_dollars_at_tier_1(self):
        """Ouvrir trade avec tier=1 → risk_$ == 100"""
        engine = RiskEngine(initial_capital=5000.0)
        engine.state.risk_tier_state.current_tier = 1
        risk_dollars = engine.get_risk_dollars()
        assert risk_dollars == 100.0
    
    def test_stopout_at_tier_2_gives_minus_2r(self):
        """Vérifier: stop-out à tier=2 ⇒ pnl_R_account == -2"""
        engine = RiskEngine(initial_capital=5000.0)
        base_r = engine.state.base_r_unit_dollars  # 100
        
        # Simuler un stop-out à tier=2
        trade_tier = 2
        trade_risk_dollars = trade_tier * base_r  # 200
        trade_pnl_dollars = -trade_risk_dollars  # -200 (full stop)
        
        result = engine.update_risk_after_trade(
            trade_result='loss',
            trade_pnl_dollars=trade_pnl_dollars,
            trade_risk_dollars=trade_risk_dollars,
            trade_tier=trade_tier,
            playbook_name='Test_Playbook',
            current_day=date.today()
        )
        
        # pnl_R_account = pnl_$ / base_r = -200 / 100 = -2
        assert result['pnl_r_account'] == -2.0
    
    def test_stopout_at_tier_1_gives_minus_1r(self):
        """Vérifier: stop-out à tier=1 ⇒ pnl_R_account == -1"""
        engine = RiskEngine(initial_capital=5000.0)
        base_r = engine.state.base_r_unit_dollars  # 100
        
        # Simuler un stop-out à tier=1
        trade_tier = 1
        trade_risk_dollars = trade_tier * base_r  # 100
        trade_pnl_dollars = -trade_risk_dollars  # -100 (full stop)
        
        result = engine.update_risk_after_trade(
            trade_result='loss',
            trade_pnl_dollars=trade_pnl_dollars,
            trade_risk_dollars=trade_risk_dollars,
            trade_tier=trade_tier,
            playbook_name='Test_Playbook',
            current_day=date.today()
        )
        
        # pnl_R_account = pnl_$ / base_r = -100 / 100 = -1
        assert result['pnl_r_account'] == -1.0


class TestRiskEngineWiring:
    """Tests C) Wiring (intégration backtest minimal)"""
    
    def test_tier_sequence_loss_win_loss(self):
        """Simuler 3 trades: loss(2R) → win(1R) → loss(2R)
        Séquence de tiers appliqués: 2 → 1 → 2
        """
        engine = RiskEngine(initial_capital=5000.0)
        base_r = engine.state.base_r_unit_dollars  # 100
        
        # Trade 1: loss à tier=2 → tier devient 1
        assert engine.get_current_risk_tier() == 2
        engine.update_risk_after_trade(
            trade_result='loss',
            trade_pnl_dollars=-200.0,
            trade_risk_dollars=200.0,
            trade_tier=2,
            playbook_name='Test',
            current_day=date.today()
        )
        assert engine.get_current_risk_tier() == 1
        
        # Trade 2: win à tier=1 → tier remonte 2
        engine.update_risk_after_trade(
            trade_result='win',
            trade_pnl_dollars=150.0,
            trade_risk_dollars=100.0,
            trade_tier=1,
            playbook_name='Test',
            current_day=date.today()
        )
        assert engine.get_current_risk_tier() == 2
        
        # Trade 3: loss à tier=2 → tier devient 1
        engine.update_risk_after_trade(
            trade_result='loss',
            trade_pnl_dollars=-200.0,
            trade_risk_dollars=200.0,
            trade_tier=2,
            playbook_name='Test',
            current_day=date.today()
        )
        assert engine.get_current_risk_tier() == 1


class TestPlaybookAllowlist:
    """Tests pour allowlist/denylist playbooks"""
    
    def test_aggressive_allowlist_contains_baseline(self):
        """Vérifier que la allowlist contient les playbooks baseline"""
        assert 'News_Fade' in AGGRESSIVE_ALLOWLIST
        assert 'Session_Open_Scalp' in AGGRESSIVE_ALLOWLIST
        assert 'SCALP_Aplus_1_Mini_FVG_Retest_NY_Open' in AGGRESSIVE_ALLOWLIST
    
    def test_aggressive_denylist_contains_destructeurs(self):
        """Vérifier que la denylist contient les playbooks destructeurs"""
        assert 'London_Sweep_NY_Continuation' in AGGRESSIVE_DENYLIST
        assert 'BOS_Momentum_Scalp' in AGGRESSIVE_DENYLIST
        assert 'Power_Hour_Expansion' in AGGRESSIVE_DENYLIST
        assert 'DAY_Aplus_1_Liquidity_Sweep_OB_Retest' in AGGRESSIVE_DENYLIST
    
    def test_is_playbook_allowed_allowlist(self):
        """Vérifier que les playbooks allowlist sont autorisés"""
        engine = RiskEngine(initial_capital=5000.0)
        engine.state.trading_mode = 'AGGRESSIVE'
        
        allowed, reason = engine.is_playbook_allowed('News_Fade')
        assert allowed is True
        assert reason == 'OK'
    
    def test_is_playbook_allowed_denylist(self):
        """Vérifier que les playbooks denylist sont refusés"""
        engine = RiskEngine(initial_capital=5000.0)
        engine.state.trading_mode = 'AGGRESSIVE'
        
        allowed, reason = engine.is_playbook_allowed('London_Sweep_NY_Continuation')
        assert allowed is False
        assert 'DENYLIST' in reason


class TestKillSwitch:
    """Tests pour kill-switch playbook"""
    
    def test_killswitch_hard_stop(self):
        """Hard stop si Total_R ≤ -25R"""
        engine = RiskEngine(initial_capital=5000.0)
        
        # Simuler des pertes massives
        for i in range(26):
            engine.update_playbook_stats('Bad_Playbook', pnl_r=-1.0, is_win=False)
        
        assert 'Bad_Playbook' in engine.state.disabled_playbooks
        stats = engine.state.playbook_stats['Bad_Playbook']
        assert stats.disabled is True
        assert 'HARD STOP' in stats.disable_reason
    
    def test_killswitch_after_30_trades_low_pf(self):
        """Disable si PF < 0.85 après 30 trades (total_r reste ≤ -10)"""
        engine = RiskEngine(initial_capital=5000.0)
        
        # Simuler 30 trades avec mauvais PF mais total_r pas trop négatif
        # Pour trigger PF < 0.85, il faut: gross_profit / |gross_loss| < 0.85
        # Exemple: 10 wins (+1R each), 20 losses (-0.5R each) → PF = 10/10 = 1.0 (trop haut)
        # Ou: 8 wins (+1R), 22 losses (-0.4R) → PF = 8/8.8 = 0.91 (encore trop haut)
        # Il faut des pertes plus grosses: 12 wins (+0.5R), 18 losses (-0.5R) → PF = 6/9 = 0.67
        for i in range(30):
            if i < 12:  # 12 wins à +0.5R = +6R profit
                engine.update_playbook_stats('Low_PF_Playbook', pnl_r=0.5, is_win=True)
            else:  # 18 losses à -0.5R = -9R loss
                engine.update_playbook_stats('Low_PF_Playbook', pnl_r=-0.5, is_win=False)
        
        stats = engine.state.playbook_stats['Low_PF_Playbook']
        # Total R = +6 - 9 = -3R (pas assez pour trigger -10R)
        # PF = 6 / 9 = 0.67 < 0.85 → devrait trigger
        assert stats.profit_factor < KILLSWITCH_MIN_PF
        assert stats.disabled is True
        assert 'PF=' in stats.disable_reason


class TestCircuitBreakers:
    """Tests pour circuit breakers"""
    
    def test_stop_day_triggered(self):
        """Stop day si PnL_day ≤ -4R"""
        engine = RiskEngine(initial_capital=5000.0)
        
        # Simuler des pertes journalières
        engine.state.daily_pnl_r = -4.5
        
        result = engine.check_circuit_breakers(date.today())
        assert result['trading_allowed'] is False
        assert result['stop_day'] is True
        assert 'STOP DAY' in result['reason']
    
    def test_stop_run_triggered(self):
        """Stop run si MaxDD ≥ 20R"""
        engine = RiskEngine(initial_capital=5000.0)
        
        # Simuler un gros drawdown
        engine.state.max_drawdown_r = 21.0
        
        result = engine.check_circuit_breakers(date.today())
        assert result['trading_allowed'] is False
        assert result['stop_run'] is True
        assert 'STOP RUN' in result['reason']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
