"""Modèles de données marché"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

class Candle(BaseModel):
    """Représente une bougie de prix"""
    symbol: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int = 0
    
    @property
    def body(self) -> float:
        """Taille du corps de la bougie"""
        return abs(self.close - self.open)
    
    @property
    def upper_wick(self) -> float:
        """Taille de la mèche haute"""
        return self.high - max(self.open, self.close)
    
    @property
    def lower_wick(self) -> float:
        """Taille de la mèche basse"""
        return min(self.open, self.close) - self.low
    
    @property
    def is_bullish(self) -> bool:
        """Bougie haussière"""
        return self.close > self.open
    
    @property
    def is_bearish(self) -> bool:
        """Bougie baissière"""
        return self.close < self.open
    
    @property
    def total_range(self) -> float:
        """Range total de la bougie"""
        return self.high - self.low

class MarketState(BaseModel):
    """État du marché à un instant T"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    symbol: str
    
    # Biais directionnel
    bias: str  # 'bullish', 'bearish', 'neutral'
    bias_confidence: float = 0.0  # 0-1
    
    # Profil de session (TJR)
    session_profile: int  # 1, 2, ou 3
    session_profile_description: str = ''
    
    # Structure HTF
    daily_structure: str = 'unknown'  # 'uptrend', 'downtrend', 'range'
    h4_structure: str = 'unknown'
    h1_structure: str = 'unknown'
    
    # Day type (P1: trend/manipulation_reversal/range)
    day_type: str = 'unknown'  # New field for playbook filtering
    
    # Niveaux HTF importants
    pdh: Optional[float] = None  # Previous Day High
    pdl: Optional[float] = None  # Previous Day Low
    asia_high: Optional[float] = None
    asia_low: Optional[float] = None
    london_high: Optional[float] = None
    london_low: Optional[float] = None
    
    # FVG HTF
    htf_fvgs: List[Dict[str, Any]] = []
    
    # Contexte
    current_session: str = 'unknown'  # 'asia', 'london', 'ny'
    notes: str = ''

class LiquidityLevel(BaseModel):
    """Niveau de liquidité à surveiller"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    price: float
    level_type: str  # 'high', 'low', 'equal_highs', 'equal_lows', 'pdh', 'pdl'
    timeframe: str
    timestamp_created: datetime = Field(default_factory=datetime.utcnow)
    
    # État
    swept: bool = False
    sweep_timestamp: Optional[datetime] = None
    sweep_details: Optional[Dict[str, Any]] = None
    
    # Importance
    importance: int = 1  # 1-5, 5 = critique
    description: str = ''
