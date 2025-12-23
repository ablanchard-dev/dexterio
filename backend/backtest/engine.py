"""
Backtest Engine - Phase 2.3 OPTIMIZED
Rejoue bougie par bougie avec agrégation incrémentale et caching
"""
import logging
import pandas as pd
import numpy as np
import pytz
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from models.backtest import BacktestConfig, BacktestResult, TradeResult
from models.market_data import MarketState, Candle
from models.setup import Setup, ICTPattern, CandlestickPattern, PatternDetection
from engines.market_state import MarketStateEngine
from engines.liquidity import LiquidityEngine
from engines.patterns.candlesticks import CandlestickPatternEngine
from engines.patterns.ict import ICTPatternEngine
from engines.setup_engine_v2 import SetupEngineV2, filter_setups_by_mode
from engines.risk_engine import RiskEngine
from engines.execution.paper_trading import ExecutionEngine
from engines.timeframe_aggregator import TimeframeAggregator
from engines.market_state_cache import MarketStateCache
from utils.timeframes import get_session_info

logger = logging.getLogger(__name__)


class BacktestEngine:
    """
    Moteur de backtest avec market replay optimisé
    
    Architecture OPTIMISÉE :
    1. Load historical data (M1 SPY/QQQ)
    2. Loop chronologique minute par minute (driver = 1m)
    3. Agrégation incrémentale vers HTF (5m/10m/15m/1h) - recalcul seulement à la clôture
    4. Caching du MarketState - recalcul seulement sur événements HTF
    5. Pipeline complet : Market → Pattern → Playbook → Setup → Risk → Execution
    6. Collecte résultats et génère rapports
    
    Règle HTF/LTF (docs) :
    - Driver = 1m (timeframe d'exécution principal)
    - HTF = 5m/10m/15m/1h/4h/1d (contexte, confluence, validation)
    - Recalcul HTF seulement quand la bougie HTF clôture
    """
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        
        # Engines
        self.market_state_engine = MarketStateEngine()
        self.liquidity_engine = LiquidityEngine()
        self.candlestick_engine = CandlestickPatternEngine()
        self.ict_engine = ICTPatternEngine()
        self.setup_engine = SetupEngineV2()
        self.risk_engine = RiskEngine(initial_capital=config.initial_capital)
        # Forcer le mode de trading du RiskEngine selon la config (SAFE/AGGRESSIVE)
        self.risk_engine.state.trading_mode = config.trading_mode
        self.execution_engine = ExecutionEngine(self.risk_engine)
        
        # OPTIMISATION: Timeframe aggregator et caches
        self.tf_aggregator = TimeframeAggregator()
        self.market_state_cache = MarketStateCache()
        
        # Data (M1 Parquet -> Candles multi-TF)
        self.data: Dict[str, pd.DataFrame] = {}
        self.combined_data: Optional[pd.DataFrame] = None
        # DEPRECATED: self.multi_tf_candles (remplacé par tf_aggregator)
        self.multi_tf_candles: Dict[str, Dict[str, List[Candle]]] = {}
        
        # Results tracking
        # Identifiant de run (pour journal / filtrage)
        self.run_id = self.config.run_name or f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self.trades: List[TradeResult] = []
        self.equity_curve_r: List[float] = []
        self.equity_curve_dollars: List[float] = []
        self.equity_timestamps: List[datetime] = []
        # Journal de trades global (Parquet) + suivi des trades déjà journalisés
        from engines.journal import TradeJournal

        self.trade_journal = TradeJournal()
        self._journaled_trade_ids: set[str] = {e.trade_id for e in self.trade_journal.entries}

        # Stats de setups pour instrumentation
        # structure: {date_str: {symbol: {...}}}
        self.setup_stats: Dict[str, Dict[str, Dict[str, Any]]] = {}
        
        # P0.6.1: Circuit breaker tracking
        self._stop_run_triggered: bool = False
        self._stop_run_time: Optional[datetime] = None
        self._stop_run_reason: str = ''
        self._guardrail_events: List[Dict[str, Any]] = []
        
        # PATCH D: Anti-spam tracking
        self.blocked_by_cooldown: int = 0
        self.blocked_by_session_limit: int = 0
        self.blocked_by_cooldown_details: Dict[str, int] = {}  # playbook -> count
        self.blocked_by_session_limit_details: Dict[str, int] = {}  # playbook -> count



        
        logger.info(f"BacktestEngine initialized - Mode: {config.trading_mode}, Types: {config.trade_types}")
    
    def load_data(self):
        """Charge et combine les données historiques"""
        logger.info(f"Loading {len(self.config.data_paths)} data files...")
        
        all_dfs = []
        
        for path_str in self.config.data_paths:
            path = Path(path_str)
            if not path.exists():
                logger.warning(f"File not found: {path}")
                continue
            
            try:
                df = pd.read_parquet(path)

                # Support Parquet contract v1: DatetimeIndex stored as index.
                if 'datetime' not in df.columns:
                    if isinstance(df.index, pd.DatetimeIndex):
                        df['datetime'] = df.index
                    elif '__index_level_0__' in df.columns:
                        df['datetime'] = pd.to_datetime(df['__index_level_0__'], utc=True, errors='coerce')

                df['datetime'] = pd.to_datetime(df['datetime'], utc=True, errors='coerce')
                
                # Extraire le symbole du nom du fichier
                filename = path.name.lower()
                if 'spy' in filename:
                    df['symbol'] = 'SPY'
                elif 'qqq' in filename:
                    df['symbol'] = 'QQQ'
                else:
                    logger.warning(f"Could not determine symbol from {filename}")
                    continue
                
                all_dfs.append(df)
                logger.info(f"  Loaded {path.name}: {len(df)} bars")
            
            except Exception as e:
                logger.error(f"Error loading {path}: {e}")
                continue
        
        if not all_dfs:
            raise ValueError("No data loaded!")
        
        # Combiner et trier
        self.combined_data = pd.concat(all_dfs, ignore_index=True)
        self.combined_data = self.combined_data.sort_values('datetime').reset_index(drop=True)
        
        # Séparer par symbole ET créer index par timestamp pour accès O(1)
        self.candles_1m_by_timestamp: Dict[str, Dict[datetime, Candle]] = {}
        
        for symbol in self.config.symbols:
            symbol_data = self.combined_data[self.combined_data['symbol'] == symbol].copy()
            if not symbol_data.empty:
                self.data[symbol] = symbol_data
                
                # Créer index timestamp -> Candle pour accès rapide
                candles_dict = {}
                for _, row in symbol_data.iterrows():
                    ts = row['datetime']
                    candles_dict[ts] = Candle(
                        symbol=symbol,
                        timeframe="1m",
                        timestamp=ts,
                        open=row['open'],
                        high=row['high'],
                        low=row['low'],
                        close=row['close'],
                        volume=row['volume']
                    )
                self.candles_1m_by_timestamp[symbol] = candles_dict
                
                logger.info(f"  {symbol}: {len(symbol_data)} bars, {len(candles_dict)} candles indexed")
        
        logger.info(f"✅ Data loaded: {len(self.combined_data)} total bars")
        
        # PERF: Ne JAMAIS appeler _build_multi_timeframe_candles (legacy path bloquant)
        # L'agrégation se fait de manière incrémentale via TimeframeAggregator dans le loop
    
    def _build_multi_timeframe_candles(self):
        """Construit des listes de Candle multi-timeframes à partir des Parquet M1."""
        self.multi_tf_candles = {}

        for symbol, df in self.data.items():
            # S'assurer de l'ordre chronologique
            df_sorted = df.sort_values("datetime").reset_index(drop=True)

            # Construire les candles 1m
            candles_1m: List[Candle] = []
            for _, row in df_sorted.iterrows():
                candles_1m.append(
                    Candle(
                        symbol=symbol,
                        timeframe="1m",
                        timestamp=row["datetime"],
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=int(row.get("volume", 0)),
                    )
                )

            # Agrégation via pandas (similaire à DataFeedEngine.aggregate_to_higher_tf)
            def aggregate(candles: List[Candle], rule: str, tf: str) -> List[Candle]:
                if not candles:
                    return []
                import pandas as _pd

                _df = _pd.DataFrame(
                    [
                        {
                            "timestamp": c.timestamp,
                            "open": c.open,
                            "high": c.high,
                            "low": c.low,
                            "close": c.close,
                            "volume": c.volume,
                        }
                        for c in candles
                    ]
                )
                _df.set_index("timestamp", inplace=True)
                _df_resampled = _df.resample(rule).agg(
                    {
                        "open": "first",
                        "high": "max",
                        "low": "min",
                        "close": "last",
                        "volume": "sum",
                    }
                ).dropna()

                agg: List[Candle] = []
                for idx, r in _df_resampled.iterrows():
                    agg.append(
                        Candle(
                            symbol=symbol,
                            timeframe=tf,
                            timestamp=idx.to_pydatetime(),
                            open=float(r["open"]),
                            high=float(r["high"]),
                            low=float(r["low"]),
                            close=float(r["close"]),
                            volume=int(r["volume"]),
                        )
                    )
                return agg

            candles_5m = aggregate(candles_1m, "5T", "5m")
            candles_15m = aggregate(candles_1m, "15T", "15m")
            candles_1h = aggregate(candles_1m, "1H", "1h")
            candles_4h = aggregate(candles_1m, "4H", "4h")
            candles_1d = aggregate(candles_1m, "1D", "1d")

            self.multi_tf_candles[symbol] = {
                "1m": candles_1m,
                "5m": candles_5m,
                "15m": candles_15m,
                "1h": candles_1h,
                "4h": candles_4h,
                "1d": candles_1d,
            }

        logger.info(f"   Period: {self.combined_data['datetime'].min()} → {self.combined_data['datetime'].max()}")

    def _convert_candlestick_patterns(self, patterns: List[PatternDetection]) -> List[CandlestickPattern]:
        """Convertit les PatternDetection du moteur chandelles en CandlestickPattern
        compatibles avec les playbooks (famille + direction + strength).
        """
        converted: List[CandlestickPattern] = []

        for p in patterns:
            name = p.pattern_name.lower()

            # Déterminer la famille générique attendue par les playbooks
            if "engulfing" in name:
                family = "engulfing"
            elif "hammer" in name:
                family = "hammer"
            elif "shooting_star" in name:
                family = "shooting_star"
            elif "doji" in name:
                family = "doji"
            elif "marubozu" in name:
                family = "marubozu"
            elif "three_white_soldiers" in name:
                family = "three_soldiers"
            elif "three_black_crows" in name:
                family = "three_crows"
            elif "morning_star" in name:
                family = "morning_star"
            elif "evening_star" in name:
                family = "evening_star"
            else:
                # Par défaut on réutilise le nom comme famille
                family = name

            # Direction à partir du type de pattern
            ptype = p.pattern_type
            if "bullish" in ptype:
                direction = "bullish"
            elif "bearish" in ptype:
                direction = "bearish"
            else:
                direction = "neutral"

            converted.append(
                CandlestickPattern(
                    timestamp=p.timestamp,
                    timeframe=p.timeframe,
                    family=family,
                    name=p.pattern_name,
                    direction=direction,
                    strength=p.pattern_score,
                    body_size=0.0,
                    confirmation=True,
                    at_level=p.at_support_resistance,
                    after_sweep=p.after_sweep,
                )
            )

        return converted

    def run(self) -> BacktestResult:
        """Exécute le backtest complet (boucle minute par minute)."""
        logger.info("=" * 80)
        logger.info(
            "STARTING BACKTEST - mode=%s, trade_types=%s, symbols=%s",
            self.config.trading_mode,
            self.config.trade_types,
            self.config.symbols,
        )
        logger.info("=" * 80)

        # Load data
        self.load_data()

        start_date = self.combined_data["datetime"].min()
        end_date = self.combined_data["datetime"].max()

        # OPTIMISATION: Plus de pre-build multi-TF, on utilise l'agrégateur incrémental
        # self._build_multi_timeframe_candles()

        # Group by minute (pour traiter SPY et QQQ ensemble)
        self.combined_data["minute"] = self.combined_data["datetime"].dt.floor("1min")
        minutes = sorted(self.combined_data["datetime"].unique())  # Toutes les bougies 1m

        logger.info("\n📊 Processing %d bars (1m driver)...", len(minutes))

        # Loop chronologique (désactiver logs fréquents pour perf)
        log_interval = max(1000, len(minutes) // 10)  # Log tous les 10% ou min 1000
        for idx, current_time in enumerate(minutes):
            if idx % log_interval == 0 and idx > 0:
                logger.info(
                    "  Processed %d/%d bars (%.1f%%)",
                    idx,
                    len(minutes),
                    idx / len(minutes) * 100.0,
                )

            # 1) Ajouter les bougies 1m à l'agrégateur et détecter clôtures HTF
            htf_events = {}
            for symbol in self.config.symbols:
                # Accès O(1) au lieu de O(N)
                candle_1m = self.candles_1m_by_timestamp.get(symbol, {}).get(current_time)
                if candle_1m is None:
                    continue
                
                # Ajouter à l'agrégateur et récupérer les flags de clôture HTF
                events = self.tf_aggregator.add_1m_candle(candle_1m)
                htf_events[symbol] = events
            
            # 2) Générer au plus un setup par symbole pour cette minute
            candidate_setups: List[Setup] = []
            for symbol in self.config.symbols:
                # OPTIMISÉ: Utiliser _process_bar_optimized avec TimeframeAggregator + cache
                events = htf_events.get(symbol, {})
                setup = self._process_bar_optimized(symbol, current_time, events)
                if setup is not None:
                    candidate_setups.append(setup)

            # 3) Sélection multi-actifs globale SPY/QQQ (mode simple 2.a)
            if candidate_setups:
                def setup_priority(s: Setup) -> tuple:
                    quality_rank = {"A+": 3, "A": 2, "B": 1, "C": 0}
                    return (
                        quality_rank.get(s.quality, 0),
                        s.final_score,
                        s.confluences_count,
                        s.risk_reward,
                    )

                best_setup = max(candidate_setups, key=setup_priority)

                # Priorité DAILY > SCALP si on doit choisir un seul trade
                daily_setups = [s for s in candidate_setups if s.trade_type == "DAILY"]
                if daily_setups and best_setup.trade_type == "SCALP":
                    best_setup = max(daily_setups, key=setup_priority)

                # Vérifier limites de risque avant exécution
                limits_check = self.risk_engine.check_daily_limits()
                if limits_check["trading_allowed"]:
                    self._execute_setup(best_setup, current_time)

            # 3) Mettre à jour les positions ouvertes
            self._update_positions(current_time)

            # 4) Suivre la courbe d'equity
            self._track_equity(current_time)

        # Fermer toutes les positions restantes
        self._close_all_remaining_positions(end_date)

        # Générer résultats
        result = self._generate_result(start_date, end_date, len(minutes))

        # Sauvegarder
        self._save_results(result)

        logger.info("=" * 80)
        logger.info("BACKTEST COMPLETE - %d trades", result.total_trades)
        logger.info("=" * 80)

        return result
    
    def _process_bar_optimized(self, symbol: str, current_time: datetime, htf_events: Dict[str, bool]) -> Optional[Setup]:
        """
        Construit le meilleur setup pour un symbole et une minute donnée (VERSION OPTIMISÉE).
        
        Utilise l'agrégateur incrémental et le cache market_state pour éviter les recalculs inutiles.
        
        Args:
            symbol: Symbole (SPY/QQQ)
            current_time: Timestamp de la bougie 1m actuelle
            htf_events: Dict avec is_close_5m, is_close_10m, is_close_15m, is_close_1h, etc.
        
        Returns:
            Setup ou None
        """
        # Récupérer les candles depuis l'agrégateur
        candles_1m = self.tf_aggregator.get_candles(symbol, "1m")
        candles_5m = self.tf_aggregator.get_candles(symbol, "5m")
        # candles_10m = self.tf_aggregator.get_candles(symbol, "10m")  # Unused for now
        candles_15m = self.tf_aggregator.get_candles(symbol, "15m")
        candles_1h = self.tf_aggregator.get_candles(symbol, "1h")
        candles_4h = self.tf_aggregator.get_candles(symbol, "4h")
        candles_1d = self.tf_aggregator.get_candles(symbol, "1d")
        
        # Besoin d'historique minimum (INCLUANT 4h et 1d)
        if len(candles_1m) < 50 or len(candles_5m) < 5 or len(candles_1h) < 2:
            return None
        
        # 🔧 FIX P0: Vérifier aussi 4h et 1d avant de calculer market_state
        if len(candles_4h) < 1 or len(candles_1d) < 1:
            return None
        
        # Déterminer si on doit recalculer le market_state
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)
        session_info = get_session_info(current_time, debug_log=False)
        current_session = session_info.get('session', 'Unknown')
        
        # Clé de cache : (symbol, session, last_1h_close, last_4h_close, last_1d_close)
        last_1h_close = candles_1h[-1].timestamp if candles_1h else None
        last_4h_close = candles_4h[-1].timestamp if candles_4h else None
        last_1d_close = candles_1d[-1].timestamp if candles_1d else None
        
        cache_key = self.market_state_cache.get_cache_key(
            symbol, current_session, last_1h_close, last_4h_close, last_1d_close
        )
        
        # Vérifier si on doit recalculer
        should_recalc = self.market_state_cache.should_recalculate(symbol, cache_key)
        
        if should_recalc or htf_events.get("is_close_1h") or htf_events.get("is_close_4h") or htf_events.get("is_close_1d"):
            # Recalculer le market state (événement HTF majeur)
            multi_tf_data = {
                "1m": candles_1m[-500:],  # Limiter à 500 dernières
                "5m": candles_5m[-200:],
                "15m": candles_15m[-100:],
                "1h": candles_1h[-50:],
                "4h": candles_4h[-20:],
                "1d": candles_1d[-10:]
            }
            
            market_state = self.market_state_engine.create_market_state(
                symbol,
                multi_tf_data,
                {
                    "session": current_session,
                    "current_time": current_time,
                    "volatility": 0.0  # Placeholder
                }
            )
            
            # Mettre en cache
            self.market_state_cache.put(cache_key, market_state)
        else:
            # Utiliser le cache
            market_state = self.market_state_cache.get(cache_key)
            if market_state is None:
                # Fallback : recalculer si cache manquant
                multi_tf_data = {
                    "1m": candles_1m[-500:],
                    "5m": candles_5m[-200:],
                    "15m": candles_15m[-100:],
                    "1h": candles_1h[-50:],
                    "4h": candles_4h[-20:],
                    "1d": candles_1d[-10:]
                }
                
                market_state = self.market_state_engine.create_market_state(
                    symbol,
                    multi_tf_data,
                    {
                        "session": current_session,
                        "current_time": current_time,
                        "volatility": 0.0
                    }
                )
                self.market_state_cache.put(cache_key, market_state)
        
        # Patterns : calculer seulement sur clôture 5m ou supérieure (pas à chaque 1m)
        ict_patterns: List[ICTPattern] = []
        candle_patterns: List[CandlestickPattern] = []
        
        if htf_events.get("is_close_5m") or htf_events.get("is_close_15m"):
            # Détecter patterns candlesticks
            if len(candles_5m) > 10:
                raw_candle_patterns = self.candlestick_engine.detect_patterns(candles_5m[-100:], timeframe="5m")
                candle_patterns = self._convert_candlestick_patterns(raw_candle_patterns)
            
            # ICT patterns (BOS/FVG)
            if len(candles_5m) > 10:
                ict_patterns.extend(self.ict_engine.detect_bos(candles_5m[-100:], timeframe="5m"))
                ict_patterns.extend(self.ict_engine.detect_fvg(candles_5m[-100:], timeframe="5m"))
            
            if len(candles_15m) > 10 and htf_events.get("is_close_15m"):
                ict_patterns.extend(self.ict_engine.detect_fvg(candles_15m[-100:], timeframe="15m"))
        
        # Générer setup via SetupEngine
        setups = self.setup_engine.generate_setups(
            symbol=symbol,
            current_time=current_time,
            market_state=market_state,
            ict_patterns=ict_patterns,
            candle_patterns=candle_patterns,
            liquidity_levels=[],  # Liquidity levels désactivés temporairement
            trading_mode=self.config.trading_mode
        )
        
        if not setups:
            return None
        
        # Filtrer selon le mode (SAFE/AGGRESSIVE)
        filtered_setups = filter_setups_by_mode(setups, self.risk_engine)
        
        if not filtered_setups:
            return None
        
        # Retourner le meilleur setup
        return max(filtered_setups, key=lambda s: s.final_score)
    
    def _process_bar(self, symbol: str, current_time: datetime) -> Optional[Setup]:
        """Construit le meilleur setup pour un symbole et une minute donnée.

        Ne s'occupe PAS de la sélection multi-actifs ni de l'exécution, seulement
        de la génération du meilleur Setup (ou None) pour ce symbole/time.
        """

        # Get data up to current time (DataFrame brut)
        symbol_data = self.data[symbol]
        historical_data = symbol_data[symbol_data["datetime"] <= current_time].copy()

        if len(historical_data) < 50:  # Besoin d'historique minimum
            return None

        # OPTIMISATION: Utiliser rolling windows au lieu de tout l'historique
        # On garde seulement les N dernières bougies par TF
        ROLLING_WINDOW = {
            "1m": 500,   # ~8 heures
            "5m": 200,   # ~16 heures
            "15m": 100,  # ~1 jour
            "1h": 50,    # ~2 jours
            "4h": 20,    # ~3 jours
            "1d": 10     # ~2 semaines
        }
        
        # Construire les listes de Candle multi-TF filtrées jusqu'à current_time (avec rolling windows)
        mtf = self.multi_tf_candles.get(symbol, {})
        candles_1m = [c for c in mtf.get("1m", []) if c.timestamp <= current_time][-ROLLING_WINDOW["1m"]:]
        candles_5m = [c for c in mtf.get("5m", []) if c.timestamp <= current_time][-ROLLING_WINDOW["5m"]:]
        candles_15m = [c for c in mtf.get("15m", []) if c.timestamp <= current_time][-ROLLING_WINDOW["15m"]:]
        candles_1h = [c for c in mtf.get("1h", []) if c.timestamp <= current_time][-ROLLING_WINDOW["1h"]:]
        candles_4h = [c for c in mtf.get("4h", []) if c.timestamp <= current_time][-ROLLING_WINDOW["4h"]:]
        candles_1d = [c for c in mtf.get("1d", []) if c.timestamp <= current_time][-ROLLING_WINDOW["1d"]:]

        if (not candles_1m or not candles_5m or not candles_15m
                or not candles_1h or not candles_4h or not candles_1d):
            return None

        # Construire market state via MarketStateEngine (vrai moteur HTF)
        # Activer debug_log pour capturer les sessions dans la fenêtre 09:20-09:40 ET (SCALP A+)
        # IMPORTANT: current_time is UTC; session logic must run in ET.
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)
        session_info = get_session_info(current_time, debug_log=False)  # Désactiver debug pour perf
        multi_tf_data = {
            "1m": candles_1m,
            "5m": candles_5m,
            "15m": candles_15m,
            "1h": candles_1h,
            "4h": candles_4h,
            "1d": candles_1d,
        }
        market_state = self.market_state_engine.create_market_state(
            symbol,
            multi_tf_data,
            {"current_session": session_info.get("name", "ny"), "session_levels": {}},
        )

        # Dernier prix réel pour le symbole à current_time (close M1)
        last_close = candles_1m[-1].close

        # Liquidity levels + sweeps ICT sur ces données
        htf_levels = self.market_state_engine.mark_htf_levels(
            candles_1d,
            candles_4h,
            {
                "asia_high": None,
                "asia_low": None,
                "london_high": None,
                "london_low": None,
            },
        )
        _ = self.liquidity_engine.identify_liquidity_levels(
            symbol,
            multi_tf_data,
            htf_levels,
        )

        # Détecter patterns candlesticks, puis convertir vers CandlestickPattern
        raw_candle_patterns = self.candlestick_engine.detect_patterns(candles_5m, timeframe="5m") + \
            self.candlestick_engine.detect_patterns(candles_15m, timeframe="15m")
        candle_patterns = self._convert_candlestick_patterns(raw_candle_patterns)

        # ICT patterns (BOS/FVG sur les TF supérieurs)
        ict_patterns: List[ICTPattern] = []
        if candles_5m:
            # Limiter à 100 dernières bougies pour la détection (garde la logique complète)
            recent_5m = candles_5m[-100:] if len(candles_5m) > 100 else candles_5m
            ict_patterns.extend(self.ict_engine.detect_bos(recent_5m, timeframe="5m"))
            ict_patterns.extend(self.ict_engine.detect_fvg(recent_5m, timeframe="5m"))
        if candles_15m:
            recent_15m = candles_15m[-100:] if len(candles_15m) > 100 else candles_15m
            ict_patterns.extend(self.ict_engine.detect_fvg(recent_15m, timeframe="15m"))

        # SMT inter-actifs (SPY vs QQQ) si les deux symboles sont présents
        # OPTIMISATION: Désactiver SMT (non critique pour les playbooks actuels)
        # if set(self.config.symbols) >= {"SPY", "QQQ"} and symbol == "SPY":
        #     other = self.multi_tf_candles.get("QQQ", {})
        #     qqq_h1 = [c for c in other.get("1h", []) if c.timestamp <= current_time]
        #     if candles_1h and qqq_h1:
        #         smt = self.ict_engine.detect_smt(candles_1h, qqq_h1)
        #         if smt:
        #             ict_patterns.append(smt)

        # Détecter sweeps de liquidité sur la dernière bougie 5m
        sweeps: List[Dict[str, Any]] = []
        if candles_5m and len(candles_5m) > 1:
            last_5m = candles_5m[-1]
            prev_5m = candles_5m[-min(50, len(candles_5m)):-1]  # Limiter à 50 précédentes
            sweeps = self.liquidity_engine.detect_sweep(symbol, last_5m, prev_5m)

        # Eventuel CHOCH si sweep récent et données M5 suffisantes (réactivé)
        if sweeps and candles_5m:
            recent_5m_for_choch = candles_5m[-50:] if len(candles_5m) > 50 else candles_5m
            choch = self.ict_engine.detect_choch(recent_5m_for_choch, sweeps[-1])
            if choch:
                ict_patterns.append(choch)

        # Générer setups via playbooks
        setups = self.setup_engine.generate_setups(
            symbol=symbol,
            market_state=market_state,
            ict_patterns=ict_patterns,
            candle_patterns=candle_patterns,
            liquidity_levels=[],
            current_time=current_time,
            trading_mode=self.config.trading_mode,
            last_price=last_close,
        )
        
        # Instrumentation: compter les setups bruts
        self._record_setups_stats(symbol, current_time, setups, stage="raw")

        if not setups:
            return None
        
        # Filtrer selon mode (RiskEngine est l'autorité finale pour playbooks)
        setups = filter_setups_by_mode(setups, risk_engine=self.risk_engine)

        # Filtrer selon trade_types demandés
        setups = [s for s in setups if s.trade_type in self.config.trade_types]

        # Instrumentation: compter les setups après mode + trade_types
        if setups:
            self._record_setups_stats(symbol, current_time, setups, stage="after_mode")

        if not setups:
            return None

        # Appliquer la règle "1 setup max par symbole & par bougie":
        # choisir le meilleur selon qualité > score > confluences > RR.
        def setup_priority(s: Setup) -> tuple:
            quality_rank = {"A+": 3, "A": 2, "B": 1, "C": 0}
            return (
                quality_rank.get(s.quality, 0),
                s.final_score,
                s.confluences_count,
                s.risk_reward,
            )

        best_setup = max(setups, key=setup_priority)

        # On applique ici uniquement la contrainte "1 setup max par symbole".
        # La priorité globale DAILY > SCALP et la vérification du risque sont
        # gérées plus haut dans run().
        return best_setup
    
    def _build_market_state(self, symbol: str, historical_data: pd.DataFrame, current_time: datetime) -> MarketState:
        """Construit le market state (version simplifiée pour backtest)"""
        
        # Pour l'instant, version basique
        # TODO: Utiliser vraiment MarketStateEngine avec reconstruction multi-TF
        
        # Déterminer bias basé sur SMA simple
        recent_data = historical_data.tail(100)
        sma_20 = recent_data['close'].rolling(20).mean().iloc[-1]
        current_price = recent_data['close'].iloc[-1]
        
        if current_price > sma_20 * 1.01:
            bias = 'bullish'
            structure = 'uptrend'
        elif current_price < sma_20 * 0.99:
            bias = 'bearish'
            structure = 'downtrend'
        else:
            bias = 'neutral'
            structure = 'range'
        
        # Session (simplifié) - MUST be evaluated in US/Eastern (ET)
        # Data is stored in UTC; convert here for any session/time-window logic.
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)
        current_time_et = current_time.astimezone(pytz.timezone('US/Eastern'))
        hour = current_time_et.hour
        if 3 <= hour < 8:
            session = 'London'
        elif 9 <= hour < 16:
            session = 'NY'
        else:
            session = 'Asia'
        
        return MarketState(
            symbol=symbol,
            timestamp=current_time,
            bias=bias,
            daily_structure=structure,
            h4_structure=structure,
            h1_structure=structure,
            current_session=session,
            session_profile=1,
            pdh=recent_data['high'].max(),
            pdl=recent_data['low'].min(),
            asia_high=0.0,
            asia_low=0.0,
            london_high=0.0,
            london_low=0.0
        )
    
    def _detect_ict_patterns(self, symbol: str, historical_data: pd.DataFrame) -> List[ICTPattern]:
        """Détecte patterns ICT (version simplifiée)"""
        
        # Pour ce backtest initial, on simule quelques patterns
        # TODO: Utiliser vraiment ICTPatternEngine
        
        patterns = []
        
        # Simuler un sweep si prix touche un niveau clé
        recent = historical_data.tail(10)
        
        # TODO: pousser les trades vers le TradeJournal avec backtest_run_id si on
        # souhaite les merger dans le journal global dès cette phase.

        if len(recent) >= 5:
            high_5 = recent['high'].iloc[-5]
            current_high = recent['high'].iloc[-1]
            
            if current_high > high_5 * 1.002:  # Sweep au-dessus
                patterns.append(ICTPattern(
                    symbol=symbol,
                    timeframe='1m',
                    pattern_type='sweep',
                    direction='bullish',
                    price_level=current_high,
                    strength=0.7,
                    confidence=0.75,
                    timestamp=recent['datetime'].iloc[-1]
                ))
        
        return patterns
    
    def _detect_candle_patterns(self, symbol: str, historical_data: pd.DataFrame) -> List[CandlestickPattern]:
        """Détecte patterns chandelles (version simplifiée)"""
        
        # Pour ce backtest initial, on simule
        # TODO: Utiliser vraiment CandlestickPatternEngine
        
        patterns = []
        
        recent = historical_data.tail(3)
        if len(recent) >= 2:
            last = recent.iloc[-1]
            prev = recent.iloc[-2]
            
            body = abs(last['close'] - last['open'])
            range_size = last['high'] - last['low']
            
            # Engulfing simple
            if body / range_size > 0.7:  # Corps large
                if last['close'] > last['open'] and last['close'] > prev['high']:
                    patterns.append(CandlestickPattern(
                        timeframe='1m',
                        family='engulfing',
                        name='Bullish Engulfing',
                        direction='bullish',
                        strength=0.8,
                        body_size=body / range_size,
                        confirmation=True,
                        timestamp=last['datetime']
                    ))
        
        return patterns
    
    def _execute_setup(self, setup: Setup, current_time: datetime):
        """Exécute un setup (via RiskEngine + ExecutionEngine) avec 2R/1R money management."""
        
        # P0.6.1: Vérifier si stop_run a été déclenché
        if self._stop_run_triggered:
            logger.debug(f"⚠️ Setup refusé: STOP_RUN actif depuis {self._stop_run_time}")
            return
        
        # Vérifier si le setup peut être pris (circuit breakers, quotas, etc.)
        can_take = self.risk_engine.can_take_setup(setup)
        if not can_take['allowed']:
            logger.debug(f"⚠️ Setup refusé par RiskEngine: {can_take['reason']}")
            return
        
        # PATCH A: Vérifier cooldown et limite par session (ANTI-SPAM)
        # Obtenir session actuelle
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)
        session_info = get_session_info(current_time, debug_log=False)
        current_session = session_info.get('session', 'Unknown')
        
        cooldown_ok, cooldown_reason = self.risk_engine.check_cooldown_and_session_limit(
            setup, current_time, current_session
        )
        if not cooldown_ok:
            logger.debug(f"⚠️ Setup bloqué (anti-spam): {cooldown_reason}")
            # PATCH D: Tracker les rejets anti-spam
            playbook_name = setup.playbook_matches[0].playbook_name if setup.playbook_matches else "UNKNOWN"
            if "Cooldown" in cooldown_reason:
                self.blocked_by_cooldown += 1
                self.blocked_by_cooldown_details[playbook_name] = self.blocked_by_cooldown_details.get(playbook_name, 0) + 1
            elif "session" in cooldown_reason:
                self.blocked_by_session_limit += 1
                self.blocked_by_session_limit_details[playbook_name] = self.blocked_by_session_limit_details.get(playbook_name, 0) + 1
            return
        
        # Vérifier cap trades par symbole
        allowed, reason = self.risk_engine.check_trades_cap(setup.symbol, current_time.date())
        if not allowed:
            logger.debug(f"⚠️ Setup refusé: {reason}")
            return
        
        # Position sizing avec 2R/1R
        position_calc = self.risk_engine.calculate_position_size(setup)
        
        if not position_calc.valid:
            logger.info(f"⚠️ Setup non exécuté (position sizing invalide): {position_calc.reason}")
            return
        
        # Execute via paper trading engine
        risk_allocation = {
            'risk_pct': self.risk_engine.state.current_risk_pct,
            'risk_tier': position_calc.risk_tier,
            'risk_dollars': position_calc.risk_amount,
            'position_calc': position_calc
        }
        
        order_result = self.execution_engine.place_order(setup, risk_allocation, current_time=current_time)
        
        if order_result['success']:
            # Incrémenter le compteur de trades pour ce symbole
            self.risk_engine.increment_trades_count(setup.symbol, current_time.date())
            # PATCH A: Record pour anti-spam (cooldown + session limit)
            self.risk_engine.record_trade_for_cooldown(setup, current_time, current_session)
            logger.debug(f"  ✅ Trade opened: {setup.symbol} {setup.direction} @ {setup.entry_price:.2f} (tier={position_calc.risk_tier}R)")

    
    def _update_positions(self, current_time: datetime):
        """Met à jour les positions ouvertes avec les prix actuels et ingère les trades fermés."""

        # Récupérer prix actuels à partir des données historiques déjà chargées
        market_data: Dict[str, float] = {}
        for symbol in self.config.symbols:
            symbol_data = self.data[symbol]
            current_bars = symbol_data[symbol_data["datetime"] <= current_time]
            if not current_bars.empty:
                market_data[symbol] = float(current_bars["close"].iloc[-1])

        # Mettre à jour les positions (SL/TP/BE) via ExecutionEngine
        self.execution_engine.update_open_trades(market_data)

        # Ingestion des trades nouvellement fermés
        self._ingest_closed_trades(current_time)
        
        # P0.6.1: Vérifier circuit breakers après chaque clôture de trade
        self._check_circuit_breakers_after_trades(current_time)
    
    def _check_circuit_breakers_after_trades(self, current_time: datetime):
        """
        Vérifie les circuit breakers après clôture de trades.
        Si stop_run déclenché, marque le run comme arrêté.
        """
        cb_result = self.risk_engine.check_circuit_breakers(current_time.date())
        
        if cb_result['stop_run'] and not self._stop_run_triggered:
            self._stop_run_triggered = True
            self._stop_run_time = current_time
            self._stop_run_reason = cb_result['reason']
            
            # Log l'événement guardrail
            logger.warning(f"🛑 CIRCUIT BREAKER: {cb_result['reason']}")
            logger.warning(f"   MaxDD={self.risk_engine.state.max_drawdown_r:.2f}R at {current_time}")
            
            # Enregistrer l'événement dans les guardrail_events
            self._guardrail_events.append({
                'timestamp': current_time.isoformat(),
                'event_type': 'stop_run',
                'reason': cb_result['reason'],
                'max_drawdown_r': self.risk_engine.state.max_drawdown_r,
                'run_total_r': self.risk_engine.state.run_total_r,
            })
    
    def _close_all_remaining_positions(self, end_time: datetime):
        """Ferme toutes les positions restantes en fin de backtest puis ingère les trades fermés."""
        open_trades = self.execution_engine.get_open_trades()

        if open_trades:
            logger.info("\n🔚 Closing %d remaining positions...", len(open_trades))

            for trade in open_trades:
                # Prix de sortie = dernier prix connu
                symbol_data = self.data[trade.symbol]
                exit_price = float(symbol_data["close"].iloc[-1])
                self.execution_engine.close_trade(trade.id, "eod", exit_price)

        # Ingestion finale des trades fermés
        self._ingest_closed_trades(end_time)
    
    def _track_equity(self, current_time: datetime):
        """Track equity curve"""
        # Calculer equity totale
        cumulative_r = sum(t.pnl_r for t in self.trades)
        current_capital = self.risk_engine.state.account_balance
        
        self.equity_curve_r.append(cumulative_r)
        self.equity_curve_dollars.append(current_capital)
        self.equity_timestamps.append(current_time)
    
    def _generate_result(self, start_date: datetime, end_date: datetime, total_bars: int) -> BacktestResult:
        """Génère le BacktestResult final"""
        
        logger.info("\n📊 Generating backtest results...")
        
        # Calculer KPIs
        total_trades = len(self.trades)
        
        if total_trades == 0:
            logger.warning("No trades executed!")
            # Retourner résultat vide
            return self._empty_result(start_date, end_date, total_bars)
        
        wins = [t for t in self.trades if t.outcome == 'win']
        losses = [t for t in self.trades if t.outcome == 'loss']
        breakevens = [t for t in self.trades if t.outcome == 'breakeven']
        
        winrate = (len(wins) / total_trades) * 100 if total_trades > 0 else 0.0
        
        # R stats
        total_r = sum(t.pnl_r for t in self.trades)
        avg_r = total_r / total_trades if total_trades > 0 else 0.0
        avg_win_r = sum(t.pnl_r for t in wins) / len(wins) if wins else 0.0
        avg_loss_r = sum(t.pnl_r for t in losses) / len(losses) if losses else 0.0
        
        # Expectancy
        win_prob = winrate / 100
        loss_prob = 1 - win_prob
        expectancy_r = (win_prob * avg_win_r) + (loss_prob * avg_loss_r)
        
        # Profit factor
        gross_profit = sum(t.pnl_dollars for t in wins)
        gross_loss = abs(sum(t.pnl_dollars for t in losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
        
        # Drawdown
        max_dd_r = self._calculate_max_drawdown(self.equity_curve_r)
        
        final_capital = self.risk_engine.state.account_balance
        total_pnl_dollars = final_capital - self.config.initial_capital
        total_pnl_pct = (total_pnl_dollars / self.config.initial_capital) * 100
        
        max_dd_dollars = self._calculate_max_drawdown(self.equity_curve_dollars)
        max_dd_pct = (max_dd_dollars / self.risk_engine.state.peak_balance) * 100
        
        # Streaks
        max_win_streak, max_loss_streak = self._calculate_streaks()
        
        # Stats breakdown
        stats_by_type = self._calculate_stats_by_type()
        stats_by_symbol = self._calculate_stats_by_symbol()
        stats_by_playbook = self._calculate_stats_by_playbook()
        stats_by_quality = self._calculate_stats_by_quality()
        
        # Best/Worst
        best_trade_r = max(t.pnl_r for t in self.trades) if self.trades else 0.0
        worst_trade_r = min(t.pnl_r for t in self.trades) if self.trades else 0.0
        
        # Output dir
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Build result
        result = BacktestResult(
            config=self.config,
            start_date=start_date,
            end_date=end_date,
            total_bars=total_bars,
            total_days=(end_date - start_date).days,
            initial_capital=self.config.initial_capital,
            final_capital=final_capital,
            total_pnl_dollars=total_pnl_dollars,
            total_pnl_pct=total_pnl_pct,
            total_pnl_r=total_r,
            equity_curve_r=self.equity_curve_r,
            equity_curve_dollars=self.equity_curve_dollars,
            equity_timestamps=self.equity_timestamps,
            max_drawdown_r=max_dd_r,
            max_drawdown_pct=max_dd_pct,
            max_drawdown_dollars=max_dd_dollars,
            total_trades=total_trades,
            wins=len(wins),
            losses=len(losses),
            breakevens=len(breakevens),
            winrate=winrate,
            avg_r=avg_r,
            avg_win_r=avg_win_r,
            avg_loss_r=avg_loss_r,
            expectancy_r=expectancy_r,
            profit_factor=profit_factor,
            max_win_streak=max_win_streak,
            max_loss_streak=max_loss_streak,
            current_streak=0,
            stats_by_type=stats_by_type,
            stats_by_symbol=stats_by_symbol,
            stats_by_playbook=stats_by_playbook,
            stats_by_quality=stats_by_quality,
            trades=self.trades,
            best_trade_r=best_trade_r,
            worst_trade_r=worst_trade_r,
            times_risk_reduced=0,  # TODO: Track from RiskEngine
            times_frozen=0,
            output_dir=str(output_dir),
        )
        
        logger.info("✅ Results generated: %d trades, %.1f%% WR, %.3fR exp", total_trades, winrate, expectancy_r)
        
        return result

    def _record_setups_stats(self, symbol: str, current_time: datetime, setups: List[Setup], stage: str) -> None:
        """Enregistre des stats de setups par jour / symbole / type / qualité.

        stage: "raw" (avant filtre de mode) ou "after_mode" (après SAFE/AGGR + trade_types)
        """
        date_str = current_time.date().isoformat()
        day_stats = self.setup_stats.setdefault(date_str, {})
        sym_stats = day_stats.setdefault(symbol, {
            "raw": {},
            "after_mode": {},
            "trades_executed": 0,
            "minutes_with_A_plus": 0,
            "sessions": {}
        })

        # Session / kill zone
        from utils.timeframes import get_session_info, is_in_kill_zone
        session_info = get_session_info(current_time)
        session_name = session_info.get("name", "off_hours")
        kz_info = is_in_kill_zone(current_time)
        kz_name = kz_info.get("zone_name") if kz_info.get("in_kill_zone") else None

        session_stats = sym_stats["sessions"].setdefault(session_name, {
            "raw": {},
            "after_mode": {},
            "minutes_with_A_plus": 0,
            "kill_zones": {}
        })
        if kz_name:
            kz_stats = session_stats["kill_zones"].setdefault(kz_name, {
                "raw": {},
                "after_mode": {},
                "minutes_with_A_plus": 0
            })
        else:
            kz_stats = None

        # Regrouper par (type, quality) et par playbook
        def inc(counter: Dict[Tuple[str, str], int], trade_type: str, quality: str) -> None:
            key = (trade_type, quality or "?")
            counter[key] = counter.get(key, 0) + 1

        # Compteurs globaux (par type/qualité)
        bucket = sym_stats.setdefault(stage, {})
        session_bucket = session_stats.setdefault(stage, {})
        kz_bucket = kz_stats.setdefault(stage, {}) if kz_stats is not None else None

        # Compteurs par playbook
        pb_key = f"playbooks_{stage}"
        pb_bucket = sym_stats.setdefault(pb_key, {})
        pb_session_bucket = session_stats.setdefault(pb_key, {})
        pb_kz_bucket = kz_stats.setdefault(pb_key, {}) if kz_stats is not None else None

        has_A_plus = False

        for s in setups:
            trade_type = getattr(s, "trade_type", "UNKNOWN")
            quality = getattr(s, "quality", "?")
            inc(bucket, trade_type, quality)
            inc(session_bucket, trade_type, quality)
            if kz_bucket is not None:
                inc(kz_bucket, trade_type, quality)

            # Incrémenter par playbook pour tous les playbooks matchés sur ce setup
            playbook_names = []
            for m in getattr(s, "playbook_matches", []) or []:
                name = getattr(m, "playbook_name", None)
                if name:
                    playbook_names.append(name)

            for pb_name in playbook_names:
                pb_ctr = pb_bucket.setdefault(pb_name, {})
                pb_s_ctr = pb_session_bucket.setdefault(pb_name, {})
                pb_kz_ctr = pb_kz_bucket.setdefault(pb_name, {}) if pb_kz_bucket is not None else None

                inc(pb_ctr, trade_type, quality)
                inc(pb_s_ctr, trade_type, quality)
                if pb_kz_ctr is not None:
                    inc(pb_kz_ctr, trade_type, quality)

            if quality == "A+":
                has_A_plus = True

        if has_A_plus and stage == "raw":
            # Minute où au moins un A+ a été vu (brut)
            sym_stats["minutes_with_A_plus"] += 1
            session_stats["minutes_with_A_plus"] += 1
            if kz_stats is not None:
                kz_stats["minutes_with_A_plus"] += 1


    def _ingest_closed_trades(self, timestamp: datetime):
        """Convertit les trades fermés en TradeResult et met à jour RiskEngine (2R/1R).

        On s'appuie sur ExecutionEngine.get_closed_trades() et on filtre ceux déjà
        traités grâce à _journaled_trade_ids.
        """
        from models.trade import Trade  # import local pour éviter les cycles

        closed_trades: List[Trade] = self.execution_engine.get_closed_trades()

        for trade in closed_trades:
            if trade.id in self._journaled_trade_ids:
                continue

            # Marquer comme traité
            self._journaled_trade_ids.add(trade.id)

            # Déterminer le résultat du trade
            trade_result_str = 'win' if trade.pnl_dollars > 0 else ('loss' if trade.pnl_dollars < 0 else 'breakeven')
            
            # Récupérer le tier de risque utilisé (default 2 si pas enregistré)
            risk_tier = getattr(trade, 'risk_tier', 2)
            risk_dollars = getattr(trade, 'risk_amount', self.risk_engine.state.base_r_unit_dollars * risk_tier)
            
            # Nom du playbook pour stats
            pb_name = getattr(trade, "playbook", None) or "UNKNOWN"
            
            # Mettre à jour RiskEngine avec 2R/1R money management
            current_day = (trade.time_exit or timestamp).date()
            risk_update = self.risk_engine.update_risk_after_trade(
                trade_result=trade_result_str,
                trade_pnl_dollars=trade.pnl_dollars or 0.0,
                trade_risk_dollars=risk_dollars,
                trade_tier=risk_tier,
                playbook_name=pb_name,
                current_day=current_day
            )

            # Incrémenter le compteur de trades exécutés pour ce jour/symbole
            date_str = current_day.isoformat()
            day_stats = self.setup_stats.setdefault(date_str, {})
            sym_stats = day_stats.setdefault(trade.symbol, {
                "raw": {},
                "after_mode": {},
                "trades_executed": 0,
                "minutes_with_A_plus": 0,
                "sessions": {}
            })
            sym_stats["trades_executed"] += 1

            # Incrémenter par playbook pour observabilité fine
            pb_key = "trades_by_playbook"
            pb_bucket = sym_stats.setdefault(pb_key, {})
            stats = pb_bucket.setdefault(pb_name, {"count": 0, "total_r": 0.0})
            stats["count"] += 1
            stats["total_r"] += float(trade.r_multiple or 0.0)

            # Construire TradeResult pour le BacktestResult
            trade_result = TradeResult(
                trade_id=trade.id,
                timestamp_entry=trade.time_entry,
                timestamp_exit=trade.time_exit or timestamp,
                duration_minutes=trade.duration_minutes or 0.0,
                symbol=trade.symbol,
                direction=trade.direction,
                trade_type=trade.trade_type,
                playbook=trade.playbook,
                quality=trade.setup_quality,
                entry_price=trade.entry_price,
                exit_price=trade.exit_price,
                stop_loss=trade.stop_loss,
                take_profit_1=trade.take_profit_1,
                position_size=trade.position_size,
                risk_pct=trade.risk_pct,
                risk_amount=risk_dollars,
                pnl_dollars=trade.pnl_dollars,
                pnl_r=trade.r_multiple,
                outcome=trade.outcome,
                exit_reason=trade.exit_reason,
            )
            self.trades.append(trade_result)

            # Pousser dans le TradeJournal global avec backtest_run_id
            context = {
                "account_balance": self.risk_engine.state.account_balance,
                "trading_mode": self.risk_engine.state.trading_mode,
                "backtest_run_id": self.run_id,
                "risk_tier": risk_tier,
                "pnl_r_account": risk_update['pnl_r_account'],
                "r_multiple": risk_update['r_multiple'],
            }
            self.trade_journal.add_entry(trade, context)

            logger.info(
                "  📝 Trade closed & journaled: %s %s %.2fR tier=%dR (run_id=%s)",
                trade.symbol,
                trade.outcome.upper(),
                trade.r_multiple,
                risk_tier,
                self.run_id,
            )
    
    def _empty_result(self, start_date: datetime, end_date: datetime, total_bars: int) -> BacktestResult:
        """Retourne un résultat vide si aucun trade"""
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        return BacktestResult(
            config=self.config,
            start_date=start_date,
            end_date=end_date,
            total_bars=total_bars,
            total_days=(end_date - start_date).days,
            initial_capital=self.config.initial_capital,
            final_capital=self.config.initial_capital,
            total_pnl_dollars=0.0,
            total_pnl_pct=0.0,
            total_pnl_r=0.0,
            max_drawdown_r=0.0,
            max_drawdown_pct=0.0,
            max_drawdown_dollars=0.0,
            total_trades=0,
            wins=0,
            losses=0,
            breakevens=0,
            winrate=0.0,
            avg_r=0.0,
            avg_win_r=0.0,
            avg_loss_r=0.0,
            expectancy_r=0.0,
            profit_factor=0.0,
            max_win_streak=0,
            max_loss_streak=0,
            current_streak=0,
            output_dir=str(output_dir)
        )
    
    def _calculate_max_drawdown(self, values: List[float]) -> float:
        """Calcule le max drawdown"""
        if not values:
            return 0.0
        
        peak = values[0]
        max_dd = 0.0
        
        for value in values:
            if value > peak:
                peak = value
            dd = peak - value
            if dd > max_dd:
                max_dd = dd
        
        return max_dd
    
    def _calculate_streaks(self) -> tuple:
        """Calcule max win/loss streaks"""
        max_win_streak = 0
        max_loss_streak = 0
        current_win = 0
        current_loss = 0
        
        for trade in self.trades:
            if trade.outcome == 'win':
                current_win += 1
                current_loss = 0
                max_win_streak = max(max_win_streak, current_win)
            elif trade.outcome == 'loss':
                current_loss += 1
                current_win = 0
                max_loss_streak = max(max_loss_streak, current_loss)
        
        return max_win_streak, max_loss_streak
    
    def _calculate_stats_by_type(self) -> Dict:
        """Stats par type de trade"""
        stats = {}
        
        for trade_type in ['DAILY', 'SCALP']:
            type_trades = [t for t in self.trades if t.trade_type == trade_type]
            if type_trades:
                wins = [t for t in type_trades if t.outcome == 'win']
                stats[trade_type] = {
                    'trades': len(type_trades),
                    'wins': len(wins),
                    'winrate': (len(wins) / len(type_trades)) * 100,
                    'avg_r': sum(t.pnl_r for t in type_trades) / len(type_trades),
                    'total_r': sum(t.pnl_r for t in type_trades)
                }
        
        return stats
    
    def _calculate_stats_by_symbol(self) -> Dict:
        """Stats par symbole"""
        stats = {}
        
        for symbol in self.config.symbols:
            symbol_trades = [t for t in self.trades if t.symbol == symbol]
            if symbol_trades:
                wins = [t for t in symbol_trades if t.outcome == 'win']
                stats[symbol] = {
                    'trades': len(symbol_trades),
                    'wins': len(wins),
                    'winrate': (len(wins) / len(symbol_trades)) * 100,
                    'avg_r': sum(t.pnl_r for t in symbol_trades) / len(symbol_trades),
                    'total_r': sum(t.pnl_r for t in symbol_trades)
                }
        
        return stats
    
    def _calculate_stats_by_playbook(self) -> Dict:
        """Stats par playbook"""
        stats = {}
        
        playbooks = set(t.playbook for t in self.trades)
        for playbook in playbooks:
            pb_trades = [t for t in self.trades if t.playbook == playbook]
            wins = [t for t in pb_trades if t.outcome == 'win']
            stats[playbook] = {
                'trades': len(pb_trades),
                'wins': len(wins),
                'winrate': (len(wins) / len(pb_trades)) * 100 if pb_trades else 0,
                'avg_r': sum(t.pnl_r for t in pb_trades) / len(pb_trades) if pb_trades else 0,
                'total_r': sum(t.pnl_r for t in pb_trades)
            }
        
        return stats
    
    def _calculate_stats_by_quality(self) -> Dict:
        """Stats par quality"""
        stats = {}
        
        qualities = set(t.quality for t in self.trades)
        for quality in qualities:
            qual_trades = [t for t in self.trades if t.quality == quality]
            wins = [t for t in qual_trades if t.outcome == 'win']
            stats[quality] = {
                'trades': len(qual_trades),
                'wins': len(wins),
                'winrate': (len(wins) / len(qual_trades)) * 100 if qual_trades else 0,
                'avg_r': sum(t.pnl_r for t in qual_trades) / len(qual_trades) if qual_trades else 0,
                'total_r': sum(t.pnl_r for t in qual_trades)
            }
        
        return stats
    
    def _save_results(self, result: BacktestResult):
        """Sauvegarde les résultats"""
        output_dir = Path(self.config.output_dir)
        
        # Timestamp pour nommage (run_id déjà unique, on peut s'en servir)
        run_id = self.run_id
        mode = result.config.trading_mode
        types = '_'.join(result.config.trade_types)

        # Fichiers de sortie
        summary_path = output_dir / f"summary_{run_id}_{mode}_{types}.json"
        trades_path = output_dir / f"trades_{run_id}_{mode}_{types}.parquet"
        equity_path = output_dir / f"equity_{run_id}_{mode}_{types}.parquet"

        # Sauvegarde JSON de synthèse
        import json

        summary = {
            "run_id": run_id,
            "mode": mode,
            "trade_types": result.config.trade_types,
            "symbols": result.config.symbols,
            "start_date": result.start_date.isoformat(),
            "end_date": result.end_date.isoformat(),
            "initial_capital": result.initial_capital,
            "final_capital": result.final_capital,
            "total_pnl_dollars": result.total_pnl_dollars,
            "total_pnl_pct": result.total_pnl_pct,
            "total_pnl_r": result.total_pnl_r,
            "total_trades": result.total_trades,
            "wins": result.wins,
            "losses": result.losses,
            "breakevens": result.breakevens,
            "winrate": result.winrate,
            "avg_r": result.avg_r,
            "avg_win_r": result.avg_win_r,
            "avg_loss_r": result.avg_loss_r,
            "expectancy_r": result.expectancy_r,
            "profit_factor": result.profit_factor,
            "max_drawdown_r": result.max_drawdown_r,
            "max_drawdown_pct": result.max_drawdown_pct,
            "max_drawdown_dollars": result.max_drawdown_dollars,
            "stats_by_type": result.stats_by_type,
            "stats_by_symbol": result.stats_by_symbol,
            "stats_by_playbook": result.stats_by_playbook,
            "stats_by_quality": result.stats_by_quality,
        }

        with summary_path.open("w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        # Sauvegarde trades avec tous les champs P0.4 requis
        import pandas as _pd
        
        base_r = self.risk_engine.state.base_r_unit_dollars
        cumulative_r = 0.0
        trades_records = []
        
        for t in result.trades:
            # Calculer r_multiple correctement: pnl_$ / risk_$ (signé)
            risk_dollars = t.risk_amount or (base_r * 2)
            r_multiple = t.pnl_dollars / risk_dollars if risk_dollars > 0 else 0.0
            
            # pnl_R_account basé sur base_r_unit
            pnl_r_account = t.pnl_dollars / base_r if base_r > 0 else 0.0
            cumulative_r += pnl_r_account
            
            trades_records.append({
                "trade_id": t.trade_id,
                "timestamp_entry": t.timestamp_entry,
                "timestamp_exit": t.timestamp_exit,
                "date": t.timestamp_entry.date().isoformat() if t.timestamp_entry else None,
                "month": t.timestamp_entry.strftime("%Y-%m") if t.timestamp_entry else None,
                "symbol": t.symbol,
                "playbook": t.playbook,
                "direction": t.direction,
                "trade_type": t.trade_type,
                "quality": t.quality,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "stop_loss": t.stop_loss,
                "take_profit_1": t.take_profit_1,
                "position_size": t.position_size,
                "duration_minutes": t.duration_minutes,
                "risk_pct": t.risk_pct,
                "pnl_dollars": t.pnl_dollars,
                "risk_dollars": risk_dollars,
                "r_multiple": r_multiple,
                "risk_tier": getattr(t, 'risk_tier', 2),
                "pnl_R_account": pnl_r_account,
                "cumulative_R": cumulative_r,
                "outcome": t.outcome,
                "exit_reason": t.exit_reason,
            })

        trades_df = _pd.DataFrame(trades_records)
        trades_df.to_parquet(trades_path, index=False)
        
        # Export CSV également pour analyse facile
        trades_csv_path = output_dir / f"trades_{run_id}_{mode}_{types}.csv"
        trades_df.to_csv(trades_csv_path, index=False)
        logger.info(f"  - Trades CSV: {trades_csv_path}")

        # Sauvegarde equity curve
        equity_df = _pd.DataFrame(
            {
                "timestamp": result.equity_timestamps,
                "equity_r": result.equity_curve_r,
                "equity_dollars": result.equity_curve_dollars,
            }
        )
        equity_df.to_parquet(equity_path, index=False)

        # Sauvegarde des stats de setups si disponibles
        if self.setup_stats:
            setup_stats_path = output_dir / f"setup_stats_backtest_{run_id}_{mode}_{types}.json"
            import json as _json

            # Conversion récursive: toutes les clés de dict deviennent des chaînes
            def make_jsonable(obj):
                if isinstance(obj, dict):
                    return {str(k): make_jsonable(v) for k, v in obj.items()}
                if isinstance(obj, list):
                    return [make_jsonable(v) for v in obj]
                return obj

            safe_stats = make_jsonable(self.setup_stats)

            with setup_stats_path.open("w", encoding="utf-8") as f:
                _json.dump(safe_stats, f, indent=2, default=str)
        else:
            setup_stats_path = None

        # Debug timefilters SCALP A+ et scoring DAY A+
        try:
            from engines.playbook_loader import TIMEFILTER_DEBUG, DEBUG_DAY_APLUS, DEBUG_DAY_APLUS_SCORING
            from utils.timeframes import export_session_debug, SESSION_DEBUG_BUFFER
            import json as _json_dbg

            # A) debug_timefilter_<run_id>.json
            tf_debug = TIMEFILTER_DEBUG.get('SCALP_Aplus_1_Mini_FVG_Retest_NY_Open', {})
            tf_payload = {
                "run_id": self.run_id,
                "playbook": "SCALP_Aplus_1_Mini_FVG_Retest_NY_Open",
                "N_total_bars_checked": tf_debug.get('total_checked', 0),
                "N_pass_session": tf_debug.get('pass_session', 0),
                "N_pass_time_range": tf_debug.get('pass_time_range', 0),
                "N_pass_both": tf_debug.get('pass_both', 0),
                "samples": tf_debug.get('samples', []),
            }
            debug_timefilter_path = output_dir / f"debug_timefilter_{self.run_id}.json"
            with debug_timefilter_path.open("w", encoding="utf-8") as f_dbg:
                _json_dbg.dump(tf_payload, f_dbg, indent=2)
            
            # A.1) debug_sessions_<run_id>.jsonl (nouveau fichier avec timestamps détaillés)
            export_session_debug(output_dir, run_id)
            logger.info(f"  - Session debug: {len(SESSION_DEBUG_BUFFER)} entries")

            # B) debug_day_aplus_200_<run_id>.jsonl + stats
            if DEBUG_DAY_APLUS:
                debug_day_path = output_dir / f"debug_day_aplus_200_{run_id}.jsonl"
                with debug_day_path.open("w", encoding="utf-8") as f_dbg2:
                    for row in DEBUG_DAY_APLUS:
                        f_dbg2.write(_json_dbg.dumps(row) + "\n")

                # Stats sur les composantes
                vals = DEBUG_DAY_APLUS
                n = len(vals)

                def stats_for(key: str):
                    arr = [float(v.get(key, 0.0)) for v in vals]
                    arr_sorted = sorted(arr)
                    if not arr_sorted:
                        return {"min": 0.0, "median": 0.0, "p90": 0.0}
                    def percentile(p):
                        if not arr_sorted:
                            return 0.0
                        k = int((len(arr_sorted) - 1) * p)
                        return arr_sorted[k]
                    return {
                        "min": arr_sorted[0],
                        "median": percentile(0.5),
                        "p90": percentile(0.9),
                    }

                def pct_flag(key: str):
                    if not vals:
                        return 0.0
                    c = sum(1 for v in vals if v.get(key, False))
                    return 100.0 * c / len(vals)

                comp_keys = [
                    "liquidity_sweep_score",
                    "bos_strength_score",
                    "fvg_quality_score",
                    "pattern_quality_score",
                ]
                flag_keys = [
                    "sweep_detected",
                    "bos_detected",
                    "fvg_detected",
                    "pattern_detected",
                ]

                stats_payload = {
                    "run_id": run_id,
                    "n_setups": n,
                    "components": {k: stats_for(k) for k in comp_keys},
                    "flags": {f"{k}_pct": pct_flag(k) for k in flag_keys},
                    "quality_distribution": {},
                }

                q_counts: Dict[str, int] = {}
                for v in vals:
                    q = str(v.get("quality", "?"))
                    q_counts[q] = q_counts.get(q, 0) + 1
                stats_payload["quality_distribution"] = q_counts

                debug_stats_path = output_dir / f"debug_day_aplus_stats_{run_id}.json"
                with debug_stats_path.open("w", encoding="utf-8") as f_dbg3:
                    _json_dbg.dump(stats_payload, f_dbg3, indent=2)
            
            # C) debug_day_aplus_scoring_<run_id>.jsonl (reason for zero score)
            if DEBUG_DAY_APLUS_SCORING:
                debug_scoring_path = output_dir / f"debug_day_aplus_scoring_{run_id}.jsonl"
                with debug_scoring_path.open("w", encoding="utf-8") as f_dbg4:
                    for row in DEBUG_DAY_APLUS_SCORING:
                        f_dbg4.write(_json_dbg.dumps(row) + "\n")
                logger.info(f"  - DAY A+ scoring debug: {len(DEBUG_DAY_APLUS_SCORING)} entries -> {debug_scoring_path}")
        except Exception as e:
            logger.warning(f"Debug export failed: {e}")

        # P0: Export des nouvelles stats (playbook_stats, daily_stats, run_stats)
        try:
            import json as _json_p0
            
            # D) risk_engine_stats_<run_id>.json (stats globales du run + circuit breakers)
            run_stats = self.risk_engine.get_run_stats()
            # Ajouter les infos de stop_run du backtest
            run_stats['stop_run_triggered'] = self._stop_run_triggered
            run_stats['stop_run_time'] = self._stop_run_time.isoformat() if self._stop_run_time else None
            run_stats['stop_run_reason'] = self._stop_run_reason
            run_stats_path = output_dir / f"risk_engine_stats_{run_id}.json"
            with run_stats_path.open("w", encoding="utf-8") as f_run:
                _json_p0.dump(run_stats, f_run, indent=2)
            logger.info(f"  - RiskEngine stats: {run_stats_path}")
            
            # D.1) guardrails_events_<run_id>.jsonl (événements circuit breakers)
            if self._guardrail_events:
                guardrails_path = output_dir / f"guardrails_events_{run_id}.jsonl"
                with guardrails_path.open("w", encoding="utf-8") as f_guard:
                    for evt in self._guardrail_events:
                        f_guard.write(_json_p0.dumps(evt) + "\n")
                logger.info(f"  - Guardrails events: {guardrails_path} ({len(self._guardrail_events)} events)")
            
            # E) playbook_stats_<run_id>.json (stats par playbook pour kill-switch)
            playbook_stats = self.risk_engine.get_playbook_stats()
            playbook_stats_path = output_dir / f"playbook_stats_{run_id}.json"
            with playbook_stats_path.open("w", encoding="utf-8") as f_pb:
                _json_p0.dump(playbook_stats, f_pb, indent=2)
            logger.info(f"  - Playbook stats: {playbook_stats_path}")
            
            # F) daily_stats_<run_id>.json (stats par jour pour instrumentation)
            daily_stats = self.risk_engine.get_daily_stats()
            daily_stats_path = output_dir / f"daily_stats_{run_id}.json"
            with daily_stats_path.open("w", encoding="utf-8") as f_daily:
                _json_p0.dump(daily_stats, f_daily, indent=2)
            logger.info(f"  - Daily stats: {daily_stats_path}")
            
            # Log des playbooks désactivés par kill-switch
            if run_stats.get('disabled_playbooks'):
                logger.warning(f"⚠️ Playbooks disabled by kill-switch: {run_stats['disabled_playbooks']}")
            
        except Exception as e:
            logger.warning(f"P0 stats export failed: {e}")

        logger.info("\n💾 Results saved to: %s", output_dir)
        logger.info("  - Summary: %s", summary_path)
        logger.info("  - Trades : %s", trades_path)
        logger.info("  - Equity : %s", equity_path)
        if setup_stats_path is not None:
            logger.info("  - Setup stats: %s", setup_stats_path)
