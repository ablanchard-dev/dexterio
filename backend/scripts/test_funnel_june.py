"""
Backtest juin 2025 avec funnel tracking
Utilise BacktestEngine pour parcourir réellement les données historiques
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backtest.engine import BacktestEngine
from models.backtest import BacktestConfig
import json

config = BacktestConfig(
    run_name='funnel_june2025',
    symbols=['SPY'],
    data_paths=['data/historical/1m/SPY.parquet'],
    initial_capital=100000.0,
    trading_mode='AGGRESSIVE',
    trade_types=['DAILY', 'SCALP'],
    output_dir='backend/results'
)

print("="*80)
print("BACKTEST JUIN 2025 AVEC FUNNEL")
print("="*80)

engine = BacktestEngine(config)
engine.load_data()

print(f"✅ Données chargées: {len(engine.data)} bars")

# Run backtest
result = engine.run()

print(f"\n✅ Backtest terminé")
print(f"   Bars processed: {result.total_bars}")
print(f"   Trades: {result.total_trades}")

# Afficher funnel
funnel_path = Path('backend/results/funnel_by_playbook.json')
if funnel_path.exists():
    with open(funnel_path) as f:
        funnel = json.load(f)
    
    print(f"\n📊 FUNNEL RESULTS:")
    for pb_name in sorted(funnel.keys()):
        timefilter_ny = 0
        for symbol_data in funnel[pb_name].values():
            for date_data in symbol_data.values():
                for r in date_data.get('top_reject_reasons', []):
                    if 'timefilter_outside_window:NY' in r.get('reason', ''):
                        timefilter_ny += r.get('count', 0)
        
        status = "✅" if timefilter_ny == 0 else f"❌ {timefilter_ny}x"
        print(f"  {pb_name:<40} timefilter:NY {status}")
else:
    print("\n⚠️  Funnel non généré")
