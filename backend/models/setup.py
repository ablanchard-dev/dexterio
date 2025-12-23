"""Modèles de setups et patterns"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

class PatternDetection(BaseModel):
    """Pattern de chandelier détecté"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    symbol: str
    timeframe: str
    
    # Pattern info
    pattern_name: str
    pattern_type: str  # 'bullish_reversal', 'bearish_reversal', 'continuation', 'indecision'
    strength: str  # 'strong', 'medium', 'weak'
    
    # Candles involved
    candles_data: List[Dict[str, Any]] = []
    
    # Context
    trend_before: str = 'unknown'
    at_support_resistance: bool = False
    at_htf_level: bool = False
    after_sweep: bool = False
    in_fvg: bool = False
    
    # Scoring
    pattern_score: float = 0.0

class ICTPattern(BaseModel):
    """Pattern ICT détecté (BOS, FVG, etc.)"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    symbol: str
    timeframe: str
    
    # Type
    pattern_type: str  # 'bos', 'choch', 'fvg', 'smt', 'sweep'
    direction: str  # 'bullish' or 'bearish'
    
    # Location
    price_level: float = 0.0
    
    # Details
    details: Dict[str, Any] = {}
    
    # Scoring
    strength: float = 0.0
    confidence: float = 0.0


class CandlestickPattern(BaseModel):
    """Pattern Chandelle détecté (Engulfing, Pin Bar, etc.)"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    timeframe: str
    
    # Pattern info
    family: str  # 'engulfing', 'pin_bar', 'doji', 'marubozu', etc.
    name: str  # 'Bullish Engulfing', 'Hammer', etc.
    direction: str  # 'bullish', 'bearish', 'neutral'
    
    # Quality metrics
    strength: float = 0.0  # 0.0-1.0
    body_size: float = 0.0  # ratio body/range
    confirmation: bool = False
    
    # Context
    at_level: bool = False
    after_sweep: bool = False

class PlaybookMatch(BaseModel):
    """Match avec un playbook connu"""
    playbook_name: str
    confidence: float = 0.0
    matched_conditions: List[str] = []

class Setup(BaseModel):
    """Setup complet fusionnant tous les signaux"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    symbol: str
    
    # Classification
    quality: str  # 'A+', 'A', 'B', 'C'
    final_score: float
    
    # Component scores
    ict_score: float = 0.0
    pattern_score: float = 0.0
    playbook_score: float = 0.0
    
    # Signals
    ict_patterns: List[ICTPattern] = []
    candlestick_patterns: List[PatternDetection] = []
    playbook_matches: List[PlaybookMatch] = []
    
    # Trading recommendation
    trade_type: str  # 'DAILY' or 'SCALP'
    direction: str  # 'LONG' or 'SHORT'
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: Optional[float] = None
    risk_reward: float
    
    # Context
    market_bias: str
    session: str
    confluences_count: int = 0
    
    notes: str = ''
