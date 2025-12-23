"""Configuration centralisée pour DexterioBOT"""
import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

class Settings:
    """Configuration globale du bot"""
    
    # MongoDB
    MONGO_URL: str = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    DB_NAME: str = os.environ.get('DB_NAME', 'dexteriobot')
    
    # API Keys
    FINNHUB_API_KEY: str = os.environ.get('FINNHUB_API_KEY', '')
    
    # Trading Configuration
    SYMBOLS: List[str] = ['SPY', 'QQQ']
    TIMEFRAMES: List[str] = ['1m', '5m', '15m', '1h', '4h', '1d']
    
    # Trading Mode
    TRADING_MODE: str = os.environ.get('TRADING_MODE', 'SAFE')  # SAFE or AGGRESSIVE
    
    # Risk Management
    INITIAL_CAPITAL: float = float(os.environ.get('INITIAL_CAPITAL', 50000))
    BASE_RISK_PCT: float = 0.02  # 2%
    REDUCED_RISK_PCT: float = 0.01  # 1%
    MAX_DAILY_LOSS_PCT: float = 0.03  # 3%
    MAX_DRAWDOWN_PCT: float = 0.10  # 10%
    
    # Daily Limits
    MAX_DAILY_TRADES_SAFE: int = 4  # 2 Daily + 2 Scalps
    MAX_DAILY_TRADES_AGGRESSIVE: int = 5
    MAX_CONSECUTIVE_LOSSES: int = 3
    
    # Setup Scoring
    SETUP_WEIGHTS = {
        'ict': 0.4,
        'pattern': 0.3,
        'playbook': 0.3
    }
    
    # Quality Thresholds
    QUALITY_THRESHOLD_A_PLUS: float = 0.85
    QUALITY_THRESHOLD_A: float = 0.70
    QUALITY_THRESHOLD_B: float = 0.55
    
    # Sessions (ET timezone)
    SESSION_ASIA_START: str = '18:00'
    SESSION_ASIA_END: str = '02:00'
    SESSION_LONDON_START: str = '03:00'
    SESSION_LONDON_END: str = '11:00'
    SESSION_NY_START: str = '09:30'
    SESSION_NY_END: str = '16:00'
    
    # Kill Zones (ET timezone)
    KILL_ZONE_NY_MORNING_START: str = '09:30'
    KILL_ZONE_NY_MORNING_END: str = '11:00'
    KILL_ZONE_NY_AFTERNOON_START: str = '14:00'
    KILL_ZONE_NY_AFTERNOON_END: str = '15:30'
    
    # Data Source
    DATA_SOURCE: str = os.environ.get('DATA_SOURCE', 'yfinance')  # yfinance or finnhub
    
    # Paper Trading
    PAPER_TRADING: bool = os.environ.get('PAPER_TRADING', 'true').lower() == 'true'
    
    # Slippage Simulation
    SLIPPAGE_TICKS: float = 0.02  # $0.02 per share average slippage
    
settings = Settings()
