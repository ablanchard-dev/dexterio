"""
DexterioBOT Backend Server - Extended avec Engines
"""
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
import os
import logging
from typing import List, Dict, Any
from pydantic import BaseModel

# Import engines
from engines.data_feed import DataFeedEngine
from engines.market_state import MarketStateEngine
from engines.liquidity import LiquidityEngine
from config.settings import settings
from models.market_data import MarketState, LiquidityLevel
from utils.timeframes import get_session_info

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Initialize engines
data_feed = DataFeedEngine(symbols=settings.SYMBOLS)
market_state_engine = MarketStateEngine()
liquidity_engine = LiquidityEngine()

# Create FastAPI app
app = FastAPI(title="DexterioBOT API", version="1.0.0")
api_router = APIRouter(prefix="/api")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== MODELS ====================

class SymbolRequest(BaseModel):
    symbol: str

class MultiSymbolRequest(BaseModel):
    symbols: List[str]

# ==================== ENDPOINTS ====================

@api_router.get("/")
async def root():
    return {
        "message": "DexterioBOT API v1.0",
        "status": "running",
        "engines": {
            "data_feed": "active",
            "market_state": "active",
            "liquidity": "active"
        }
    }

@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "trading_mode": settings.TRADING_MODE,
        "symbols": settings.SYMBOLS,
        "paper_trading": settings.PAPER_TRADING
    }

# ==================== DATA FEED ENDPOINTS ====================

@api_router.post("/data/historical")
async def get_historical_data(request: SymbolRequest):
    """Récupère données historiques pour un symbole"""
    try:
        candles = data_feed.fetch_historical_data(request.symbol, period='5d', interval='1m')
        return {
            "symbol": request.symbol,
            "count": len(candles),
            "candles": [c.model_dump() for c in candles[-100:]]  # Dernières 100
        }
    except Exception as e:
        logger.error(f"Error fetching historical data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/data/multi-timeframe")
async def get_multi_timeframe_data(request: SymbolRequest):
    """Récupère données multi-timeframes"""
    try:
        data = data_feed.get_multi_timeframe_data(request.symbol)
        
        # Convertir en JSON
        result = {}
        for tf, candles in data.items():
            result[tf] = [c.model_dump() for c in candles[-50:]]  # Dernières 50 par TF
        
        return {
            "symbol": request.symbol,
            "timeframes": result,
            "counts": {tf: len(candles) for tf, candles in data.items()}
        }
    except Exception as e:
        logger.error(f"Error fetching multi-timeframe data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/data/latest-price")
