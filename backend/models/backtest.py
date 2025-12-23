"""
Backtest Models - Phase 2.3
Configuration et résultats pour le moteur de backtest
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path


class BacktestConfig(BaseModel):
    """Configuration pour un run de backtest"""
    
    # Data source
    data_paths: List[str]  # Chemins vers fichiers Parquet
    symbols: List[str] = ['SPY', 'QQQ']
    
    # Trading parameters
    trading_mode: str = 'SAFE'  # SAFE ou AGGRESSIVE
    trade_types: List[str] = ['DAILY', 'SCALP']  # Types de trades à tester
    
    # Capital
    initial_capital: float = 50000.0
    
    # Risk parameters (héritées du RiskEngine)
    base_risk_pct: float = 0.02  # 2%
    reduced_risk_pct: float = 0.01  # 1%
    max_daily_loss_pct: float = 0.03  # -3%
    max_daily_loss_r: float = 3.0  # -3R
    max_consecutive_losses: int = 3
    max_drawdown_pct: float = 0.10  # -10%
    
    # Execution
    slippage_pct: float = 0.0002  # 0.02% slippage
    
    # Output
    output_dir: str = '/app/data/backtest_results'
    save_trades: bool = True
    save_equity_curve: bool = True
    generate_report: bool = True
    
    # Timeframe (pour reconstruction multi-TF)
    base_timeframe: str = '1m'
    
    # Run metadata
    run_name: Optional[str] = None
    run_timestamp: datetime = Field(default_factory=datetime.now)


class TradeResult(BaseModel):
    """Résultat d'un trade individuel dans le backtest"""
    trade_id: str
    timestamp_entry: datetime
    timestamp_exit: datetime
    duration_minutes: float
    
    symbol: str
    direction: str
    trade_type: str  # DAILY ou SCALP
    
    playbook: str
    quality: str
    
    entry_price: float
    exit_price: float
    stop_loss: float
    take_profit_1: float
    
    position_size: float
    risk_pct: float
    risk_amount: float
    
    pnl_dollars: float
    pnl_r: float
    outcome: str  # win, loss, breakeven
    exit_reason: str


class BacktestResult(BaseModel):
    """Résultats complets d'un backtest"""
    
    # Metadata
    config: BacktestConfig
    start_date: datetime
    end_date: datetime
    total_bars: int
    total_days: int
    
    # Capital tracking
    initial_capital: float
    final_capital: float
    total_pnl_dollars: float
    total_pnl_pct: float
    total_pnl_r: float
    
    # Equity curves
    equity_curve_r: List[float] = []
    equity_curve_dollars: List[float] = []
    equity_timestamps: List[datetime] = []
    
    # Drawdown
    max_drawdown_r: float
    max_drawdown_pct: float
    max_drawdown_dollars: float
    
    # Trade statistics
    total_trades: int
    wins: int
    losses: int
    breakevens: int
    winrate: float
    
    # R statistics
    avg_r: float
    avg_win_r: float
    avg_loss_r: float
    expectancy_r: float
    
    # Performance metrics
    profit_factor: float
    sharpe_ratio: Optional[float] = None
    
    # Streaks
    max_win_streak: int
    max_loss_streak: int
    current_streak: int
    
    # Trade type breakdown
    stats_by_type: Dict[str, Any] = {}  # DAILY vs SCALP
    
    # Symbol breakdown
    stats_by_symbol: Dict[str, Any] = {}  # SPY vs QQQ
    
    # Playbook breakdown
    stats_by_playbook: Dict[str, Any] = {}
    
    # Quality breakdown
    stats_by_quality: Dict[str, Any] = {}  # A+ vs A
    
    # Trades list
    trades: List[TradeResult] = []
    
    # Best/Worst trades
    best_trade_r: float = 0.0
    worst_trade_r: float = 0.0
    
    # Risk engine stats
    times_risk_reduced: int = 0  # Nombre de fois passé à 1%
    times_frozen: int = 0  # Nombre de fois kill-switch activé
    
    # Output files
    output_dir: str
    trades_file: Optional[str] = None
    equity_file: Optional[str] = None
    report_file: Optional[str] = None


class BacktestSummary(BaseModel):
    """Résumé condensé pour comparaison de plusieurs backtests"""
    run_name: str
    mode: str
    trade_types: List[str]
    
    total_trades: int
    winrate: float
    expectancy_r: float
    profit_factor: float
    max_drawdown_r: float
    
    total_pnl_r: float
    total_pnl_dollars: float
    
    best_playbook: str
    worst_playbook: str
