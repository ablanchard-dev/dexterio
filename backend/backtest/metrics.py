"""
P0.5 - Audit Math - Définitions Verrouillées

Ce module contient les définitions EXACTES des métriques utilisées.
Toutes les formules sont documentées et testables.

DÉFINITIONS CLÉS (non négociables):

1. R (Risk Unit):
   - base_r_unit_$ = capital_initial * 0.02 (2%)
   - risk_$ = risque à l'entrée (distance SL * size), FIGÉ
   - r_multiple = pnl_$ / risk_$ (signé, performance normalisée du setup)
   - pnl_R_account = pnl_$ / base_r_unit_$ (impact compte)

2. Profit Factor (PF):
   - PF = gross_profit_R / abs(gross_loss_R)
   - BE (=0R) est EXCLU du calcul PF
   - Si gross_loss = 0: PF = +inf si profit > 0, else 0

3. Expectancy:
   - expectancy_R = mean(r_multiple) incluant BE

4. MaxDD (Drawdown):
   - MaxDD_run = max(peak_equity_R - trough_equity_R) sur equity curve
   - Calculé sur cumulative R (pas $)
"""
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def calculate_metrics(trades: List[Dict[str, Any]], playbooks: List[str] = None) -> Dict[str, Any]:
    """
    Calcule les métriques globales d'une liste de trades.
    
    FORMULES VERROUILLÉES:
    - PF = gross_profit_R / |gross_loss_R| (BE exclu)
    - Expectancy = mean(r_multiple) (BE inclus)
    - MaxDD = max drawdown sur equity curve en R
    
    Args:
        trades: Liste de dicts avec 'r_multiple', 'pnl_R_account', 'outcome', 'playbook'
        playbooks: Filtrer par playbooks (optionnel)
    
    Returns:
        Dict avec métriques calculées
    """
    if not trades:
        return _empty_metrics()
    
    # Filtrer par playbooks si spécifié
    if playbooks:
        trades = [t for t in trades if t.get("playbook") in playbooks]
    
    if not trades:
        return _empty_metrics()
    
    # Extraire les r_multiples
    r_multiples = [t.get("r_multiple", 0.0) for t in trades]
    pnl_r_accounts = [t.get("pnl_R_account", 0.0) for t in trades]
    outcomes = [t.get("outcome", "unknown") for t in trades]
    
    # Compteurs
    total_trades = len(trades)
    wins = sum(1 for o in outcomes if o == "win")
    losses = sum(1 for o in outcomes if o == "loss")
    breakevens = sum(1 for o in outcomes if o == "breakeven")
    
    # Total R
    total_r = sum(pnl_r_accounts)
    
    # Winrate
    winrate = (wins / total_trades * 100) if total_trades > 0 else 0.0
    
    # Gross profit/loss (en r_multiple, BE exclu)
    gross_profit_r = sum(r for r in r_multiples if r > 0)
    gross_loss_r = sum(r for r in r_multiples if r < 0)  # Négatif
    
    # PF = gross_profit / |gross_loss| (BE exclu)
    if gross_loss_r < 0:
        profit_factor = gross_profit_r / abs(gross_loss_r)
    else:
        profit_factor = float('inf') if gross_profit_r > 0 else 0.0
    
    # Expectancy = mean(r_multiple) incluant BE
    expectancy_r = sum(r_multiples) / len(r_multiples) if r_multiples else 0.0
    
    # MaxDD sur equity curve en R
    max_drawdown_r = _calculate_max_drawdown_r(trades)
    
    # Avg win/loss
    winning_r = [r for r in r_multiples if r > 0]
    losing_r = [r for r in r_multiples if r < 0]
    avg_win_r = sum(winning_r) / len(winning_r) if winning_r else 0.0
    avg_loss_r = sum(losing_r) / len(losing_r) if losing_r else 0.0
    
    # Max consecutive losses
    max_consecutive_losses = _max_consecutive_losses(outcomes)

    # Trades/day
    unique_days = sorted({t.get("date") for t in trades if t.get("date")})
    total_days = len(unique_days)
    trades_per_day = (total_trades / total_days) if total_days > 0 else 0.0

    return {
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "breakevens": breakevens,
        "winrate": winrate,
        "total_r": total_r,
        "gross_profit_r": gross_profit_r,
        "gross_loss_r": gross_loss_r,
        "profit_factor": profit_factor,
        "expectancy_r": expectancy_r,
        "avg_win_r": avg_win_r,
        "avg_loss_r": avg_loss_r,
        "max_drawdown_r": max_drawdown_r,
        "max_consecutive_losses": max_consecutive_losses,
        "total_days": total_days,
        "trades_per_day": trades_per_day,
    }


