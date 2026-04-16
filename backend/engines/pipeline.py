"""Trading Pipeline - Orchestration Phase 1.1 + 1.2 + 1.3"""
import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone
from engines.data_feed import DataFeedEngine
from engines.market_state import MarketStateEngine
from engines.liquidity import LiquidityEngine
from engines.patterns.candlesticks import CandlestickPatternEngine
from engines.patterns.ict import ICTPatternEngine
# Import the unified custom detectors.  These functions encapsulate all ICT pattern
# detection (BOS, FVG, IFVG, Order Blocks, Equilibrium, Breaker Blocks) and expose
# additional wrappers for SMT and CHOCH that always return lists.  Using
# these functions decouples the pipeline from the internal implementation of
# the detectors and simplifies future extensions.
from engines.patterns.custom_detectors import (
    detect_custom_patterns,
    detect_smt_pattern,
    detect_choch_pattern,
)
from engines.playbooks import PlaybookEngine
from engines.setup_engine import SetupEngine, filter_setups_safe_mode, filter_setups_aggressive_mode
from engines.setup_engine_v2 import SetupEngineV2
from engines.risk_engine import RiskEngine
from engines.execution.paper_trading import ExecutionEngine
from engines.journal import TradeJournal, PerformanceStats
from models.setup import Setup, ICTPattern
from models.trade import Trade
from config.settings import settings
from utils.timeframes import get_session_info
from utils.shadow_comparator import (
    build_shadow_comparison_payload,
    candlestick_patterns_from_legacy_detections,
    write_shadow_comparison,
)

logger = logging.getLogger(__name__)

