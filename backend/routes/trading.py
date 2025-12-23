"""Trading API Routes - Phase 1.4"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from engines.pipeline import TradingPipeline
from engines.journal import TradeJournal, PerformanceStats
from models.setup import Setup
from models.trade import Trade
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trading", tags=["trading"])

# Global pipeline instance (singleton pattern)
_pipeline_instance = None


def get_pipeline() -> TradingPipeline:
    """Get or create pipeline singleton"""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = TradingPipeline()
    return _pipeline_instance


# ============== Request/Response Models ==============

class MarketStateResponse(BaseModel):
    """Market state data"""
    timestamp: datetime
    symbols: List[str]
    spy_price: float
    qqq_price: float
    htf_bias: Dict[str, str]  # {symbol: bias}
    session: str
    session_profile: Dict[str, Any]
    structure: Dict[str, Any]
    kill_zone_active: bool


class LiquidityLevel(BaseModel):
    """Liquidity level info"""
    symbol: str
    level_type: str
    price: float
    importance: int
    swept: bool


class SetupResponse(BaseModel):
    """Setup detected"""
    id: str
    timestamp: datetime
    symbol: str
    direction: str
    quality: str
    final_score: float
    trade_type: str
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: Optional[float]
    risk_reward: float
    confluences_count: int
    playbook_matches: List[str]
    market_bias: str
    session: str
    notes: str


class TradeResponse(BaseModel):
    """Trade info"""
    id: str
    symbol: str
    direction: str
    trade_type: str
    entry_price: float
    stop_loss: float
    take_profit_1: float
    position_size: float
    risk_pct: float
    outcome: str
    pnl_dollars: float
    r_multiple: float
    time_entry: datetime
    time_exit: Optional[datetime]
    duration_minutes: Optional[float]
    setup_quality: str
    playbook: str


class RiskStateResponse(BaseModel):
    """Risk engine state"""
    account_balance: float
    peak_balance: float
    current_risk_pct: float
    trading_mode: str
    trading_allowed: bool
    day_frozen: bool
    freeze_reason: str
    daily_trade_count: int
    daily_pnl_dollars: float
    daily_pnl_r: float
    open_positions_count: int


class PerformanceResponse(BaseModel):
    """Performance KPIs"""
    total_trades: int
    wins: int
    losses: int
    winrate: float
    avg_r: float
    avg_win_r: float
    avg_loss_r: float
    expectancy: float
    profit_factor: float
    max_drawdown_r: float
    total_pnl_r: float
    total_pnl_dollars: float
    by_playbook: Dict[str, Any]
    by_quality: Dict[str, Any]


class TradingControlRequest(BaseModel):
    """Control bot"""
    action: str  # 'start', 'stop', 'close_all'


class ManualTradeRequest(BaseModel):
    """Manual trade execution"""
    setup_id: str
    override: bool = False


# ============== API ENDPOINTS ==============

@router.get("/market-state", response_model=MarketStateResponse)
async def get_market_state():
    """Get current market state"""
    try:
        pipeline = get_pipeline()
        
        # Get latest data
        spy_price = pipeline.data_feed.get_latest_price('SPY') or 0.0
        qqq_price = pipeline.data_feed.get_latest_price('QQQ') or 0.0
        
        # Get market states
        spy_data = pipeline.data_feed.get_multi_timeframe_data('SPY')
        qqq_data = pipeline.data_feed.get_multi_timeframe_data('QQQ')
        
        spy_state = pipeline.market_state_engine.create_market_state(
            'SPY', spy_data, {'current_session': 'NY', 'session_levels': {}}
        )
        qqq_state = pipeline.market_state_engine.create_market_state(
            'QQQ', qqq_data, {'current_session': 'NY', 'session_levels': {}}
        )
        
        return MarketStateResponse(
            timestamp=datetime.now(),
            symbols=['SPY', 'QQQ'],
            spy_price=spy_price,
            qqq_price=qqq_price,
            htf_bias={
                'SPY': spy_state.bias,
                'QQQ': qqq_state.bias
            },
            session=spy_state.current_session,
            session_profile={
                'SPY': spy_state.session_profile,
                'QQQ': qqq_state.session_profile
            },
            structure={
                'SPY': {
                    'daily': spy_state.daily_structure,
                    'h4': spy_state.h4_structure,
                    'h1': spy_state.h1_structure
                },
                'QQQ': {
                    'daily': qqq_state.daily_structure,
                    'h4': qqq_state.h4_structure,
                    'h1': qqq_state.h1_structure
                }
            },
            kill_zone_active=False  # TODO: implement kill zone detection
        )
    
    except Exception as e:
        logger.error(f"Error getting market state: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/liquidity-levels", response_model=List[LiquidityLevel])
async def get_liquidity_levels():
    """Get liquidity levels"""
    try:
        pipeline = get_pipeline()
        
        levels = []
        for symbol in ['SPY', 'QQQ']:
            multi_tf_data = pipeline.data_feed.get_multi_timeframe_data(symbol)
            market_state = pipeline.market_state_engine.create_market_state(
                symbol, multi_tf_data, {'current_session': 'NY', 'session_levels': {}}
            )
            
            htf_levels = {
                'pdh': market_state.pdh,
                'pdl': market_state.pdl,
                'asia_high': market_state.asia_high,
                'asia_low': market_state.asia_low,
                'london_high': market_state.london_high,
                'london_low': market_state.london_low
            }
            
            liquidity_levels = pipeline.liquidity_engine.identify_liquidity_levels(
                symbol, multi_tf_data, htf_levels
            )
            
            for lvl in liquidity_levels:
                levels.append(LiquidityLevel(
                    symbol=symbol,
                    level_type=lvl.level_type,
                    price=lvl.price,
                    importance=lvl.importance,
                    swept=lvl.swept
                ))
        
        return levels
    
    except Exception as e:
        logger.error(f"Error getting liquidity levels: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/setups", response_model=List[SetupResponse])
async def get_setups():
    """Get detected setups"""
    try:
        pipeline = get_pipeline()
        
        # Run analysis
        results = pipeline.run_full_analysis()
        
        setups = []
        for symbol, setup_list in results.items():
            for setup in setup_list:
                playbooks = [pb.playbook_name for pb in setup.playbook_matches]
                
                setups.append(SetupResponse(
                    id=setup.id,
                    timestamp=setup.timestamp,
                    symbol=setup.symbol,
                    direction=setup.direction,
                    quality=setup.quality,
                    final_score=setup.final_score,
                    trade_type=setup.trade_type,
                    entry_price=setup.entry_price,
                    stop_loss=setup.stop_loss,
                    take_profit_1=setup.take_profit_1,
                    take_profit_2=setup.take_profit_2,
                    risk_reward=setup.risk_reward,
                    confluences_count=setup.confluences_count,
                    playbook_matches=playbooks,
                    market_bias=setup.market_bias,
                    session=setup.session,
                    notes=setup.notes
                ))
        
        return setups
    
    except Exception as e:
        logger.error(f"Error getting setups: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trades/open", response_model=List[TradeResponse])
async def get_open_trades():
    """Get open trades"""
    try:
        pipeline = get_pipeline()
        open_trades = pipeline.execution_engine.get_open_trades()
        
        return [
            TradeResponse(
                id=t.id,
                symbol=t.symbol,
                direction=t.direction,
                trade_type=t.trade_type,
                entry_price=t.entry_price,
                stop_loss=t.stop_loss,
                take_profit_1=t.take_profit_1,
                position_size=t.position_size,
                risk_pct=t.risk_pct,
                outcome=t.outcome,
                pnl_dollars=t.pnl_dollars,
                r_multiple=t.r_multiple,
                time_entry=t.time_entry,
                time_exit=t.time_exit,
                duration_minutes=t.duration_minutes,
                setup_quality=t.setup_quality,
                playbook=t.playbook
            )
            for t in open_trades
        ]
    
    except Exception as e:
        logger.error(f"Error getting open trades: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trades/history", response_model=List[TradeResponse])
async def get_trade_history(
    limit: int = 100,
    playbook: Optional[str] = None,
    quality: Optional[str] = None,
    outcome: Optional[str] = None
):
    """Get trade history with filters"""
    try:
        journal = TradeJournal()
        
        # Apply filters
        filters = {}
        if playbook:
            filters['playbook'] = playbook
        if quality:
            filters['setup_quality'] = quality
        if outcome:
            filters['outcome'] = outcome
        
        entries = journal.filter(**filters) if filters else journal.get_all()
        
        # Limit results
        entries = entries[-limit:]
        
        trades = []
        for entry in entries:
            trades.append(TradeResponse(
                id=entry.trade_id,
                symbol=entry.symbol,
                direction=entry.direction,
                trade_type=entry.trade_type,
                entry_price=entry.entry_price,
                stop_loss=entry.stop_loss_final,
                take_profit_1=entry.take_profit_1,
                position_size=entry.position_size,
                risk_pct=entry.risk_pct,
                outcome=entry.outcome,
                pnl_dollars=entry.pnl_dollars,
                r_multiple=entry.r_multiple,
                time_entry=entry.timestamp_opened,
                time_exit=entry.timestamp_closed,
                duration_minutes=entry.duration_minutes,
                setup_quality=entry.setup_quality,
                playbook=entry.playbook
            ))
        
        return trades
    
    except Exception as e:
        logger.error(f"Error getting trade history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance", response_model=PerformanceResponse)
async def get_performance():
    """Get performance stats"""
    try:
        journal = TradeJournal()
        perf_stats = PerformanceStats(journal)
        kpis = perf_stats.calculate_kpis()
        
        return PerformanceResponse(
            total_trades=kpis['total_trades'],
            wins=kpis['wins'],
            losses=kpis['losses'],
            winrate=kpis['winrate'],
            avg_r=kpis['avg_pnl_r'],
            avg_win_r=kpis['avg_win_r'],
            avg_loss_r=kpis['avg_loss_r'],
            expectancy=kpis['expectancy'],
            profit_factor=kpis['profit_factor'],
            max_drawdown_r=kpis['max_drawdown_r'],
            total_pnl_r=kpis['total_pnl_r'],
            total_pnl_dollars=kpis['total_pnl_dollars'],
            by_playbook=kpis['by_playbook'],
            by_quality=kpis['by_quality']
        )
    
    except Exception as e:
        logger.error(f"Error getting performance: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk-state", response_model=RiskStateResponse)
async def get_risk_state():
    """Get risk engine state"""
    try:
        pipeline = get_pipeline()
        state = pipeline.risk_engine.state
        
        return RiskStateResponse(
            account_balance=state.account_balance,
            peak_balance=state.peak_balance,
            current_risk_pct=state.current_risk_pct,
            trading_mode=state.trading_mode,
            trading_allowed=state.trading_allowed,
            day_frozen=state.day_frozen,
            freeze_reason=state.freeze_reason,
            daily_trade_count=state.daily_trade_count,
            daily_pnl_dollars=state.daily_pnl_dollars,
            daily_pnl_r=state.daily_pnl_r,
            open_positions_count=state.open_positions_count
        )
    
    except Exception as e:
        logger.error(f"Error getting risk state: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/control")
async def control_trading(request: TradingControlRequest):
    """Control trading bot"""
    try:
        pipeline = get_pipeline()
        
        if request.action == 'start':
            # TODO: Implement auto trading loop
            return {"status": "started", "message": "Auto trading started (not yet implemented)"}
        
        elif request.action == 'stop':
            # TODO: Implement stop
            return {"status": "stopped", "message": "Auto trading stopped"}
        
        elif request.action == 'close_all':
            result = pipeline.close_all_positions_eod()
            return {"status": "closed", "closed_positions": result['closed_positions']}
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")
    
    except Exception as e:
        logger.error(f"Error controlling trading: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute-manual")
async def execute_manual_trade(request: ManualTradeRequest):
    """Execute a trade manually (override)"""
    try:
        pipeline = get_pipeline()
        
        # Get all current setups
        results = pipeline.run_full_analysis()
        
        # Find the setup
        target_setup = None
        for symbol, setup_list in results.items():
            for setup in setup_list:
                if setup.id == request.setup_id:
                    target_setup = setup
                    break
            if target_setup:
                break
        
        if not target_setup:
            raise HTTPException(status_code=404, detail=f"Setup {request.setup_id} not found")
        
        # Check risk limits (even in override mode)
        limits_check = pipeline.risk_engine.check_daily_limits()
        if not limits_check['trading_allowed'] and not request.override:
            raise HTTPException(status_code=403, detail=f"Trading not allowed: {limits_check['reason']}")
        
        # Calculate position size
        position_calc = pipeline.risk_engine.calculate_position_size(
            target_setup,
            pipeline.risk_engine.state.current_risk_pct
        )
        
        if not position_calc.valid:
            raise HTTPException(status_code=400, detail=f"Position sizing failed: {position_calc.reason}")
        
        # Execute trade
        risk_allocation = {
            'risk_pct': pipeline.risk_engine.state.current_risk_pct,
            'position_calc': position_calc
        }
        
        order_result = pipeline.execution_engine.place_order(target_setup, risk_allocation)
        
        if not order_result['success']:
            raise HTTPException(status_code=400, detail=f"Order failed: {order_result['reason']}")
        
        trade = order_result['trade']
        
        return {
            "status": "executed",
            "trade_id": trade.id,
            "symbol": trade.symbol,
            "direction": trade.direction,
            "entry_price": trade.entry_price,
            "position_size": trade.position_size
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing manual trade: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