async def get_latest_price(request: SymbolRequest):
    """Récupère le dernier prix"""
    try:
        price = data_feed.get_latest_price(request.symbol)
        if price is None:
            raise HTTPException(status_code=404, detail="Price not found")
        
        return {
            "symbol": request.symbol,
            "price": price,
            "timestamp": "now"
        }
    except Exception as e:
        logger.error(f"Error getting latest price: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== MARKET STATE ENDPOINTS ====================

@api_router.post("/market-state/analyze")
async def analyze_market_state(request: SymbolRequest):
    """Analyse l'état du marché et détermine le biais"""
    try:
        # Récupérer données multi-TF
        multi_tf_data = data_feed.get_multi_timeframe_data(request.symbol)
        
        # Info session (simplifié pour MVP)
        from datetime import datetime
        session_info = get_session_info(datetime.utcnow())
        
        # Simuler session levels pour MVP
        session_levels = {}
        if multi_tf_data.get('1h'):
            recent_h1 = multi_tf_data['1h'][-20:]
            session_levels = {
                'asia_high': max(c.high for c in recent_h1[:8]),
                'asia_low': min(c.low for c in recent_h1[:8]),
                'london_high': max(c.high for c in recent_h1[8:16]),
                'london_low': min(c.low for c in recent_h1[8:16])
            }
        
        # Créer market state
        market_state = market_state_engine.create_market_state(
            request.symbol,
            multi_tf_data,
            {'current_session': session_info['name'], 'session_levels': session_levels}
        )
        
        return market_state.model_dump()
    
    except Exception as e:
        logger.error(f"Error analyzing market state: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/market-state/current")
async def get_current_market_state(request: SymbolRequest):
    """Récupère l'état actuel du marché"""
    try:
        market_state = market_state_engine.get_current_state(request.symbol)
        
        if not market_state:
            raise HTTPException(status_code=404, detail="Market state not found. Run /analyze first.")
        
        return market_state.model_dump()
    
    except Exception as e:
        logger.error(f"Error getting market state: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== LIQUIDITY ENDPOINTS ====================

@api_router.post("/liquidity/identify")
async def identify_liquidity_levels(request: SymbolRequest):
    """Identifie les niveaux de liquidité"""
    try:
        # Récupérer données
        multi_tf_data = data_feed.get_multi_timeframe_data(request.symbol)
        
        # Récupérer market state pour HTF levels
        market_state = market_state_engine.get_current_state(request.symbol)
        
        if not market_state:
            # Créer market state si pas existant
            from datetime import datetime
            session_info = get_session_info(datetime.utcnow())
            market_state = market_state_engine.create_market_state(
                request.symbol, multi_tf_data, {'current_session': session_info['name'], 'session_levels': {}}
            )
        
        # HTF levels
        htf_levels = {
            'pdh': market_state.pdh,
            'pdl': market_state.pdl,
            'asia_high': market_state.asia_high,
            'asia_low': market_state.asia_low,
            'london_high': market_state.london_high,
            'london_low': market_state.london_low
        }
        
        # Identifier liquidité
        levels = liquidity_engine.identify_liquidity_levels(request.symbol, multi_tf_data, htf_levels)
        
        return {
            "symbol": request.symbol,
            "count": len(levels),
            "levels": [l.model_dump() for l in levels]
        }
    
    except Exception as e:
        logger.error(f"Error identifying liquidity: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/liquidity/detect-sweep")
async def detect_sweep(request: SymbolRequest):
    """Détecte les sweeps sur les dernières bougies"""
    try:
        # Récupérer données M5
        candles_m5 = data_feed.get_candles_for_analysis(request.symbol, '5m', count=20)
        
        if len(candles_m5) < 2:
            return {"sweeps": [], "message": "Not enough data"}
        
        # Détecter sweeps
        current_candle = candles_m5[-1]
        previous_candles = candles_m5[:-1]
        
        sweeps = liquidity_engine.detect_sweep(request.symbol, current_candle, previous_candles)
        
        return {
            "symbol": request.symbol,
            "sweeps_count": len(sweeps),
            "sweeps": [
                {
                    "level_type": s['level'].level_type,
                    "level_price": s['level'].price,
                    "sweep_type": s['sweep_type'],
                    "wick_beyond": s['wick_beyond'],
                    "rejection_size": s['rejection_size'],
                    "is_strong_rejection": s['is_strong_rejection']
                }
                for s in sweeps
            ]
        }
    
    except Exception as e:
        logger.error(f"Error detecting sweep: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/liquidity/nearest")
async def get_nearest_liquidity(request: SymbolRequest):
    """Trouve les niveaux de liquidité les plus proches"""
    try:
        # Récupérer prix actuel
        current_price = data_feed.get_latest_price(request.symbol)
        
        if not current_price:
            raise HTTPException(status_code=404, detail="Could not get current price")
        
        # Trouver nearest
        nearest = liquidity_engine.get_nearest_liquidity(request.symbol, current_price, direction='both')
        
        result = {
            "symbol": request.symbol,
            "current_price": current_price
        }
        
        if nearest['above']:
            result['above'] = nearest['above'].model_dump()
        if nearest['below']:
            result['below'] = nearest['below'].model_dump()
        
        return result
    
    except Exception as e:
        logger.error(f"Error getting nearest liquidity: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== ANALYSIS WORKFLOW ====================

@api_router.post("/analyze/full")
async def full_analysis(request: MultiSymbolRequest):
    """
    Analyse complète pour plusieurs symboles:
    1. Récupère données multi-TF
    2. Analyse market state
    3. Identifie liquidité
    4. Détecte sweeps
    """
    try:
        results = {}
        
        for symbol in request.symbols:
            logger.info(f"Running full analysis for {symbol}")
            
            # 1. Données multi-TF
            multi_tf_data = data_feed.get_multi_timeframe_data(symbol)
            
            # 2. Market state
            from datetime import datetime
            session_info = get_session_info(datetime.utcnow())
            market_state = market_state_engine.create_market_state(
                symbol, multi_tf_data, {'current_session': session_info['name'], 'session_levels': {}}
            )
            
            # 3. Liquidité
            htf_levels = {
                'pdh': market_state.pdh,
                'pdl': market_state.pdl,
                'asia_high': market_state.asia_high,
                'asia_low': market_state.asia_low
            }
            liquidity_levels = liquidity_engine.identify_liquidity_levels(symbol, multi_tf_data, htf_levels)
            
            # 4. Sweeps
            candles_m5 = multi_tf_data.get('5m', [])
            sweeps = []
            if len(candles_m5) >= 2:
                sweeps = liquidity_engine.detect_sweep(symbol, candles_m5[-1], candles_m5[:-1])
            
            # Compiler résultats
            results[symbol] = {
                "market_state": market_state.model_dump(),
                "liquidity_levels_count": len(liquidity_levels),
                "liquidity_levels": [l.model_dump() for l in liquidity_levels[:10]],  # Top 10
                "sweeps_detected": len(sweeps),
                "recent_sweeps": [
                    {
                        "level_type": s['level'].level_type,
                        "level_price": s['level'].price,
                        "sweep_type": s['sweep_type']
                    }
                    for s in sweeps
                ]
            }
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "symbols": request.symbols,
            "results": results
        }
    
    except Exception as e:
        logger.error(f"Error in full analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== INCLUDE ROUTER ====================

# Import backtest routes (PHASE C)
from routes import backtests
api_router.include_router(backtests.router)

app.include_router(api_router)

# ==================== SHUTDOWN ====================

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
    logger.info("MongoDB connection closed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