def _calculate_max_drawdown_r(trades: List[Dict[str, Any]]) -> float:
    """
    Calcule le MaxDD sur l'equity curve en R.
    
    MaxDD = max(peak - trough) sur cumulative R
    """
    if not trades:
        return 0.0
    
    # Construire equity curve
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    
    for t in trades:
        pnl_r = t.get("pnl_R_account", 0.0)
        equity += pnl_r
        
        if equity > peak:
            peak = equity
        
        drawdown = peak - equity
        if drawdown > max_dd:
            max_dd = drawdown
    
    return max_dd


def _max_consecutive_losses(outcomes: List[str]) -> int:
    """Calcule le nombre max de pertes consécutives."""
    max_consec = 0
    current = 0
    
    for o in outcomes:
        if o == "loss":
            current += 1
            max_consec = max(max_consec, current)
        else:
            current = 0
    
    return max_consec


def _empty_metrics() -> Dict[str, Any]:
    """Retourne des métriques vides."""
    return {
        "total_trades": 0,
        "wins": 0,
        "losses": 0,
        "breakevens": 0,
        "winrate": 0.0,
        "total_r": 0.0,
        "gross_profit_r": 0.0,
        "gross_loss_r": 0.0,
        "profit_factor": 0.0,
        "expectancy_r": 0.0,
        "avg_win_r": 0.0,
        "avg_loss_r": 0.0,
        "max_drawdown_r": 0.0,
        "max_consecutive_losses": 0,
        "total_days": 0,
        "trades_per_day": 0.0,
    }


