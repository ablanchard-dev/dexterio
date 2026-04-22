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
    
    # Date filtering (P2-1.B)
    start_date: Optional[str] = None  # Format: YYYY-MM-DD
    end_date: Optional[str] = None    # Format: YYYY-MM-DD
    
    # P2-2.B: HTF warmup for day_type calculation
    htf_warmup_days: int = 30  # Days of HTF history before start_date
    
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
    slippage_pct: float = 0.0002  # 0.02% slippage (legacy, kept for compat)
    
    # PHASE B: Execution costs model (realistic backtest)
    commission_model: str = "ibkr_fixed"  # ibkr_fixed, ibkr_tiered, none
    enable_reg_fees: bool = True
    slippage_model: str = "pct"           # pct, ticks, none
    slippage_cost_pct: float = 0.0005     # 0.05% default (renamed from slippage_pct)
    slippage_ticks: int = 1
    spread_model: str = "fixed_bps"       # fixed_bps, none
    spread_bps: float = 2.0               # 2 bps = 0.02%
    
    # PATCH 3: Time-stop pour SCALP (empêcher overnight)
    max_scalp_minutes: float = 120.0      # Durée max en minutes pour trade_type=SCALP
    
    # Output (default will be resolved at runtime via path_resolver)
    output_dir: str = 'data/backtest_results'  # Relative path, resolved by engine
    save_trades: bool = True
    save_equity_curve: bool = True
    generate_report: bool = True
    
    # P2-2.B: Market state instrumentation
    export_market_state: bool = False
    market_state_export_stride: int = 1  # Export every N setups (1=all)
    
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
    
    # PHASE B: Cost breakdown
    entry_commission: float = 0.0
    entry_reg_fees: float = 0.0
    entry_slippage: float = 0.0
    entry_spread_cost: float = 0.0
    entry_total_cost: float = 0.0
    
    exit_commission: float = 0.0
    exit_reg_fees: float = 0.0
    exit_slippage: float = 0.0
    exit_spread_cost: float = 0.0
    exit_total_cost: float = 0.0
    
    total_costs: float = 0.0
    
    # PnL (gross vs net)
    pnl_gross_dollars: float = 0.0
    pnl_net_dollars: float = 0.0
    pnl_gross_R: float = 0.0
    pnl_net_R: float = 0.0
    
    # Legacy fields (kept for backward compat)
    pnl_dollars: float = 0.0  # Will be set to pnl_net_dollars
    pnl_r: float = 0.0        # Will be set to pnl_net_R
    
    outcome: str  # win, loss, breakeven
    exit_reason: str
    
    # P0: Grading debug info (propagated from Trade)
    match_score: Optional[float] = None  # Score utilisé pour grader
    match_grade: Optional[str] = None  # Grade renvoyé par playbook_loader
    grade_thresholds: Optional[Dict[str, float]] = None  # Seuils A_plus/A/B pour ce playbook
    score_scale_hint: Optional[str] = None  # Hint pour l'échelle du score
    
    # P1: Master Candle info (Sprint 2 - propagated from Trade)
    mc_high: Optional[float] = None
    mc_low: Optional[float] = None
    mc_range: Optional[float] = None
    mc_breakout_dir: Optional[str] = None  # LONG, SHORT, NONE
    mc_window_minutes: Optional[int] = None
    mc_session_date: Optional[str] = None  # YYYY-MM-DD

    # Phase A: MAE / MFE excursion tracking (for SL/TP calibration)
    peak_r: float = 0.0   # Max Favorable Excursion in R (>= 0)
    mae_r: float = 0.0    # Max Adverse Excursion in R (<= 0)

    # Option A v2 — tp_resolver + structure_alignment instrumentation
    tp_reason: Optional[str] = None
    structure_alignment_tf: Optional[str] = None
    structure_alignment_last_pivot_type: Optional[str] = None


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
    
    # PHASE B: PnL gross vs net
    total_pnl_gross_dollars: float = 0.0
    total_pnl_net_dollars: float = 0.0
    total_pnl_gross_R: float = 0.0
    total_pnl_net_R: float = 0.0
    total_costs_dollars: float = 0.0
    
    # Legacy (kept for compat, will be set to net)
    total_pnl_dollars: float
    total_pnl_pct: float
    total_pnl_r: float
    
    # Equity curves
    # equity_curve_r: cumulative pnl in R-account units (pnl_$ / base_r_unit_$).
    # 1R = base_r_unit_dollars (2% of initial capital). Consistent with max_drawdown_r.
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
