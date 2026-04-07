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
    
    # Live loop: intervalle entre deux passes (analyse + mise à jour positions)
    LIVE_LOOP_INTERVAL_SEC: float = float(os.environ.get('LIVE_LOOP_INTERVAL_SEC', '60'))
    # Réduit les appels Yahoo Finance répétés (yfinance) pendant la boucle paper/live
    DATA_FEED_CACHE_SECONDS: float = float(os.environ.get('DATA_FEED_CACHE_SECONDS', '45'))

    # Exécution: paper (simulation locale) ou ibkr (ordres réels via TWS / Gateway)
    EXECUTION_BACKEND: str = os.environ.get('EXECUTION_BACKEND', 'paper').strip().lower()
    IBKR_HOST: str = os.environ.get('IBKR_HOST', '127.0.0.1')
    IBKR_PORT: int = int(os.environ.get('IBKR_PORT', '7497'))  # paper TWS souvent 7497, live 7496
    IBKR_CLIENT_ID: int = int(os.environ.get('IBKR_CLIENT_ID', '1'))
    # Ne passe à True qu’après tests paper; requiert EXECUTION_BACKEND=ibkr + ib_insync
    LIVE_TRADING_ENABLED: bool = os.environ.get('LIVE_TRADING_ENABLED', 'false').lower() in {
        '1', 'true', 'yes', 'on',
    }

    # Workers ProcessPool pour les jobs backtest
    BACKTEST_MAX_WORKERS: int = max(1, int(os.environ.get('BACKTEST_MAX_WORKERS', '2')))

    # Gate 3 / Wave 1: allowlist paper explicite optionnelle
    PAPER_USE_WAVE1_PLAYBOOKS: bool = os.environ.get(
        "PAPER_USE_WAVE1_PLAYBOOKS", "false"
    ).lower() in {"1", "true", "yes", "on"}
    PAPER_WAVE1_PLAYBOOKS_FILE: str = os.environ.get(
        "PAPER_WAVE1_PLAYBOOKS_FILE", "backend/knowledge/paper_wave1_playbooks.yaml"
    )

    # Slippage Simulation
    SLIPPAGE_TICKS: float = 0.02  # $0.02 per share average slippage

    # Si False (défaut prod), les erreurs 500 ne renvoient pas le détail d'exception au client
    EXPOSE_INTERNAL_ERRORS: bool = os.environ.get(
        "EXPOSE_INTERNAL_ERRORS", "false"
    ).lower() in {"1", "true", "yes", "on"}

settings = Settings()