def calculate_monthly_metrics(trades: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Calcule les métriques par mois.
    
    Args:
        trades: Liste de trades avec champ 'month' (format "YYYY-MM")
    
    Returns:
        Dict {month: metrics}
    """
    if not trades:
        return {}
    
    # Grouper par mois
    by_month: Dict[str, List[Dict[str, Any]]] = {}
    for t in trades:
        month = t.get("month") or "unknown"
        if month not in by_month:
            by_month[month] = []
        by_month[month].append(t)
    
    # Calculer métriques par mois
    result = {}
    for month, month_trades in sorted(by_month.items()):
        result[month] = calculate_metrics(month_trades)
    
    return result


def calculate_playbook_metrics(trades: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Calcule les métriques par playbook.
    
    Args:
        trades: Liste de trades avec champ 'playbook'
    
    Returns:
        Dict {playbook: metrics}
    """
    if not trades:
        return {}
    
    # Grouper par playbook
    by_playbook: Dict[str, List[Dict[str, Any]]] = {}
    for t in trades:
        pb = t.get("playbook") or "UNKNOWN"
        if pb not in by_playbook:
            by_playbook[pb] = []
        by_playbook[pb].append(t)
    
    # Calculer métriques par playbook
    result = {}
    for pb, pb_trades in sorted(by_playbook.items()):
        result[pb] = calculate_metrics(pb_trades)
    
    return result


def calculate_regime_metrics(trades: List[Dict[str, Any]], atr_quantiles: Dict[str, float] = None) -> Dict[str, Dict[str, Any]]:
    """
    Calcule les métriques par régime de volatilité.
    
    Args:
        trades: Liste de trades avec champ 'atr_daily' (optionnel)
        atr_quantiles: Dict {Q1: threshold1, Q2: threshold2, ...}
    
    Returns:
        Dict {regime: metrics}
    """
    # Pour l'instant, retourner vide (à implémenter avec données ATR)
    return {}


def export_trades_csv(trades: List[Dict[str, Any]], output_path: Path) -> str:
    """
    Exporte les trades en CSV avec tous les champs requis.
    
    Champs obligatoires:
    - timestamp, symbol, playbook, entry/exit, pnl_$, risk_$, r_multiple,
      risk_tier, pnl_R_account, cumulative_R, outcome, exit_reason
    """
    if not trades:
        logger.warning("No trades to export")
        return str(output_path)
    
    fieldnames = [
        "trade_id",
        "timestamp_entry",
        "timestamp_exit",
        "date",
        "month",
        "symbol",
        "playbook",
        "direction",
        "trade_type",
        "quality",
        "entry_price",
        "exit_price",
        "stop_loss",
        "position_size",
        "pnl_dollars",
        "risk_dollars",
        "r_multiple",
        "risk_tier",
        "pnl_R_account",
        "cumulative_R",
        "outcome",
        "exit_reason",
    ]
    
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        
        for t in trades:
            # Convertir timestamps en strings
            row = t.copy()
            if row.get("timestamp_entry"):
                row["timestamp_entry"] = str(row["timestamp_entry"])
            if row.get("timestamp_exit"):
                row["timestamp_exit"] = str(row["timestamp_exit"])
            writer.writerow(row)
    
    logger.info(f"Exported {len(trades)} trades to {output_path}")
    return str(output_path)


def export_daily_summary(trades: List[Dict[str, Any]], output_path: Path) -> str:
    """
    Exporte un résumé journalier.
    
    Format:
    {
        "YYYY-MM-DD": {
            "pnl_r": float,
            "trades": int,
            "setups_raw": int (si disponible),
            "setups_passed": int (si disponible),
            "by_playbook": {playbook: pnl_r}
        }
    }
    """
    if not trades:
        logger.warning("No trades for daily summary")
        return str(output_path)
    
    # Grouper par date
    by_date: Dict[str, List[Dict[str, Any]]] = {}
    for t in trades:
        date_str = t.get("date") or "unknown"
        if date_str not in by_date:
            by_date[date_str] = []
        by_date[date_str].append(t)
    
    # Calculer résumé par jour
    summary = {}
    for date_str, day_trades in sorted(by_date.items()):
        # PnL total du jour
        pnl_r = sum(t.get("pnl_R_account", 0.0) for t in day_trades)
        
        # Par playbook
        by_pb: Dict[str, float] = {}
        for t in day_trades:
            pb = t.get("playbook") or "UNKNOWN"
            by_pb[pb] = by_pb.get(pb, 0.0) + t.get("pnl_R_account", 0.0)
        
        summary[date_str] = {
            "pnl_r": round(pnl_r, 4),
            "trades": len(day_trades),
            "by_playbook": {k: round(v, 4) for k, v in by_pb.items()},
        }
    
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"Exported daily summary for {len(summary)} days to {output_path}")
    return str(output_path)


# ============================================================================
# TESTS ASSERTIONS (pour audit math)
# ============================================================================

def validate_metrics_math():
    """
    Fonction de validation des définitions math.
    À appeler pour vérifier la cohérence.
    """
    # Test 1: PF calculation
    test_trades = [
        {"r_multiple": 2.0, "pnl_R_account": 2.0, "outcome": "win"},
        {"r_multiple": -1.0, "pnl_R_account": -1.0, "outcome": "loss"},
        {"r_multiple": 3.0, "pnl_R_account": 3.0, "outcome": "win"},
        {"r_multiple": -1.0, "pnl_R_account": -1.0, "outcome": "loss"},
        {"r_multiple": 0.0, "pnl_R_account": 0.0, "outcome": "breakeven"},  # BE exclu du PF
    ]
    
    metrics = calculate_metrics(test_trades)
    
    # PF = (2+3) / |(-1)+(-1)| = 5 / 2 = 2.5
    assert abs(metrics["profit_factor"] - 2.5) < 0.001, f"PF error: {metrics['profit_factor']}"
    
    # Expectancy = (2 + -1 + 3 + -1 + 0) / 5 = 3/5 = 0.6
    assert abs(metrics["expectancy_r"] - 0.6) < 0.001, f"Expectancy error: {metrics['expectancy_r']}"
    
    # Total R = 2 - 1 + 3 - 1 + 0 = 3
    assert abs(metrics["total_r"] - 3.0) < 0.001, f"Total R error: {metrics['total_r']}"
    
    # WR = 2/5 = 40%
    assert abs(metrics["winrate"] - 40.0) < 0.001, f"WR error: {metrics['winrate']}"
    
    logger.info("✅ Validation math OK: PF, Expectancy, Total R, WR")
    return True


if __name__ == "__main__":
    validate_metrics_math()
    print("All math validations passed!")
