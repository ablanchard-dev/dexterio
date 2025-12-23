"""
P0.6.2 - News_Fade Breakdown / Diagnostic

Segmentation des trades par:
1. Fenêtre horaire (NY time)
2. Régime volatilité (ATR daily buckets)
3. Symbol (SPY vs QQQ)
4. Type de sortie (exit_reason)

Export: breakdown_<playbook>.json avec PF/expectancy/Total_R par segment
"""
import json
import logging
from datetime import datetime, time
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd

from backtest.metrics import calculate_metrics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# TIME BUCKETS (NY Time)
# ============================================================================

TIME_BUCKETS = [
    ("09:30-10:00", time(9, 30), time(10, 0)),
    ("10:00-11:30", time(10, 0), time(11, 30)),
    ("11:30-14:00", time(11, 30), time(14, 0)),
    ("14:00-16:00", time(14, 0), time(16, 0)),
]


def get_time_bucket(timestamp) -> str:
    """Retourne le bucket horaire pour un timestamp."""
    if timestamp is None:
        return "unknown"
    
    # Convertir en datetime si nécessaire
    if isinstance(timestamp, str):
        timestamp = pd.to_datetime(timestamp)
    
    t = timestamp.time()
    
    for bucket_name, start, end in TIME_BUCKETS:
        if start <= t < end:
            return bucket_name
    
    return "outside_hours"


# ============================================================================
# VOLATILITY REGIME (ATR daily buckets)
# ============================================================================

def calculate_volatility_regime(trades_df: pd.DataFrame, atr_col: str = None) -> pd.DataFrame:
    """
    Ajoute une colonne 'vol_regime' (LOW/MID/HIGH) basée sur l'ATR daily.
    
    Si atr_col n'est pas disponible, utilise un proxy basé sur le range daily.
    """
    df = trades_df.copy()
    
    # Pour l'instant, utiliser un placeholder (à améliorer avec vraies données ATR)
    # On utilise la variance des pnl_R_account par jour comme proxy
    df['vol_regime'] = 'MID'  # Default
    
    return df


# ============================================================================
# BREAKDOWN GENERATOR
# ============================================================================

def generate_breakdown(
    trades_csv_path: str,
    output_path: str = None,
    playbook_filter: str = None,
) -> Dict[str, Any]:
    """
    Génère un breakdown détaillé des trades.
    
    Args:
        trades_csv_path: Chemin vers le fichier trades CSV
        output_path: Chemin de sortie pour le JSON (optionnel)
        playbook_filter: Filtrer par playbook (optionnel)
    
    Returns:
        Dict avec les breakdowns par segment
    """
    # Charger les trades
    df = pd.read_csv(trades_csv_path)
    
    if df.empty:
        logger.warning("No trades to analyze")
        return {}
    
    # Filtrer par playbook si spécifié
    if playbook_filter:
        df = df[df['playbook'] == playbook_filter]
        if df.empty:
            logger.warning(f"No trades for playbook {playbook_filter}")
            return {}
    
    # Convertir timestamps
    df['timestamp_entry'] = pd.to_datetime(df['timestamp_entry'])
    
    # Ajouter colonnes de segmentation
    df['time_bucket'] = df['timestamp_entry'].apply(get_time_bucket)
    df = calculate_volatility_regime(df)
    
    # Préparer les données pour calculate_metrics
    trades_list = df.to_dict('records')
    
    # Calculer les métriques globales
    global_metrics = calculate_metrics(trades_list)
    
    # Breakdown par dimension
    breakdown = {
        "playbook": playbook_filter or "ALL",
        "total_trades": len(df),
        "global_metrics": global_metrics,
        "by_time_bucket": {},
        "by_symbol": {},
        "by_exit_reason": {},
        "by_time_x_symbol": {},
    }
    
    # 1) Par fenêtre horaire
    for bucket in df['time_bucket'].unique():
        bucket_trades = df[df['time_bucket'] == bucket].to_dict('records')
        breakdown["by_time_bucket"][bucket] = calculate_metrics(bucket_trades)
    
    # 2) Par symbol
    for symbol in df['symbol'].unique():
        symbol_trades = df[df['symbol'] == symbol].to_dict('records')
        breakdown["by_symbol"][symbol] = calculate_metrics(symbol_trades)
    
    # 3) Par exit_reason
    if 'exit_reason' in df.columns:
        for reason in df['exit_reason'].dropna().unique():
            reason_trades = df[df['exit_reason'] == reason].to_dict('records')
            breakdown["by_exit_reason"][str(reason)] = calculate_metrics(reason_trades)
    
    # 4) Croisement time_bucket x symbol
    for bucket in df['time_bucket'].unique():
        for symbol in df['symbol'].unique():
            key = f"{bucket}_{symbol}"
            cross_trades = df[(df['time_bucket'] == bucket) & (df['symbol'] == symbol)].to_dict('records')
            if cross_trades:
                breakdown["by_time_x_symbol"][key] = calculate_metrics(cross_trades)
    
    # Identifier les segments profitables et destructeurs
    breakdown["analysis"] = analyze_segments(breakdown)
    
    # Export JSON
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(breakdown, f, indent=2, default=str)
        logger.info(f"Breakdown exported to {output_path}")
    
    return breakdown


