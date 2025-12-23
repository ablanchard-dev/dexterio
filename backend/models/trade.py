"""Modèles de trading"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

class Position(BaseModel):
    """Position ouverte"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    direction: str  # 'LONG' or 'SHORT'
    entry_price: float
    quantity: float
    stop_loss: float
    take_profit_1: Optional[float] = None
    take_profit_2: Optional[float] = None
    take_profit_3: Optional[float] = None
    
    timestamp_opened: datetime = Field(default_factory=datetime.utcnow)
    timestamp_closed: Optional[datetime] = None
    
    # État
    status: str = 'open'  # 'open', 'closed', 'breakeven'
    breakeven_moved: bool = False
    
    # P&L
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0

class TradeSetup(BaseModel):
    """Setup de trade détecté"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    symbol: str
    
    # Type
    trade_type: str  # 'DAILY' or 'SCALP'
    direction: str  # 'LONG' or 'SHORT'
    
    # Setup details
    playbook: str
    quality: str  # 'A+', 'A', 'B', 'C'
    score: float
    
    # Confluences
    sweep_detected: bool = False
    bos_detected: bool = False
    fvg_detected: bool = False
    pattern_detected: Optional[str] = None
    smt_detected: bool = False
    htf_alignment: bool = False
    
    # Prices
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: Optional[float] = None
    
    # Risk/Reward
    risk_reward_ratio: float
    risk_amount: float
    
    # Status
    executed: bool = False
    execution_timestamp: Optional[datetime] = None
    
    notes: str = ''

class Trade(BaseModel):
    """Trade complété avec journalisation"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Timing
    date: datetime
    time_entry: datetime
    time_exit: Optional[datetime] = None
    duration_minutes: Optional[float] = 0.0
    
    # Instrument
    symbol: str
    direction: str  # 'LONG' or 'SHORT'
    
    # Contexte Marché
    bias_htf: str
    session_profile: int
    session: str
    market_conditions: str = ''
    
    # Setup
    playbook: str
    setup_quality: str
    setup_score: float
    trade_type: str  # 'DAILY' or 'SCALP'
    
    # Confluences
    confluences: Dict[str, Any] = {}
    
    # Exécution
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: Optional[float] = None
    exit_price: float
    position_size: float
    risk_amount: float
    risk_pct: float
    
    # Résultat
    pnl_dollars: float
    pnl_pct: float
    r_multiple: float
    outcome: str  # 'win' or 'loss'
    exit_reason: str
    
    # Psychologie
    emotions_entry: str = ''
    emotions_during: str = ''
    emotions_exit: str = ''
    mistakes: str = ''
    lessons: str = ''
    
    # Screenshots & Notes
    screenshots: List[str] = []
    notes: str = ''
