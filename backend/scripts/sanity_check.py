#!/usr/bin/env python3
"""
Sanity Check - PATCH D FINAL
Script de validation pour vérifier la santé du bot avant un backtest complet.

Usage:
    python scripts/sanity_check.py --duration 1d
    python scripts/sanity_check.py --duration 5d
    python scripts/sanity_check.py --duration 1m
"""
import sys
import logging
import time
from pathlib import Path
from datetime import datetime, timedelta
import argparse

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backtest.engine import BacktestEngine
from models.backtest import BacktestConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_sanity_check(duration: str = "5d"):
    """
    Lance un backtest court pour validation.
    
    Args:
        duration: "1d" (1 jour), "5d" (5 jours) ou "1m" (1 mois)
    """
    logger.info("=" * 80)
    logger.info(f"SANITY CHECK - Duration: {duration}")
    logger.info("=" * 80)
    
    # Calculer dates
    end_date = datetime(2024, 6, 12, 23, 59, 59)  # Date de fin des données
    
    if duration == "1d":
        start_date = end_date - timedelta(days=1)
        run_name = "sanity_check_1day"
    elif duration == "5d":
        start_date = end_date - timedelta(days=5)
        run_name = "sanity_check_5days"
    elif duration == "1m":
        start_date = end_date - timedelta(days=30)
        run_name = "sanity_check_1month"
    else:
        raise ValueError(f"Invalid duration: {duration}")
    
    logger.info(f"Period: {start_date.date()} to {end_date.date()}")
    
    # Configuration
    config = BacktestConfig(
        run_name=run_name,
        start_date=start_date,
        end_date=end_date,
        symbols=['SPY', 'QQQ'],
        data_paths=[
            '/app/data/historical/1m/SPY.parquet',
            '/app/data/historical/1m/QQQ.parquet'
        ],
        initial_capital=10000.0,
        trading_mode='AGGRESSIVE',
        trade_types=['DAILY', 'SCALP']
    )
    
    # PROFILING: Mesurer les temps
    timings = {}
    
    # Data load
    t0 = time.time()
    engine = BacktestEngine(config)
    engine.load_data()
    timings['data_load'] = time.time() - t0
    
    # Run backtest (inclut pattern detection, setup generation, risk filtering, execution)
    t0 = time.time()
    result = engine.run()
    timings['total_run'] = time.time() - t0
    
    # Générer rapport détaillé
    logger.info("\n" + "=" * 80)
    logger.info("SANITY CHECK REPORT")
    logger.info("=" * 80)
    
    # 0. PROFILING
    logger.info("\n⏱️ PROFILING")
    logger.info(f"   Data Load: {timings['data_load']:.2f}s")
    logger.info(f"   Total Run: {timings['total_run']:.2f}s")
    logger.info(f"   Speed: {timings['total_run'] / result.bars_processed * 1000:.2f}ms per bar")
    
    # 1. Métriques globales
    logger.info("\n📊 GLOBAL METRICS")
    logger.info(f"   Total Trades: {result.total_trades}")
    logger.info(f"   Total R: {result.total_r:.2f}R")
    logger.info(f"   Profit Factor: {result.profit_factor:.2f}")
    logger.info(f"   Win Rate: {result.win_rate:.1f}%")
    logger.info(f"   Expectancy (R/trade): {result.expectancy_r:.2f}R")
    logger.info(f"   Max Drawdown: {result.max_drawdown_r:.2f}R")
    
    # 2. Trades par playbook
    logger.info("\n📝 TRADES BY PLAYBOOK")
    playbook_stats = {}
    for trade in result.trades:
        pb_name = trade.playbook_name or "UNKNOWN"
        if pb_name not in playbook_stats:
            playbook_stats[pb_name] = {'count': 0, 'r': 0.0, 'wins': 0}
        playbook_stats[pb_name]['count'] += 1
        playbook_stats[pb_name]['r'] += trade.pnl_r
        if trade.pnl_r > 0:
            playbook_stats[pb_name]['wins'] += 1
    
    # Sort by R descending
    sorted_playbooks = sorted(playbook_stats.items(), key=lambda x: x[1]['r'], reverse=True)
    
    for pb_name, stats in sorted_playbooks:
        wr = (stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0
        logger.info(f"   {pb_name:<40} | Trades: {stats['count']:3d} | Total R: {stats['r']:+7.2f} | WR: {wr:5.1f}%")
    
    # 3. Trades par symbole
    logger.info("\n📈 TRADES BY SYMBOL")
    symbol_stats = {}
    for trade in result.trades:
        sym = trade.symbol
        if sym not in symbol_stats:
            symbol_stats[sym] = {'count': 0, 'r': 0.0}
        symbol_stats[sym]['count'] += 1
        symbol_stats[sym]['r'] += trade.pnl_r
    
    for sym, stats in symbol_stats.items():
        logger.info(f"   {sym}: {stats['count']} trades, {stats['r']:+.2f}R")
    
    # 4. ANTI-SPAM VERIFICATION (PATCH D FINAL)
    logger.info("\n🛡️ ANTI-SPAM VERIFICATION")
    
    # Métriques directes du moteur
    logger.info(f"   Total Blocked by Cooldown: {engine.blocked_by_cooldown}")
    logger.info(f"   Total Blocked by Session Limit: {engine.blocked_by_session_limit}")
    
    if engine.blocked_by_cooldown > 0:
        logger.info("   Blocked by Cooldown (by playbook):")
        for pb, count in sorted(engine.blocked_by_cooldown_details.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"      {pb}: {count}")
    
    if engine.blocked_by_session_limit > 0:
        logger.info("   Blocked by Session Limit (by playbook):")
        for pb, count in sorted(engine.blocked_by_session_limit_details.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"      {pb}: {count}")
    
    # Vérifier doublons résiduels (ne devrait pas exister si anti-spam fonctionne)
    trades_by_pb_sym = {}
    spam_detected = []
    
    for trade in result.trades:
        key = (trade.symbol, trade.playbook_name)
        if key not in trades_by_pb_sym:
            trades_by_pb_sym[key] = []
        trades_by_pb_sym[key].append(trade)
    
    for (sym, pb), trades in trades_by_pb_sym.items():
        trades_sorted = sorted(trades, key=lambda t: t.entry_time)
        for i in range(1, len(trades_sorted)):
            prev_trade = trades_sorted[i-1]
            curr_trade = trades_sorted[i]
            time_diff = (curr_trade.entry_time - prev_trade.entry_time).total_seconds() / 60.0
            if time_diff < 15:
                spam_detected.append({
                    'symbol': sym,
                    'playbook': pb,
                    'time_diff_minutes': time_diff,
                    'prev_entry': prev_trade.entry_time,
                    'curr_entry': curr_trade.entry_time
                })
    
    if spam_detected:
        logger.warning(f"   ⚠️ {len(spam_detected)} residual spam trade(s) detected (< 15min cooldown):")
        for spam in spam_detected[:5]:
            logger.warning(f"      {spam['symbol']} {spam['playbook']}: {spam['time_diff_minutes']:.1f}min between {spam['prev_entry']} and {spam['curr_entry']}")
    else:
        logger.info("   ✅ No residual spam - Cooldown working correctly")
    
    # 5. Top 3 / Bottom 3 playbooks
    logger.info("\n🏆 TOP 3 PLAYBOOKS (by R)")
    for i, (pb_name, stats) in enumerate(sorted_playbooks[:3], 1):
        wr = (stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0
        logger.info(f"   {i}. {pb_name}: {stats['r']:+.2f}R ({stats['count']} trades, {wr:.1f}% WR)")
    
    logger.info("\n💥 BOTTOM 3 PLAYBOOKS (by R)")
    for i, (pb_name, stats) in enumerate(sorted_playbooks[-3:][::-1], 1):
        wr = (stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0
        logger.info(f"   {i}. {pb_name}: {stats['r']:+.2f}R ({stats['count']} trades, {wr:.1f}% WR)")
    
    # 6. Verdict
    logger.info("\n" + "=" * 80)
    logger.info("VERDICT")
    logger.info("=" * 80)
    
    issues = []
    
    # Check 1: Au moins 10 trades
    if result.total_trades < 10:
        issues.append(f"❌ Too few trades ({result.total_trades} < 10)")
    else:
        logger.info(f"✅ Trade count: {result.total_trades} trades")
    
    # Check 2: Total R positif (ou pas trop négatif)
    if result.total_r < -10:
        issues.append(f"❌ Total R too negative ({result.total_r:.2f}R)")
    else:
        logger.info(f"✅ Total R: {result.total_r:+.2f}R")
    
    # Check 3: Pas de spam
    if spam_detected:
        issues.append(f"⚠️ Anti-spam may not be working ({len(spam_detected)} spam trades)")
    else:
        logger.info("✅ Anti-spam: No spam detected")
    
    # Check 4: MaxDD acceptable
    if result.max_drawdown_r > 20:
        issues.append(f"⚠️ High drawdown ({result.max_drawdown_r:.2f}R > 20R)")
    else:
        logger.info(f"✅ Max Drawdown: {result.max_drawdown_r:.2f}R")
    
    # Final verdict
    logger.info("\n" + "=" * 80)
    if issues:
        logger.warning("⚠️ SANITY CHECK: ISSUES DETECTED")
        for issue in issues:
            logger.warning(f"   {issue}")
        logger.warning("\n   Recommandation: Fix issues before running 6-month backtest")
        return False
    else:
        logger.info("✅ SANITY CHECK: PASS")
        logger.info("   Bot is ready for full backtest")
        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Sanity Check for DexterioBOT')
    parser.add_argument('--duration', type=str, default='1d', choices=['1d', '5d', '1m'],
                        help='Duration: 1d (1 day), 5d (5 days) or 1m (1 month)')
    
    args = parser.parse_args()
    
    success = run_sanity_check(args.duration)
    sys.exit(0 if success else 1)