class TradingPipeline:
    """Pipeline complet d'analyse DexterioBOT Phase 1.1 + 1.2 + 1.3"""
    
    def __init__(self, initial_capital: float = None):
        # Phase 1.1 engines
        self.data_feed = DataFeedEngine(symbols=settings.SYMBOLS)
        self.market_state_engine = MarketStateEngine()
        self.liquidity_engine = LiquidityEngine()
        
        # Phase 1.2 engines
        self.candlestick_engine = CandlestickPatternEngine()
        self.ict_engine = ICTPatternEngine()
        self.playbook_engine = PlaybookEngine()
        self.setup_engine = SetupEngine()
        # Shadow-only: SetupEngineV2 is the canonical backtest setup engine.
        # In TradingPipeline it must never replace legacy decisions (shadow comparator only).
        self.setup_engine_v2 = SetupEngineV2()
        
        # Phase 1.3 engines
        self.risk_engine = RiskEngine(initial_capital=initial_capital)
        self.execution_engine = ExecutionEngine(risk_engine=self.risk_engine)
        self.trade_journal = TradeJournal()
        self.performance_stats = PerformanceStats(self.trade_journal)
        
        logger.info("TradingPipeline initialized (Phase 1.1 + 1.2 + 1.3)")
    
    def _apply_canonical_policy_guard(
        self,
        *,
        symbol: str,
        setups: List[Setup],
        warn_on_block: bool,
        log_prefix: str,
    ) -> List[Setup]:
        accepted: List[Setup] = []
        for s in setups:
            rejected = False
            for m in s.playbook_matches:
                allowed, reason = self.risk_engine.is_playbook_allowed(m.playbook_name)
                if not allowed:
                    if warn_on_block:
                        logger.warning(
                            f"{log_prefix} {symbol}: setup blocked by canonical policy "
                            f"(playbook='{m.playbook_name}', reason='{reason}')"
                        )
                    rejected = True
                    break
            if not rejected:
                accepted.append(s)
        return accepted

    def run_full_analysis(
        self,
        symbols: List[str] = None,
        *,
        use_v2_shadow: bool = False,
        v2_shadow_label: Optional[str] = None,
    ) -> Dict[str, List[Setup]]:
        """
        Exécute le pipeline complet pour plusieurs symboles
        
        Pipeline:
        1. Data Feed → Données multi-TF
        2. Market State → Biais, profil session
        3. Liquidity → Niveaux, sweeps
        4. Candlestick Patterns → Détection patterns
        5. ICT Patterns → BOS, FVG, SMT, CHOCH
        6. Playbook Matching → Vérification playbooks
        7. Setup Scoring → Classification A+/A/B/C
        8. Filtering → Mode SAFE/AGRESSIF
        
        Returns:
            Dict {symbol: [Setup, Setup, ...]} - Setups tradables
        """
        symbols = symbols or settings.SYMBOLS
        results = {}
        
        logger.info(f"=== Starting Full Analysis Pipeline for {symbols} ===")
        
        for symbol in symbols:
            try:
                logger.info(f"\n--- Processing {symbol} ---")
                analysis_time = datetime.now(timezone.utc)
                
                # ========== PHASE 1.1 ==========
                
                # 1. Data Feed
                logger.info("[1/8] Data Feed...")
                multi_tf_data = self.data_feed.get_multi_timeframe_data(symbol)
                
                # 2. Market State
                logger.info("[2/8] Market State...")
                session_info = get_session_info(analysis_time)
                market_state = self.market_state_engine.create_market_state(
                    symbol, multi_tf_data,
                    {'current_session': session_info.get('name', 'unknown'), 'session_levels': {}}
                )
                
                # 3. Liquidity
                logger.info("[3/8] Liquidity...")
                htf_levels = {
                    'pdh': market_state.pdh,
                    'pdl': market_state.pdl,
                    'asia_high': market_state.asia_high,
                    'asia_low': market_state.asia_low,
                    'london_high': market_state.london_high,
                    'london_low': market_state.london_low
                }
                liquidity_levels = self.liquidity_engine.identify_liquidity_levels(
                    symbol, multi_tf_data, htf_levels
                )
                
                # Détecter sweeps
                candles_m5 = multi_tf_data.get('5m', [])
                sweeps = []
                if len(candles_m5) >= 2:
                    sweeps = self.liquidity_engine.detect_sweep(
                        symbol, candles_m5[-1], candles_m5[:-1]
                    )
                swept_levels = [s['level'] for s in sweeps]
                
                # ========== PHASE 1.2 ==========
                
                # 4. Candlestick Patterns
                logger.info("[4/8] Candlestick Patterns...")
                candlestick_patterns = []
                
                # SR levels pour contexte
                sr_levels = [lvl.price for lvl in liquidity_levels if lvl.importance >= 4]
                
                for tf in ['5m', '15m']:
                    candles = multi_tf_data.get(tf, [])
                    if candles:
                        patterns = self.candlestick_engine.detect_patterns(
                            candles, timeframe=tf, sr_levels=sr_levels
                        )
                        candlestick_patterns.extend(patterns)
                
                logger.info(f"  Detected {len(candlestick_patterns)} candlestick patterns")
                
                # 5. ICT Patterns
                #
                # Use unified custom detectors for all ICT patterns.  This wrapper
                # runs the legacy BOS/FVG detections as well as the custom
                # extensions (IFVG, order blocks, equilibrium and breaker blocks).
                logger.info("[5/8] ICT Patterns via custom detectors...")
                ict_patterns: List[ICTPattern] = []

                # Detect patterns on 5m and 15m timeframes
                for tf in ['5m', '15m']:
                    candles_tf = multi_tf_data.get(tf, [])
                    if candles_tf:
                        detections = detect_custom_patterns(candles_tf, tf)
                        for plist in detections.values():
                            if plist:
                                ict_patterns.extend(plist)

                # SMT (SPY vs QQQ) using the custom wrapper
                if symbol == 'SPY' and 'QQQ' in symbols:
                    qqq_data = self.data_feed.get_multi_timeframe_data('QQQ')
                    spy_h1 = multi_tf_data.get('1h', [])
                    qqq_h1 = qqq_data.get('1h', [])
                    if spy_h1 and qqq_h1:
                        smt_patterns = detect_smt_pattern(spy_h1, qqq_h1)
                        ict_patterns.extend(smt_patterns)

                # CHOCH detection if there was a recent sweep
                if sweeps:
                    # Use the most recent 50 candles on 5m (or all if fewer) for CHOCH detection
                    recent_5m = candles_m5[-50:] if len(candles_m5) > 50 else candles_m5
                    choch_patterns = detect_choch_pattern(recent_5m, sweeps[-1])
                    if choch_patterns:
                        ict_patterns.extend(choch_patterns)

                logger.info(f"  Detected {len(ict_patterns)} ICT patterns")
                
                # 6. Playbook Matching
                logger.info("[6/8] Playbook Matching...")
                playbook_matches = self.playbook_engine.check_all_playbooks(
                    market_state,
                    self.liquidity_engine,
                    ict_patterns,
                    analysis_time
                )
                
                logger.info(f"  Matched {len(playbook_matches)} playbooks")
                
                # 7. Setup Scoring
                logger.info("[7/8] Setup Scoring...")
                
                # Prix actuel
                current_price = self.data_feed.get_latest_price(symbol)
                if not current_price:
                    logger.warning(f"Could not get current price for {symbol}, skipping")
                    results[symbol] = []
                    continue

                legacy_setup = self.setup_engine.score_setup(
                    symbol,
                    market_state,
                    ict_patterns,
                    candlestick_patterns,
                    playbook_matches,
                    swept_levels,
                    current_price,
                )

                # 8. Filtering selon mode (legacy output)
                logger.info("[8/8] Filtering...")
                legacy_final: List[Setup] = []
                if legacy_setup is not None:
                    if settings.TRADING_MODE == "SAFE":
                        legacy_final = filter_setups_safe_mode([legacy_setup])
                    else:
                        legacy_final = filter_setups_aggressive_mode([legacy_setup])

                    legacy_final = self._apply_canonical_policy_guard(
                        symbol=symbol,
                        setups=legacy_final,
                        warn_on_block=True,
                        log_prefix="[P0]",
                    )

                # Shadow comparator (SetupEngineV2), strictly non-blocking.
                if use_v2_shadow:
                    v2_raw: List[Setup] = []
                    v2_final: List[Setup] = []
                    v2_error: Optional[str] = None
                    v2_candle_patterns = []
                    try:
                        v2_candle_patterns = candlestick_patterns_from_legacy_detections(candlestick_patterns)
                        v2_raw = self.setup_engine_v2.generate_setups(
                            symbol=symbol,
                            market_state=market_state,
                            ict_patterns=ict_patterns,
                            candle_patterns=v2_candle_patterns,
                            liquidity_levels=liquidity_levels,
                            current_time=analysis_time,
                            trading_mode=settings.TRADING_MODE,
                            last_price=current_price,
                        )
                        if settings.TRADING_MODE == "SAFE":
                            v2_final = filter_setups_safe_mode(list(v2_raw))
                        else:
                            v2_final = filter_setups_aggressive_mode(list(v2_raw))
                        v2_final = self._apply_canonical_policy_guard(
                            symbol=symbol,
                            setups=v2_final,
                            warn_on_block=False,
                            log_prefix="[SHADOW_V2]",
                        )
                    except Exception as e:
                        v2_error = f"{type(e).__name__}: {e}"
                        v2_raw = []
                        v2_final = []

                    try:
                        payload = build_shadow_comparison_payload(
                            symbol=symbol,
                            analysis_time=analysis_time,
                            trading_mode=settings.TRADING_MODE,
                            market_state=market_state,
                            current_price=current_price,
                            legacy_raw=legacy_setup,
                            legacy_final=list(legacy_final),
                            v2_raw=list(v2_raw),
                            v2_final=list(v2_final),
                            v2_error=v2_error,
                            counts={
                                "candlestick_patterns_legacy": len(candlestick_patterns),
                                "candlestick_patterns_v2": len(v2_candle_patterns),
                                "ict_patterns": len(ict_patterns),
                                "liquidity_levels": len(liquidity_levels),
                                "legacy_playbook_matches": len(playbook_matches) if playbook_matches else 0,
                                "v2_raw_setups": len(v2_raw),
                                "v2_final_setups": len(v2_final),
                                "legacy_final_setups": len(legacy_final),
                            },
                            is_playbook_allowed=self.risk_engine.is_playbook_allowed,
                        )
                        wr = write_shadow_comparison(
                            payload,
                            symbol=symbol,
                            analysis_time=analysis_time,
                            label=v2_shadow_label,
                        )
                        logger.info(f"[SHADOW_V2] wrote comparison artefact: {wr.path}")
                    except Exception as e:
                        logger.warning(f"[SHADOW_V2] failed to write comparison artefact: {e}")

                results[symbol] = legacy_final

                logger.info(f"✓ {symbol} complete: {len(legacy_final)} tradable setups")
                
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}", exc_info=True)
                results[symbol] = []
        
        # Summary
        total_setups = sum(len(setups) for setups in results.values())
        logger.info(f"\n=== Pipeline Complete: {total_setups} total tradable setups ===")
        
        return results
    
    def get_summary(self, results: Dict[str, List[Setup]]) -> Dict:
        """Génère un résumé des setups détectés"""
        
        summary = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'trading_mode': settings.TRADING_MODE,
            'total_setups': 0,
            'by_symbol': {},
            'by_quality': {'A+': 0, 'A': 0, 'B': 0},
            'by_direction': {'LONG': 0, 'SHORT': 0},
            'by_type': {'DAILY': 0, 'SCALP': 0}
        }
        
        for symbol, setups in results.items():
            summary['total_setups'] += len(setups)
            summary['by_symbol'][symbol] = len(setups)
            
            for setup in setups:
                summary['by_quality'][setup.quality] += 1
                summary['by_direction'][setup.direction] += 1
                summary['by_type'][setup.trade_type] += 1
        
        return summary
    
    def execute_trading_loop(self, symbols: List[str] = None) -> Dict:
        """
        Boucle complète de trading : Analyse → Risk → Execution → Journal
        
        Phase 1.3 - Intégration complète RiskEngine + ExecutionEngine + TradeJournal
        
        Returns:
            Dict avec résultats d'exécution, trades ouverts, stats
        """
        symbols = symbols or settings.SYMBOLS
        now = datetime.now(timezone.utc)

        logger.info("=== Starting Full Trading Loop (Phase 1.1 + 1.2 + 1.3) ===")
        
        # 1. Vérifier limites quotidiennes
        limits_check = self.risk_engine.check_daily_limits()
        if not limits_check['trading_allowed']:
            logger.warning(f"❌ Trading NOT allowed: {limits_check['reason']}")
            return {
                'trading_allowed': False,
                'reason': limits_check['reason'],
                'risk_state': self.risk_engine.state.model_dump()
            }
        
        logger.info(f"✓ Trading allowed (Risk: {self.risk_engine.state.current_risk_pct*100:.1f}%)")
        
        # 2. Exécuter analyse complète (Phase 1.1 + 1.2)
        analysis_results = self.run_full_analysis(symbols)
        
        # 3. Rassembler tous les setups filtrés
        all_setups = []
        for symbol, setups in analysis_results.items():
            all_setups.extend(setups)
        
        if not all_setups:
            logger.info("No tradable setups detected")
            return {
                'trading_allowed': True,
                'setups_detected': 0,
                'trades_executed': 0,
                'risk_state': self.risk_engine.state.model_dump()
            }
        
        logger.info(f"📊 {len(all_setups)} tradable setups detected")
        
        # 4. Sélection multi-actifs (SPY/QQQ)
        # Récupérer patterns ICT pour SMT
        ict_patterns = []
        for setup in all_setups:
            ict_patterns.extend(setup.ict_patterns)
        
        trade_allocations = self.risk_engine.evaluate_multi_asset_trade(all_setups, ict_patterns)
        
        if not trade_allocations:
            logger.info("No optimal trade allocation found")
            return {
                'trading_allowed': True,
                'setups_detected': len(all_setups),
                'trades_executed': 0,
                'risk_state': self.risk_engine.state.model_dump()
            }
        
        logger.info(f"🎯 {len(trade_allocations)} trade(s) selected for execution")
        
        # 5. Exécution des trades
        executed_trades = []
        
        for allocation in trade_allocations:
            setup = allocation['setup']
            risk_pct = allocation['risk_pct']
            
            # Position sizing
            position_calc = self.risk_engine.calculate_position_size(setup, risk_pct)
            
            if not position_calc.valid:
                logger.warning(f"⚠ Position sizing failed for {setup.symbol}: {position_calc.reason}")
                continue
            
            # Place order (Paper Trading)
            risk_allocation = {
                'risk_pct': risk_pct,
                'position_calc': position_calc
            }
            
            order_result = self.execution_engine.place_order(setup, risk_allocation, current_time=now)
            
            if order_result['success']:
                trade = order_result['trade']
                executed_trades.append(trade)
                logger.info(f"✅ Trade opened: {trade.symbol} {trade.direction} @ {trade.entry_price:.2f}")
            else:
                logger.warning(f"❌ Order failed: {order_result['reason']}")
        
        logger.info(f"=== Trading Loop Complete: {len(executed_trades)} trade(s) executed ===")
        
        return {
            'trading_allowed': True,
            'setups_detected': len(all_setups),
            'trades_executed': len(executed_trades),
            'executed_trades': [t.model_dump() for t in executed_trades],
            'risk_state': self.risk_engine.state.model_dump()
        }
    
    def update_open_positions(self) -> Dict:
        """
        Met à jour toutes les positions ouvertes avec prix actuels
        Ferme automatiquement si SL/TP atteint
        
        Returns:
            Dict avec events (SL hit, TP hit, etc.) et trades fermés
        """
        # Récupérer prix actuels
        market_data = {}
        for symbol in settings.SYMBOLS:
            price = self.data_feed.get_latest_price(symbol)
            if price:
                market_data[symbol] = price
        
        # Mettre à jour positions
        now = datetime.now(timezone.utc)
        events = self.execution_engine.update_open_trades(market_data, current_time=now)
        
        # Récupérer trades fermés récents (ceux qui viennent d'être fermés)
        closed_trades = [t for t in self.execution_engine.get_closed_trades() 
                        if not self._trade_in_journal(t)]
        
        # Enregistrer dans journal
        for trade in closed_trades:
            context = {
                'account_balance': self.risk_engine.state.account_balance,
                'trading_mode': self.risk_engine.state.trading_mode
            }
            self.trade_journal.add_entry(trade, context)
            logger.info(f"📝 Trade logged to journal: {trade.id}")
        
        return {
            'events': events,
            'trades_closed': len(closed_trades),
            'open_positions': len(self.execution_engine.get_open_trades())
        }
    
    def _trade_in_journal(self, trade: Trade) -> bool:
        """Vérifie si un trade est déjà dans le journal"""
        journal_ids = [e.trade_id for e in self.trade_journal.entries]
        return trade.id in journal_ids
    
    def close_all_positions_eod(self) -> Dict:
        """
        Ferme toutes les positions en fin de journée (EOD)
        
        Returns:
            Dict avec nombre de positions fermées
        """
        open_trades = self.execution_engine.get_open_trades()
        closed_count = 0
        
        now = datetime.now(timezone.utc)
        for trade in open_trades:
            # Récupérer prix actuel
            current_price = self.data_feed.get_latest_price(trade.symbol)
            if current_price:
                self.execution_engine.close_trade(
                    trade.id, 'eod', current_price, current_time=now
                )
                closed_count += 1
        
        logger.info(f"EOD: Closed {closed_count} position(s)")
        
        # Logger tous les trades fermés
        self.update_open_positions()
        
        return {
            'closed_positions': closed_count
        }
    
    def get_performance_report(self) -> Dict:
        """
        Génère un rapport de performance complet
        
        Returns:
            Dict avec tous les KPIs (winrate, expectancy, profit factor, etc.)
        """
        kpis = self.performance_stats.calculate_kpis()
        
        return {
            'overall': kpis,
            'risk_state': self.risk_engine.state.model_dump(),
            'open_positions': len(self.execution_engine.get_open_trades()),
            'total_trades_in_journal': len(self.trade_journal.entries)
        }
