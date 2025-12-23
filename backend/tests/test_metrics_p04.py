"""
P0.5 - Tests Audit Math pour backtest/metrics.py

Vérifie que les formules sont correctement implémentées.
"""
import pytest
from backtest.metrics import (
    calculate_metrics,
    calculate_monthly_metrics,
    calculate_playbook_metrics,
    _calculate_max_drawdown_r,
    _max_consecutive_losses,
    validate_metrics_math,
)


class TestMetricsDefinitions:
    """Tests des définitions math verrouillées."""
    
    def test_profit_factor_be_excluded(self):
        """PF = gross_profit / |gross_loss| avec BE exclu."""
        trades = [
            {"r_multiple": 2.0, "pnl_R_account": 2.0, "outcome": "win"},
            {"r_multiple": -1.0, "pnl_R_account": -1.0, "outcome": "loss"},
            {"r_multiple": 0.0, "pnl_R_account": 0.0, "outcome": "breakeven"},
        ]
        
        metrics = calculate_metrics(trades)
        
        # PF = 2.0 / |-1.0| = 2.0 (BE non inclus)
        assert metrics["profit_factor"] == 2.0
    
    def test_profit_factor_no_loss(self):
        """PF = +inf si aucune perte."""
        trades = [
            {"r_multiple": 2.0, "pnl_R_account": 2.0, "outcome": "win"},
            {"r_multiple": 1.0, "pnl_R_account": 1.0, "outcome": "win"},
        ]
        
        metrics = calculate_metrics(trades)
        
        assert metrics["profit_factor"] == float('inf')
    
    def test_expectancy_includes_be(self):
        """Expectancy = mean(r_multiple) incluant BE."""
        trades = [
            {"r_multiple": 3.0, "pnl_R_account": 3.0, "outcome": "win"},
            {"r_multiple": -1.0, "pnl_R_account": -1.0, "outcome": "loss"},
            {"r_multiple": 0.0, "pnl_R_account": 0.0, "outcome": "breakeven"},
        ]
        
        metrics = calculate_metrics(trades)
        
        # Expectancy = (3 - 1 + 0) / 3 = 2/3 ≈ 0.667
        assert abs(metrics["expectancy_r"] - 0.6667) < 0.01
    
    def test_max_drawdown_calculation(self):
        """MaxDD = max(peak - trough) sur equity curve en R."""
        trades = [
            {"pnl_R_account": 2.0},   # equity = 2, peak = 2
            {"pnl_R_account": 1.0},   # equity = 3, peak = 3
            {"pnl_R_account": -4.0},  # equity = -1, DD = 4
            {"pnl_R_account": 1.0},   # equity = 0, DD = 3
        ]
        
        max_dd = _calculate_max_drawdown_r(trades)
        
        # MaxDD = 3 - (-1) = 4
        assert max_dd == 4.0
    
    def test_winrate_calculation(self):
        """WR = wins / total_trades * 100."""
        trades = [
            {"r_multiple": 1.0, "pnl_R_account": 1.0, "outcome": "win"},
            {"r_multiple": 1.0, "pnl_R_account": 1.0, "outcome": "win"},
            {"r_multiple": -1.0, "pnl_R_account": -1.0, "outcome": "loss"},
            {"r_multiple": 0.0, "pnl_R_account": 0.0, "outcome": "breakeven"},
        ]
        
        metrics = calculate_metrics(trades)
        
        # WR = 2/4 = 50%
        assert metrics["winrate"] == 50.0
    
    def test_max_consecutive_losses(self):
        """Max pertes consécutives."""
        outcomes = ["win", "loss", "loss", "loss", "win", "loss", "loss"]
        
        max_consec = _max_consecutive_losses(outcomes)
        
        assert max_consec == 3
    
    def test_total_r_calculation(self):
        """Total R = sum(pnl_R_account)."""
        trades = [
            {"r_multiple": 2.0, "pnl_R_account": 2.0, "outcome": "win"},
            {"r_multiple": -1.0, "pnl_R_account": -1.0, "outcome": "loss"},
            {"r_multiple": 3.0, "pnl_R_account": 3.0, "outcome": "win"},
        ]
        
        metrics = calculate_metrics(trades)
        
        # Total R = 2 - 1 + 3 = 4
        assert metrics["total_r"] == 4.0
    
    def test_empty_trades(self):
        """Gérer liste vide."""
        metrics = calculate_metrics([])
        
        assert metrics["total_trades"] == 0
        assert metrics["profit_factor"] == 0.0
        assert metrics["expectancy_r"] == 0.0


class TestMonthlyMetrics:
    """Tests des métriques par mois."""
    
    def test_monthly_grouping(self):
        """Groupement correct par mois."""
        trades = [
            {"r_multiple": 1.0, "pnl_R_account": 1.0, "outcome": "win", "month": "2025-11"},
            {"r_multiple": -1.0, "pnl_R_account": -1.0, "outcome": "loss", "month": "2025-11"},
            {"r_multiple": 2.0, "pnl_R_account": 2.0, "outcome": "win", "month": "2025-12"},
        ]
        
        monthly = calculate_monthly_metrics(trades)
        
        assert "2025-11" in monthly
        assert "2025-12" in monthly
        assert monthly["2025-11"]["total_trades"] == 2
        assert monthly["2025-12"]["total_trades"] == 1


class TestPlaybookMetrics:
    """Tests des métriques par playbook."""
    
    def test_playbook_grouping(self):
        """Groupement correct par playbook."""
        trades = [
            {"r_multiple": 1.0, "pnl_R_account": 1.0, "outcome": "win", "playbook": "News_Fade"},
            {"r_multiple": 2.0, "pnl_R_account": 2.0, "outcome": "win", "playbook": "SCALP_Aplus_1"},
        ]
        
        by_playbook = calculate_playbook_metrics(trades)
        
        assert "News_Fade" in by_playbook
        assert "SCALP_Aplus_1" in by_playbook
        assert by_playbook["News_Fade"]["total_r"] == 1.0
        assert by_playbook["SCALP_Aplus_1"]["total_r"] == 2.0


class TestMathValidation:
    """Test de la fonction de validation."""
    
    def test_validate_metrics_math(self):
        """Valide que les formules sont correctes."""
        result = validate_metrics_math()
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