def analyze_segments(breakdown: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyse les segments pour identifier les profitables et destructeurs.
    
    Critères:
    - Profitable: PF >= 1.15 ET expectancy >= +0.05R
    - Destructeur: PF < 0.85
    """
    analysis = {
        "profitable_segments": [],
        "destructive_segments": [],
        "neutral_segments": [],
    }
    
    # Analyser time_buckets
    for bucket, metrics in breakdown.get("by_time_bucket", {}).items():
        segment_info = {
            "dimension": "time_bucket",
            "value": bucket,
            "metrics": metrics,
        }
        
        pf = metrics.get("profit_factor", 0)
        exp = metrics.get("expectancy_r", 0)
        trades = metrics.get("total_trades", 0)
        
        if trades < 10:
            segment_info["note"] = "insufficient_sample"
            analysis["neutral_segments"].append(segment_info)
        elif pf >= 1.15 and exp >= 0.05:
            analysis["profitable_segments"].append(segment_info)
        elif pf < 0.85:
            analysis["destructive_segments"].append(segment_info)
        else:
            analysis["neutral_segments"].append(segment_info)
    
    # Analyser symbols
    for symbol, metrics in breakdown.get("by_symbol", {}).items():
        segment_info = {
            "dimension": "symbol",
            "value": symbol,
            "metrics": metrics,
        }
        
        pf = metrics.get("profit_factor", 0)
        exp = metrics.get("expectancy_r", 0)
        trades = metrics.get("total_trades", 0)
        
        if trades < 10:
            segment_info["note"] = "insufficient_sample"
            analysis["neutral_segments"].append(segment_info)
        elif pf >= 1.15 and exp >= 0.05:
            analysis["profitable_segments"].append(segment_info)
        elif pf < 0.85:
            analysis["destructive_segments"].append(segment_info)
        else:
            analysis["neutral_segments"].append(segment_info)
    
    # Summary
    analysis["summary"] = {
        "total_profitable": len(analysis["profitable_segments"]),
        "total_destructive": len(analysis["destructive_segments"]),
        "total_neutral": len(analysis["neutral_segments"]),
        "recommendation": _generate_recommendation(analysis),
    }
    
    return analysis


def _generate_recommendation(analysis: Dict[str, Any]) -> str:
    """Génère une recommandation basée sur l'analyse."""
    profitable = analysis["profitable_segments"]
    destructive = analysis["destructive_segments"]
    
    if not profitable and destructive:
        return "NO_EDGE: Aucun segment profitable identifié. Considérer désactiver le playbook."
    elif profitable and destructive:
        return f"FILTER_NEEDED: {len(profitable)} segments profitables, {len(destructive)} segments destructeurs. Ajouter timefilter pour exclure les segments destructeurs."
    elif profitable and not destructive:
        return f"EDGE_CONFIRMED: {len(profitable)} segments profitables identifiés. Playbook OK."
    else:
        return "INCONCLUSIVE: Pas assez de données pour conclure. Étendre la période de test."


def print_breakdown_summary(breakdown: Dict[str, Any]):
    """Affiche un résumé du breakdown."""
    print("\n" + "="*80)
    print(f"BREAKDOWN ANALYSIS: {breakdown.get('playbook', 'ALL')}")
    print("="*80)
    
    global_m = breakdown.get("global_metrics", {})
    print(f"\nGlobal: {global_m.get('total_trades', 0)} trades, "
          f"WR={global_m.get('winrate', 0):.1f}%, "
          f"PF={global_m.get('profit_factor', 0):.2f}, "
          f"Exp={global_m.get('expectancy_r', 0):.4f}R")
    
    print("\n--- BY TIME BUCKET ---")
    print(f"{'Bucket':<15} {'Trades':>8} {'WR':>8} {'Total_R':>10} {'PF':>8} {'Exp':>8}")
    print("-"*60)
    
    for bucket, m in sorted(breakdown.get("by_time_bucket", {}).items()):
        print(f"{bucket:<15} {m.get('total_trades', 0):>8} "
              f"{m.get('winrate', 0):>7.1f}% "
              f"{m.get('total_r', 0):>+9.2f}R "
              f"{m.get('profit_factor', 0):>7.2f} "
              f"{m.get('expectancy_r', 0):>+7.4f}R")
    
    print("\n--- BY SYMBOL ---")
    for symbol, m in breakdown.get("by_symbol", {}).items():
        print(f"{symbol}: {m.get('total_trades', 0)} trades, "
              f"WR={m.get('winrate', 0):.1f}%, "
              f"PF={m.get('profit_factor', 0):.2f}, "
              f"Total_R={m.get('total_r', 0):+.2f}R")
    
    analysis = breakdown.get("analysis", {})
    summary = analysis.get("summary", {})
    print(f"\n📊 RECOMMENDATION: {summary.get('recommendation', 'N/A')}")
    
    if analysis.get("profitable_segments"):
        print(f"\n✅ Segments profitables:")
        for seg in analysis["profitable_segments"]:
            print(f"   - {seg['dimension']}={seg['value']}: "
                  f"PF={seg['metrics'].get('profit_factor', 0):.2f}, "
                  f"Exp={seg['metrics'].get('expectancy_r', 0):.4f}R")
    
    if analysis.get("destructive_segments"):
        print(f"\n❌ Segments destructeurs:")
        for seg in analysis["destructive_segments"]:
            print(f"   - {seg['dimension']}={seg['value']}: "
                  f"PF={seg['metrics'].get('profit_factor', 0):.2f}, "
                  f"Exp={seg['metrics'].get('expectancy_r', 0):.4f}R")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m backtest.breakdown <trades.csv> [playbook_name]")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    playbook = sys.argv[2] if len(sys.argv) > 2 else None
    
    output = Path(csv_path).parent / f"breakdown_{playbook or 'all'}.json"
    
    breakdown = generate_breakdown(csv_path, str(output), playbook)
    print_breakdown_summary(breakdown)
