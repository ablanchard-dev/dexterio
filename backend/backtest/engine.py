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
from backtest.costs import calculate_total_execution_costs  # PHASE B
from engines.market_state import MarketStateEngine
from engines.liquidity import LiquidityEngine
from engines.patterns.candlesticks import CandlestickPatternEngine
from engines.patterns.ict import ICTPatternEngine
# Unified detectors for BOS/FVG and custom ICT patterns
from engines.patterns.custom_detectors import (
    detect_custom_patterns,
    detect_smt_pattern,
    detect_choch_pattern,
)
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
        # P0 TÂCHE 1B: Forcer explicitement le mode de trading du RiskEngine selon la config
        old_mode = self.risk_engine.state.trading_mode
        self.risk_engine.state.trading_mode = config.trading_mode
        logger.warning(
            f"[P0] BacktestEngine forced risk mode => "
            f"{self.risk_engine.state.trading_mode} (config={config.trading_mode}, was={old_mode})"
        )
        assert self.risk_engine.state.trading_mode == config.trading_mode, \
            f"RiskEngine mode mismatch: {self.risk_engine.state.trading_mode} != {config.trading_mode}"
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
        
        # Collecteur de tous les setups générés (pour funnel post-run)
        self.all_generated_setups: List[Setup] = []
        
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
        
        # P2-2.B: Market state stream (instrumentation)
        self.market_state_records = [] if config.export_market_state else None

        # P1: Inter-session state tracking (logging only)
        # Structure: {symbol: {session_label: {open, high, low, close, range, date}}}
        self._session_states: Dict[str, Dict[str, Dict[str, Any]]] = {}
        # Historique des ranges de session pour calculer vol_regime (dernières N sessions) - PAR SYMBOL
        self._session_ranges_history: Dict[str, List[float]] = {}  # {symbol: [ranges]}
        self._last_session_label: Dict[str, Optional[str]] = {}  # {symbol: last_session_label}

        # DIAGNOSTIC: Compteurs d'instrumentation
        self.debug_counts = {
            "candles_loaded_1m": 0,
            "candles_loaded_htf": {},  # {timeframe: count}
            "setups_detected_total": 0,
            "setups_rejected_total": 0,
            "setups_accepted_total": 0,
            "setups_rejected_by_mode": 0,
            "setups_rejected_by_trade_types": 0,
            "trades_opened_total": 0,
            "trades_closed_total": 0,
            "reject_reasons": {},  # {reason: count}
            "bars_processed": 0,  # P0 DEBUG
            # P0 ÉTAPE 3: Instrumentation playbooks
            "playbooks_registered_count": 0,
            "playbooks_registered_names": [],
            "playbooks_evaluated_total": 0,
            "playbooks_evaluated_unique": {},  # {playbook_name: count}
            # P0 FIX: Compteurs distincts matches vs setups vs trades
            "matches_total": 0,  # Avant tout filtre
            "matches_by_playbook": {},  # {playbook_name: count}
            "setups_created_total": 0,  # Setups réellement créés
            "setups_created_by_playbook": {},  # {playbook_name: count}
            "setups_after_risk_filter_total": 0,  # Après RiskEngine
            "setups_after_risk_filter_by_playbook": {},  # {playbook_name: count}
            "trades_open_attempted_total": 0,  # Tentatives d'ouverture
            "trades_opened_total": 0,
            "trades_open_rejected_by_reason": {},  # {reason: count, max 10}
            # Legacy (gardé pour compatibilité)
            "setups_detected_by_playbook": {},  # Alias de setups_created_by_playbook
            "setups_rejected_by_reason": {},  # {reason: count}
            "setups_rejected_by_mode_by_playbook": {},  # {playbook_name: count}
            "setups_rejected_by_mode_examples": [],  # Max 5 exemples
            "missing_playbook_name": 0,  # Setups sans playbook_name
            # P0 TÂCHE 3: Champs détaillés pour diagnostic
            "risk_mode_used": "",  # Mode réellement utilisé par RiskEngine
            "risk_allowlist_snapshot": {},  # Snapshot des allowlists (len + first5)
            "risk_rejects_by_playbook": {},  # Rejets détaillés par playbook
            "risk_reject_examples": [],  # Exemples détaillés de rejets (max 5)
            # P0 PLUMBING: Diagnostic entrée/sortie RiskEngine
            "risk_input_setups_len": 0,
            "risk_output_setups_len": 0,
            "risk_first3_input_playbooks": [],
            "risk_first3_output_playbooks": [],
            # OPTION B: Caps & répartition trades
            "caps_snapshot": {},
            "trades_opened_by_playbook": {},           # {playbook_name: count}
            "trades_attempted_by_playbook": {},        # {playbook_name: count}
            "session_limit_reached_by_playbook": {},   # {playbook_name: count}
            "session_key_used": "",                    # Clé hybride session+bucket4h
            "grade_counts_by_playbook": {},            # {playbook_name: {A+,A,B,C,UNKNOWN}}
            # P1: Inter-session state tracking (logging only)
            "trade_context_snapshots": [],              # Liste de snapshots (max 200)
            # P0.2: Multi-symbol instrumentation
            "symbols_processed": [],                    # Liste des symboles réellement traités
            "metrics_by_symbol": {},                    # Copie de stats_by_symbol
            # P0.3: Anti-mitraillage par minute
            "trades_opened_by_minute": {},              # {minute_key: count}
            "trades_opened_by_minute_by_symbol": {},    # {minute_key: {symbol: count}}
            "blocked_by_per_minute_cap": 0,              # Nombre de setups bloqués par cap par minute
        }
        
        logger.info(f"BacktestEngine initialized - Mode: {config.trading_mode}, Types: {config.trade_types}")
        
        # P0 ÉTAPE 2: Vérifier que les playbooks sont bien enregistrés (CORE + A+)
        if hasattr(self.setup_engine, 'playbook_loader'):
            loader = self.setup_engine.playbook_loader
            core = getattr(loader, "playbooks", []) or []
            aplus = getattr(loader, "aplus_playbooks", []) or []
            all_playbooks = list(core) + list(aplus)
            playbook_names = [pb.name for pb in all_playbooks]
            self.debug_counts["playbooks_registered_count"] = len(all_playbooks)
            self.debug_counts["playbooks_registered_names"] = playbook_names[:30]  # Max 30
            logger.warning(f"[DEBUG] Registered playbooks (CORE+A+): {playbook_names}")
            logger.warning(f"[DEBUG] Total playbooks count (CORE+A+): {len(all_playbooks)}")

            # Option B: informer le RiskEngine du nombre de playbooks actifs
            try:
                if hasattr(self.risk_engine, "set_active_playbooks_count"):
                    self.risk_engine.set_active_playbooks_count(len(all_playbooks))
                    # Snapshot des caps (SAFE / AGGRESSIVE) pour debug_counts.json
                    caps_snapshot = self.risk_engine.get_caps_snapshot()
                    self.debug_counts["caps_snapshot"] = caps_snapshot
            except Exception:
                logger.exception("Failed to set active_playbooks_count on RiskEngine (ignored).")
        else:
            logger.error("[DEBUG] ⚠️  Cannot access playbooks! setup_engine structure:")
            logger.error(f"  hasattr setup_engine: {hasattr(self, 'setup_engine')}")
            if hasattr(self, 'setup_engine'):
                logger.error(f"  hasattr playbook_loader: {hasattr(self.setup_engine, 'playbook_loader')}")
                if hasattr(self.setup_engine, 'playbook_loader'):
                    logger.error(f"  playbook_loader type: {type(self.setup_engine.playbook_loader)}")
                    logger.error(f"  playbook_loader attrs: {dir(self.setup_engine.playbook_loader)}")
        if config.export_market_state:
            logger.info(f"  Market state export: ENABLED (stride={config.market_state_export_stride})")
    
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
                
                # P0 BUGFIX: Normalize datetime to avoid index/column ambiguity
                # Step 1: If index is DatetimeIndex, move it to column safely
                if isinstance(df.index, pd.DatetimeIndex):
                    df = df.copy()
                    # Temporarily name the index so reset_index creates a column with that name
                    index_name = df.index.name if df.index.name else "datetime"
                    df.index.name = index_name
                    df = df.reset_index()
                    logger.debug(f"  Moved DatetimeIndex to column: {index_name}")
                
                # Step 2: Handle __index_level_0__ if present (parquet multi-index fallback)
                if '__index_level_0__' in df.columns and 'datetime' not in df.columns:
                    df['datetime'] = pd.to_datetime(df['__index_level_0__'], utc=True, errors='coerce')
                    df = df.drop(columns=['__index_level_0__'])
                
                # Step 3: Ensure exactly ONE "datetime" column exists
                datetime_cols = [col for col in df.columns if col == 'datetime']
                if len(datetime_cols) > 1:
                    # Keep the first one, drop duplicates
                    df = df.loc[:, ~df.columns.duplicated(keep='first')]
                    logger.warning(f"  Removed duplicate 'datetime' columns, keeping first")
                elif len(datetime_cols) == 0:
                    # No datetime column at all - this is an error
                    raise ValueError(f"No 'datetime' column or DatetimeIndex found in {path.name}")
                
                # Step 4: Ensure datetime column is tz-aware UTC
                df['datetime'] = pd.to_datetime(df['datetime'], utc=True, errors='coerce')
                if df['datetime'].dt.tz is None:
                    df['datetime'] = df['datetime'].dt.tz_localize('UTC')
                else:
                    df['datetime'] = df['datetime'].dt.tz_convert('UTC')
                
                # Step 5: Ensure index is clean (RangeIndex, no name)
                df = df.reset_index(drop=True)
                
                # GUARD: Assert single source of truth
                assert "datetime" in df.columns, f"'datetime' column missing after normalization"
                assert not (isinstance(df.index, pd.DatetimeIndex) and df.index.name == "datetime"), \
                    f"Index still has 'datetime' name, causing ambiguity"
                assert df.columns.tolist().count("datetime") == 1, \
                    f"Multiple 'datetime' columns found: {df.columns.tolist()}"
                
                # Inférer le symbol depuis le filename
                filename = path.stem
                if '_' in filename:
                    symbol = filename.split('_')[0].upper()
                else:
                    symbol = filename.upper()
                
                if symbol not in self.config.symbols:
                    logger.warning(f"Symbol {symbol} not in config.symbols, skipping")
                    continue
                
                # Ajouter colonne symbol si absente (single-symbol parquet)
                if 'symbol' not in df.columns:
                    df['symbol'] = symbol
                
                all_dfs.append(df)
                logger.info(f"  Loaded {path.name}: {len(df)} bars, symbol={symbol}")
            
            except Exception as e:
                logger.error(f"Error loading {path}: {e}")
                continue
        
        if not all_dfs:
            raise ValueError("No data loaded!")
        
        # Combiner et trier
        self.combined_data = pd.concat(all_dfs, ignore_index=True)
        
        # GUARD: Assert single source of truth before slicing
        assert "datetime" in self.combined_data.columns, "'datetime' column missing after concat"
        assert not (isinstance(self.combined_data.index, pd.DatetimeIndex) and self.combined_data.index.name == "datetime"), \
            "Index still has 'datetime' name after concat, causing ambiguity"
        assert self.combined_data.columns.tolist().count("datetime") == 1, \
            f"Multiple 'datetime' columns after concat: {self.combined_data.columns.tolist()}"
        
        # DIAGNOSTIC: Ensure datetime column is tz-aware UTC before slicing
        if self.combined_data['datetime'].dt.tz is None:
            self.combined_data['datetime'] = self.combined_data['datetime'].dt.tz_localize('UTC')
        else:
            self.combined_data['datetime'] = self.combined_data['datetime'].dt.tz_convert('UTC')
        
        # Sort by datetime (using column, never index)
        self.combined_data = self.combined_data.sort_values('datetime').reset_index(drop=True)
        
        # P2-1.B: Date slicing si spécifié dans config
        if self.config.start_date or self.config.end_date:
            before_slice = len(self.combined_data)
            
            # DIAGNOSTIC: Log before slice
            logger.info(f"📅 Before slice: {before_slice} bars")
            if len(self.combined_data) > 0:
                logger.info(f"   Datetime range: {self.combined_data['datetime'].min()} to {self.combined_data['datetime'].max()}")
                logger.info(f"   Datetime tz: {self.combined_data['datetime'].dt.tz}")
            
            # Build slicing bounds as tz-aware UTC
            if self.config.start_date:
                # Ensure start_dt is tz-aware UTC
                start_dt_raw = pd.to_datetime(self.config.start_date)
                if start_dt_raw.tz is None:
                    start_dt = start_dt_raw.tz_localize('UTC')
                else:
                    start_dt = start_dt_raw.tz_convert('UTC')
                
                logger.info(f"   Slicing start: {start_dt} (tz-aware: {start_dt.tz is not None})")
                self.combined_data = self.combined_data[self.combined_data['datetime'] >= start_dt]
            
            if self.config.end_date:
                # End date is inclusive (entire day) - use end-exclusive slice
                end_dt_raw = pd.to_datetime(self.config.end_date)
                if end_dt_raw.tz is None:
                    end_dt = end_dt_raw.tz_localize('UTC')
                else:
                    end_dt = end_dt_raw.tz_convert('UTC')
                
                # End-exclusive: add 1 day and use < (not <=)
                end_excl = end_dt + pd.Timedelta(days=1)
                
                logger.info(f"   Slicing end (exclusive): {end_excl} (tz-aware: {end_excl.tz is not None})")
                self.combined_data = self.combined_data[self.combined_data['datetime'] < end_excl]
            
            after_slice = len(self.combined_data)
            logger.info(f"📅 Date slicing: {before_slice} → {after_slice} bars ({self.config.start_date} to {self.config.end_date})")
            
            # DIAGNOSTIC: Log after slice
            if after_slice > 0:
                # Ensure sorted after slice
                self.combined_data = self.combined_data.sort_values('datetime').reset_index(drop=True)
                logger.info(f"   After slice range: {self.combined_data['datetime'].min()} to {self.combined_data['datetime'].max()}")
                logger.info(f"   After slice shape: {self.combined_data.shape}")
            else:
                logger.warning(f"   ⚠️  EMPTY SLICE! Check timezone alignment.")
                logger.warning(f"   Config: start_date={self.config.start_date}, end_date={self.config.end_date}")
                if len(self.combined_data) > 0:
                    logger.warning(f"   Data range: {self.combined_data['datetime'].min()} to {self.combined_data['datetime'].max()}")
        
        # P2-2.B: HTF Warmup - Load extended HTF data for context
        # This provides historical HTF candles BEFORE start_date for day_type calculation
        # while keeping intraday (1m) strictly within start_date/end_date
        if self.config.start_date and self.config.htf_warmup_days > 0:
            # Build warmup bounds as tz-aware UTC
            start_dt_raw = pd.to_datetime(self.config.start_date)
            if start_dt_raw.tz is None:
                start_dt_utc = start_dt_raw.tz_localize('UTC')
            else:
                start_dt_utc = start_dt_raw.tz_convert('UTC')
            
            warmup_start_dt = start_dt_utc - pd.Timedelta(days=self.config.htf_warmup_days)
            
            logger.info(f"🔧 HTF Warmup: Loading {self.config.htf_warmup_days} days before {self.config.start_date}")
            logger.info(f"   Warmup period: {warmup_start_dt.strftime('%Y-%m-%d')} → {self.config.start_date}")
            
            # Load warmup data for HTF only (not for 1m iteration)
            self.htf_warmup_data = {}
            for i, path in enumerate(self.config.data_paths):
                symbol = self.config.symbols[i]
                path_obj = Path(path)
                df_warmup = pd.read_parquet(path_obj)
                
                # P0 BUGFIX: Normalize datetime for warmup (same as main load)
                if isinstance(df_warmup.index, pd.DatetimeIndex):
                    df_warmup = df_warmup.copy()
                    index_name = df_warmup.index.name if df_warmup.index.name else "datetime"
                    df_warmup.index.name = index_name
                    df_warmup = df_warmup.reset_index()
                
                if '__index_level_0__' in df_warmup.columns and 'datetime' not in df_warmup.columns:
                    df_warmup['datetime'] = pd.to_datetime(df_warmup['__index_level_0__'], utc=True, errors='coerce')
                    df_warmup = df_warmup.drop(columns=['__index_level_0__'])
                
                # Ensure exactly ONE "datetime" column
                datetime_cols = [col for col in df_warmup.columns if col == 'datetime']
                if len(datetime_cols) > 1:
                    df_warmup = df_warmup.loc[:, ~df_warmup.columns.duplicated(keep='first')]
                elif len(datetime_cols) == 0:
                    raise ValueError(f"No 'datetime' column found in warmup data for {symbol}")
                
                df_warmup['datetime'] = pd.to_datetime(df_warmup['datetime'], utc=True, errors='coerce')
                
                # DIAGNOSTIC: Ensure datetime is tz-aware UTC
                if df_warmup['datetime'].dt.tz is None:
                    df_warmup['datetime'] = df_warmup['datetime'].dt.tz_localize('UTC')
                else:
                    df_warmup['datetime'] = df_warmup['datetime'].dt.tz_convert('UTC')
                
                # Clean index
                df_warmup = df_warmup.reset_index(drop=True)
                
                # Filter warmup: [warmup_start, start_date) - both tz-aware UTC
                df_warmup = df_warmup[
                    (df_warmup['datetime'] >= warmup_start_dt) &
                    (df_warmup['datetime'] < start_dt_utc)
                ]
                
                # Sort by datetime (using column, never index)
                df_warmup = df_warmup.sort_values('datetime').reset_index(drop=True)
                
                self.htf_warmup_data[symbol] = df_warmup
                logger.info(f"   {symbol}: {len(df_warmup)} warmup bars loaded")
        else:
            self.htf_warmup_data = {}
        
        # Filtrer par période si spécifié dans run_name (ex: rolling_2025-06)
        if 'rolling_' in self.config.run_name and '-' in self.config.run_name:
            try:
                month_str = self.config.run_name.split('rolling_')[-1]  # 2025-06
                year, month = month_str.split('-')
                start_date = pd.Timestamp(f'{year}-{month}-01', tz='UTC')
                # Fin de mois
                if int(month) == 12:
                    end_date = pd.Timestamp(f'{int(year)+1}-01-01', tz='UTC')
                else:
                    end_date = pd.Timestamp(f'{year}-{int(month)+1:02d}-01', tz='UTC')
                
                before_filter = len(self.combined_data)
                self.combined_data = self.combined_data[
                    (self.combined_data['datetime'] >= start_date) &
                    (self.combined_data['datetime'] < end_date)
                ]
                logger.info(f"📅 Filtered to {month_str}: {len(self.combined_data)} bars (was {before_filter})")
            except:
                pass  # Pas un run rolling, on garde tout
        
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
                
                # DIAGNOSTIC: Compter candles 1m chargés
                self.debug_counts["candles_loaded_1m"] += len(symbol_data)
                
                logger.info(f"  {symbol}: {len(symbol_data)} bars, {len(candles_dict)} candles indexed")
        
        logger.info(f"✅ Data loaded: {len(self.combined_data)} total bars")
        logger.info(f"✅ Total 1m candles loaded: {self.debug_counts['candles_loaded_1m']}")
        
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

        # Load data (only if not already loaded)
        if self.combined_data is None:
            self.load_data()

        # P0.2: Logs clairs par symbol
        logger.info("\n📊 Data loaded per symbol:")
        for symbol in self.config.symbols:
            symbol_data = self.combined_data[self.combined_data['symbol'] == symbol]
            if len(symbol_data) > 0:
                symbol_start = symbol_data['datetime'].min()
                symbol_end = symbol_data['datetime'].max()
                logger.info(
                    "  Running symbol=%s, bars=%d, range=%s -> %s",
                    symbol,
                    len(symbol_data),
                    symbol_start,
                    symbol_end
                )
            else:
                logger.warning(f"  ⚠️  No data for symbol={symbol}")

        start_date = self.combined_data["datetime"].min()
        end_date = self.combined_data["datetime"].max()

        # OPTIMISATION: Plus de pre-build multi-TF, on utilise l'agrégateur incrémental
        # self._build_multi_timeframe_candles()
        
        # P2-2.B: CHECKPOINT - Capture état AVANT prefeed gate
        prefeed_gate_state = {
            "hasattr_htf_warmup_data": hasattr(self, 'htf_warmup_data'),
            "htf_warmup_data_is_none": getattr(self, 'htf_warmup_data', None) is None,
            "id_htf_warmup_data": id(self.htf_warmup_data) if hasattr(self, 'htf_warmup_data') else None,
            "type_htf_warmup_data": str(type(self.htf_warmup_data)) if hasattr(self, 'htf_warmup_data') else None,
            "len_htf_warmup_data": len(self.htf_warmup_data) if hasattr(self, 'htf_warmup_data') and isinstance(self.htf_warmup_data, dict) else -1,
            "bool_htf_warmup_data": bool(self.htf_warmup_data) if hasattr(self, 'htf_warmup_data') else None,
            "keys_htf_warmup_data": list(self.htf_warmup_data.keys())[:5] if hasattr(self, 'htf_warmup_data') and isinstance(self.htf_warmup_data, dict) else [],
            "combined_data_is_none": self.combined_data is None,
            "config_start_date": self.config.start_date,
            "config_end_date": self.config.end_date,
            "config_htf_warmup_days": self.config.htf_warmup_days,
        }
        
        # Add symbol-specific counts if dict exists
        if hasattr(self, 'htf_warmup_data') and isinstance(self.htf_warmup_data, dict):
            for symbol in self.config.symbols[:2]:  # Max 2 symbols
                if symbol in self.htf_warmup_data:
                    val = self.htf_warmup_data[symbol]
                    prefeed_gate_state[f"{symbol}_type"] = str(type(val))
                    prefeed_gate_state[f"{symbol}_len"] = len(val) if hasattr(val, '__len__') else -1
        
        # Export checkpoint for debug
        if not hasattr(self, '_debug_checkpoints'):
            self._debug_checkpoints = []
        self._debug_checkpoints.append(("prefeed_gate", prefeed_gate_state))
        
        logger.info(f"🔍 Prefeed gate: hasattr={prefeed_gate_state['hasattr_htf_warmup_data']}, "
                   f"len={prefeed_gate_state['len_htf_warmup_data']}, "
                   f"bool={prefeed_gate_state['bool_htf_warmup_data']}")
        
        # P2-2.B: Pre-feed TimeframeAggregator with warmup data
        if hasattr(self, 'htf_warmup_data') and self.htf_warmup_data:
            logger.info("🔧 Pre-feeding HTF warmup data to TimeframeAggregator...")
            warmup_bars_fed = 0
            for symbol, df_warmup in self.htf_warmup_data.items():
                # Convert warmup bars to Candle objects and feed to aggregator
                for _, row in df_warmup.iterrows():
                    candle_1m = Candle(
                        timestamp=row['datetime'],
                        open=row['open'],
                        high=row['high'],
                        low=row['low'],
                        close=row['close'],
                        volume=row['volume'],
                        symbol=symbol,
                        timeframe='1m'
                    )
                    self.tf_aggregator.add_1m_candle(candle_1m)
                    warmup_bars_fed += 1
            
            # Log HTF candles after warmup
            for symbol in self.config.symbols:
                candles_1d = self.tf_aggregator.get_candles(symbol, "1d")
                candles_4h = self.tf_aggregator.get_candles(symbol, "4h")
                candles_1h = self.tf_aggregator.get_candles(symbol, "1h")
                logger.info(f"   {symbol}: {len(candles_1d)} daily, {len(candles_4h)} 4h, {len(candles_1h)} 1h candles after warmup (fed {warmup_bars_fed} 1m bars)")
                
                # DIAGNOSTIC: Compter candles HTF chargés
                if "candles_loaded_htf" not in self.debug_counts:
                    self.debug_counts["candles_loaded_htf"] = {}
                self.debug_counts["candles_loaded_htf"][f"{symbol}_1d"] = len(candles_1d)
                self.debug_counts["candles_loaded_htf"][f"{symbol}_4h"] = len(candles_4h)
                self.debug_counts["candles_loaded_htf"][f"{symbol}_1h"] = len(candles_1h)
        
        # Group by minute (pour traiter SPY et QQQ ensemble)
        self.combined_data["minute"] = self.combined_data["datetime"].dt.floor("1min")
        minutes = sorted(self.combined_data["datetime"].unique())  # Toutes les bougies 1m

        logger.info("\n📊 Processing %d bars (1m driver)...", len(minutes))

        # P0.3: Déterminer les caps selon le mode
        if self.config.trading_mode == "SAFE":
            max_global_per_minute = 1
            max_per_symbol_per_minute = 1
        else:  # AGGRESSIVE
            max_global_per_minute = 2
            max_per_symbol_per_minute = 1
        
        # P0.3: Variables de tracking anti-mitraillage par minute
        current_minute_key = None
        opened_symbols_this_minute = set()
        opened_count_this_minute = 0

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
                
                # P0 DEBUG - Étape 1: Vérifier que la boucle de traitement des bougies tourne
                self.debug_counts["bars_processed"] = self.debug_counts.get("bars_processed", 0) + 1
                if self.debug_counts["bars_processed"] <= 5:
                    logger.warning(
                        f"[DEBUG] BAR {self.debug_counts['bars_processed']} "
                        f"dt={candle_1m.timestamp} "
                        f"O={candle_1m.open} H={candle_1m.high} L={candle_1m.low} C={candle_1m.close}"
                    )
                
                # P0 DEBUG - Étape 3: Forcer un setup artificiel (preuve absolue)
                if self.debug_counts["bars_processed"] == 100:
                    self.debug_counts["setups_detected_total"] += 1
                    logger.error("🔥 DEBUG: FAKE SETUP TRIGGERED AT BAR 100")
                
                # P1: Mettre à jour le tracking inter-session (logging only)
                try:
                    self._update_inter_session_state(symbol, current_time, candle_1m.close)
                except Exception:
                    pass  # Ne pas faire crasher le backtest sur l'instrumentation
                
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

            # P0.3: Réinitialiser les compteurs par minute si nouvelle minute
            minute_key = pd.Timestamp(current_time).floor("1min")
            if minute_key != current_minute_key:
                current_minute_key = minute_key
                opened_symbols_this_minute = set()
                opened_count_this_minute = 0
            
            # 3) P0.2: Exécuter TOUS les setups candidats (multi-symbol réel)
            # Trier par priorité et exécuter dans l'ordre (DAILY en premier, puis SCALP)
            if candidate_setups:
                def setup_priority(s: Setup) -> tuple:
                    quality_rank = {"A+": 3, "A": 2, "B": 1, "C": 0}
                    return (
                        quality_rank.get(s.quality, 0),
                        s.final_score,
                        s.confluences_count,
                        s.risk_reward,
                    )

                # Séparer DAILY et SCALP, trier chaque groupe par priorité
                daily_setups = [s for s in candidate_setups if s.trade_type == "DAILY"]
                scalp_setups = [s for s in candidate_setups if s.trade_type == "SCALP"]
                
                # Trier chaque groupe par priorité (meilleur en premier)
                daily_setups_sorted = sorted(daily_setups, key=setup_priority, reverse=True)
                scalp_setups_sorted = sorted(scalp_setups, key=setup_priority, reverse=True)
                
                # Exécuter dans l'ordre : DAILY d'abord, puis SCALP
                # Chaque _execute_setup vérifie ses propres limites (can_take_setup, cooldown, etc.)
                all_setups_to_try = daily_setups_sorted + scalp_setups_sorted
                
                for setup in all_setups_to_try:
                    # P0.3: Vérifier cap par symbole (1 trade max par symbole par minute)
                    if setup.symbol in opened_symbols_this_minute:
                        self.debug_counts["blocked_by_per_minute_cap"] += 1
                        continue  # Skip ce setup, symbole déjà traité cette minute
                    
                    # P0.3: Vérifier cap global (N trades max par minute)
                    if opened_count_this_minute >= max_global_per_minute:
                        self.debug_counts["blocked_by_per_minute_cap"] += 1
                        break  # Arrêter pour cette minute, cap global atteint
                    
                    # Vérifier limites globales (circuit breakers) avant chaque exécution
                    limits_check = self.risk_engine.check_daily_limits()
                    if limits_check["trading_allowed"]:
                        # _execute_setup vérifie les limites individuelles (cooldown, session, etc.)
                        # Retourne True si un trade a été ouvert
                        trade_opened = self._execute_setup(setup, current_time)
                        
                        # P0.3: Mettre à jour les compteurs par minute si trade ouvert
                        if trade_opened:
                            opened_symbols_this_minute.add(setup.symbol)
                            opened_count_this_minute += 1
                            
                            # Instrumentation: compter trades par minute
                            minute_key_str = minute_key.isoformat()
                            if minute_key_str not in self.debug_counts["trades_opened_by_minute"]:
                                self.debug_counts["trades_opened_by_minute"][minute_key_str] = 0
                            self.debug_counts["trades_opened_by_minute"][minute_key_str] += 1
                            
                            # Instrumentation: compter trades par minute par symbole
                            if minute_key_str not in self.debug_counts["trades_opened_by_minute_by_symbol"]:
                                self.debug_counts["trades_opened_by_minute_by_symbol"][minute_key_str] = {}
                            symbol_dict = self.debug_counts["trades_opened_by_minute_by_symbol"][minute_key_str]
                            symbol_dict[setup.symbol] = symbol_dict.get(setup.symbol, 0) + 1
                    else:
                        # Si trading bloqué globalement, arrêter pour cette minute
                        break

            # 3) Mettre à jour les positions ouvertes
            self._update_positions(current_time)

            # 4) Suivre la courbe d'equity
            self._track_equity(current_time)

        # Fermer toutes les positions restantes
        self._close_all_remaining_positions(end_date)

        # Générer résultats
        result = self._generate_result(start_date, end_date, len(minutes))

        # DIAGNOSTIC: Exporter debug_counts.json
        self._export_debug_counts()

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
                "4h": candles_4h[-30:],  # P2-2.B: Increased
                "1d": candles_1d[-30:]   # P2-2.B: Increased to support detect_structure (>= 20)
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
                    "4h": candles_4h[-30:],  # P2-2.B
                    "1d": candles_1d[-30:]   # P2-2.B
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
            
            # ICT patterns via unified custom detectors (BOS/FVG + IFVG/OB/EQ/BB)
            if len(candles_5m) > 10:
                detections_5m = detect_custom_patterns(candles_5m[-100:], "5m")
                for plist in detections_5m.values():
                    if plist:
                        ict_patterns.extend(plist)
            
            if len(candles_15m) > 10 and htf_events.get("is_close_15m"):
                detections_15m = detect_custom_patterns(candles_15m[-100:], "15m")
                for plist in detections_15m.values():
                    if plist:
                        ict_patterns.extend(plist)
        
        # P0 ÉTAPE 2: Instrumentation - Log évaluation playbooks (rate limit)
        bar_num = self.debug_counts.get("bars_processed", 0)
        if bar_num == 1 or (bar_num > 0 and bar_num % 200 == 0):
            playbook_count = self.debug_counts.get("playbooks_registered_count", 0)
            logger.warning(
                f"[DEBUG] BAR {bar_num} - Evaluating playbooks | "
                f"dt={current_time} | "
                f"playbooks={playbook_count} | "
                f"mode={self.config.trading_mode} | "
                f"trade_types={self.config.trade_types} | "
                f"ict_patterns={len(ict_patterns)} | "
                f"candle_patterns={len(candle_patterns)}"
            )
        
        # P0 ÉTAPE 3: Compter évaluation playbooks
        # On compte chaque appel à generate_setups comme une évaluation
        self.debug_counts["playbooks_evaluated_total"] = self.debug_counts.get("playbooks_evaluated_total", 0) + 1
        
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
        
        # P0 FIX: Compter matches (après génération, matches stockés dans _last_matches)
        if hasattr(self.setup_engine, '_last_matches') and self.setup_engine._last_matches:
            matches = self.setup_engine._last_matches
            self.debug_counts["matches_total"] += len(matches)
            for match in matches:
                pb_name = match.get('playbook_name', 'unknown')
                if pb_name not in self.debug_counts["matches_by_playbook"]:
                    self.debug_counts["matches_by_playbook"][pb_name] = 0
                self.debug_counts["matches_by_playbook"][pb_name] += 1
        
        # P0 FIX: Compter setups créés
        if setups:
            self.debug_counts["setups_created_total"] += len(setups)
            for setup in setups:
                # P0 FIX: Utiliser setup.playbook_name (source de vérité unique)
                playbook_name = setup.playbook_name if setup.playbook_name else "unknown"
                
                logger.error(
                    f"[DEBUG] SETUP MATCHED | "
                    f"bar={bar_num} | "
                    f"playbook={playbook_name} | "
                    f"type={getattr(setup, 'trade_type', 'N/A')} | "
                    f"direction={getattr(setup, 'direction', 'N/A')} | "
                    f"quality={getattr(setup, 'quality', 'N/A')}"
                )
                # P0 FIX: Compter setups créés par playbook
                if playbook_name not in self.debug_counts["setups_created_by_playbook"]:
                    self.debug_counts["setups_created_by_playbook"][playbook_name] = 0
                self.debug_counts["setups_created_by_playbook"][playbook_name] += 1
                
                # Legacy (compatibilité)
                if playbook_name not in self.debug_counts["setups_detected_by_playbook"]:
                    self.debug_counts["setups_detected_by_playbook"][playbook_name] = 0
                self.debug_counts["setups_detected_by_playbook"][playbook_name] += 1
        
        # Collecter tous les setups générés (pour funnel)
        if setups:
            self.all_generated_setups.extend(setups)
            
            # P2-2.B: Collect market_state data (if export enabled)
            if self.market_state_records is not None:
                for setup in setups:
                    self.market_state_records.append({
                        'timestamp': setup.timestamp.isoformat(),
                        'symbol': setup.symbol,
                        'market_bias': setup.market_bias,
                        'session': setup.session,
                        'day_type': getattr(setup, 'day_type', 'unknown'),
                        'daily_structure': getattr(setup, 'daily_structure', 'unknown'),
                    })
        
        if not setups:
            return None
        
        # Filtrer selon le mode (SAFE/AGGRESSIVE)
        filtered_setups = filter_setups_by_mode(setups, self.risk_engine)
        
        # P0 PLUMBING: Diagnostic entrée/sortie RiskEngine sur ce bar
        # Entrée
        self.debug_counts["risk_input_setups_len"] = len(setups)
        self.debug_counts["risk_first3_input_playbooks"] = [
            (s.playbook_name or "unknown") for s in setups[:3]
        ]

        # Appel RiskEngine (autorité finale sur les playbooks)
        filtered_setups = filter_setups_by_mode(setups, self.risk_engine)

        # Sortie
        self.debug_counts["risk_output_setups_len"] = len(filtered_setups)
        self.debug_counts["risk_first3_output_playbooks"] = [
            (s.playbook_name or "unknown") for s in filtered_setups[:3]
        ]

        # P0 FIX: Compter setups après RiskEngine
        self.debug_counts["setups_after_risk_filter_total"] += len(filtered_setups)
        for setup in filtered_setups:
            playbook_name = setup.playbook_name if setup.playbook_name else "unknown"
            if playbook_name not in self.debug_counts["setups_after_risk_filter_by_playbook"]:
                self.debug_counts["setups_after_risk_filter_by_playbook"][playbook_name] = 0
            self.debug_counts["setups_after_risk_filter_by_playbook"][playbook_name] += 1
        
        # P0 TÂCHE 3: Récupérer rejets détaillés depuis RiskEngine et propager vers debug_counts
        rejects = self.risk_engine.get_last_filter_rejects()
        
        # Stocker rejets par playbook
        for playbook_name, count in rejects.get('by_playbook', {}).items():
            if playbook_name not in self.debug_counts["setups_rejected_by_mode_by_playbook"]:
                self.debug_counts["setups_rejected_by_mode_by_playbook"][playbook_name] = 0
            self.debug_counts["setups_rejected_by_mode_by_playbook"][playbook_name] += count
        
        # Stocker exemples détaillés (max 5)
        existing_count = len(self.debug_counts["setups_rejected_by_mode_examples"])
        for example in rejects.get('examples', [])[:5 - existing_count]:
            self.debug_counts["setups_rejected_by_mode_examples"].append(example)
        
        # P0 TÂCHE 3: Stocker mode réel + allowlist snapshot (une seule fois, au premier appel)
        if "risk_mode_used" not in self.debug_counts or not self.debug_counts["risk_mode_used"]:
            self.debug_counts["risk_mode_used"] = self.risk_engine.state.trading_mode
            from engines.risk_engine import AGGRESSIVE_ALLOWLIST, SAFE_ALLOWLIST
            aggressive_len = len(AGGRESSIVE_ALLOWLIST)
            safe_len = len(SAFE_ALLOWLIST)
            aggressive_first5 = list(AGGRESSIVE_ALLOWLIST[:5])
            safe_first5 = list(SAFE_ALLOWLIST[:5])
            self.debug_counts["risk_allowlist_snapshot"] = {
                "aggressive": {
                    "len": aggressive_len,
                    "first5": aggressive_first5
                },
                "safe": {
                    "len": safe_len,
                    "first5": safe_first5
                }
            }

        # Stocker aussi les rejets détaillés avec clés claires (toujours à jour)
        self.debug_counts["risk_rejects_by_playbook"] = rejects.get('by_playbook', {}).copy()
        self.debug_counts["risk_reject_examples"] = rejects.get('examples', []).copy()
        
        # Compter missing_playbook_name
        self.debug_counts["missing_playbook_name"] += rejects.get('missing_playbook_name', 0)
        
        if not filtered_setups:
            # P0 ÉTAPE 3: Compter rejet par mode
            self.debug_counts["setups_rejected_by_mode"] = self.debug_counts.get("setups_rejected_by_mode", 0) + len(setups)
            if "rejected_by_mode" not in self.debug_counts["setups_rejected_by_reason"]:
                self.debug_counts["setups_rejected_by_reason"]["rejected_by_mode"] = 0
            self.debug_counts["setups_rejected_by_reason"]["rejected_by_mode"] += len(setups)
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

        # ICT patterns via unified custom detectors on higher timeframes (5m/15m)
        ict_patterns: List[ICTPattern] = []
        if candles_5m:
            # Limit to the last 100 candles for detection
            recent_5m = candles_5m[-100:] if len(candles_5m) > 100 else candles_5m
            detections_5m = detect_custom_patterns(recent_5m, "5m")
            for plist in detections_5m.values():
                if plist:
                    ict_patterns.extend(plist)
        if candles_15m:
            recent_15m = candles_15m[-100:] if len(candles_15m) > 100 else candles_15m
            detections_15m = detect_custom_patterns(recent_15m, "15m")
            for plist in detections_15m.values():
                if plist:
                    ict_patterns.extend(plist)

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
            choch_patterns = detect_choch_pattern(recent_5m_for_choch, sweeps[-1])
            if choch_patterns:
                ict_patterns.extend(choch_patterns)

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
        
        # DIAGNOSTIC: Compter setups détectés
        if setups:
            self.debug_counts["setups_detected_total"] += len(setups)
        
        # Instrumentation: compter les setups bruts
        self._record_setups_stats(symbol, current_time, setups, stage="raw")

        if not setups:
            return None
        
        # Filtrer selon mode (RiskEngine est l'autorité finale pour playbooks)
        setups_before_mode = len(setups)
        setups = filter_setups_by_mode(setups, risk_engine=self.risk_engine)
        setups_after_mode = len(setups)
        
        # DIAGNOSTIC: Compter rejets par mode
        if setups_before_mode > setups_after_mode:
            self.debug_counts["setups_rejected_by_mode"] += (setups_before_mode - setups_after_mode)

        # Filtrer selon trade_types demandés
        setups_before_types = len(setups)
        setups = [s for s in setups if s.trade_type in self.config.trade_types]
        setups_after_types = len(setups)
        
        # DIAGNOSTIC: Compter rejets par trade_types
        if setups_before_types > setups_after_types:
            self.debug_counts["setups_rejected_by_trade_types"] += (setups_before_types - setups_after_types)

        # Instrumentation: compter les setups après mode + trade_types
        if setups:
            self._record_setups_stats(symbol, current_time, setups, stage="after_mode")
            self.debug_counts["setups_accepted_total"] += len(setups)
        else:
            self.debug_counts["setups_rejected_total"] += setups_before_mode

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
    
    def _execute_setup(self, setup: Setup, current_time: datetime) -> bool:
        """
        Exécute un setup (via RiskEngine + ExecutionEngine) avec 2R/1R money management.
        
        Returns:
            bool: True si un trade a été ouvert avec succès, False sinon.
        """
        
        # P0 FIX: Compter tentative d'ouverture
        self.debug_counts["trades_open_attempted_total"] += 1

        # OPTION B: Compter tentatives par playbook
        playbook_name = setup.playbook_name if setup.playbook_name else "UNKNOWN"
        attempts_dict = self.debug_counts.get("trades_attempted_by_playbook")
        if not isinstance(attempts_dict, dict):
            attempts_dict = {}
            self.debug_counts["trades_attempted_by_playbook"] = attempts_dict
        attempts_dict[playbook_name] = attempts_dict.get(playbook_name, 0) + 1

        # OPTION B: grade_counts_by_playbook (A+/A/B/C/UNKNOWN) – pure instrumentation
        quality_raw = getattr(setup, "quality", "") or ""
        quality_norm = quality_raw.strip().upper()
        if quality_norm in ("APLUS", "A_PLUS"):
            grade = "A+"
        elif quality_norm in ("A+", "A", "B", "C"):
            grade = quality_norm
        else:
            grade = "UNKNOWN"

        grade_counts = self.debug_counts.get("grade_counts_by_playbook")
        if not isinstance(grade_counts, dict):
            grade_counts = {}
            self.debug_counts["grade_counts_by_playbook"] = grade_counts
        if playbook_name not in grade_counts:
            grade_counts[playbook_name] = {"A+": 0, "A": 0, "B": 0, "C": 0, "UNKNOWN": 0}
        grade_counts[playbook_name][grade] += 1
        
        # P0.6.1: Vérifier si stop_run a été déclenché
        if self._stop_run_triggered:
            reason = f"STOP_RUN actif depuis {self._stop_run_time}"
            logger.debug(f"⚠️ Setup refusé: {reason}")
            self._increment_reject_reason("stop_run_triggered")
            return False
        
        # Vérifier si le setup peut être pris (circuit breakers, quotas, etc.)
        can_take = self.risk_engine.can_take_setup(setup)
        if not can_take['allowed']:
            reason = can_take.get('reason', 'unknown')
            logger.debug(f"⚠️ Setup refusé par RiskEngine: {reason}")
            self._increment_reject_reason(reason)
            return False
        
        # PATCH A: Vérifier cooldown et limite par session (ANTI-SPAM)
        # Obtenir session actuelle et construire la clé hybride session+bucket4h (en NY time)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        # Bucket 4h basé sur l'heure America/New_York (market-aligned)
        try:
            from zoneinfo import ZoneInfo  # Python 3.9+
            ny_time = current_time.astimezone(ZoneInfo("America/New_York"))
        except Exception:
            # Fallback: si ZoneInfo indisponible, on reste en UTC
            ny_time = current_time

        # P0.1 FIX: Appeler get_session_info avec ny_time pour obtenir le bon session_label
        session_info = get_session_info(ny_time, debug_log=False)
        session_label = session_info.get('session', 'Unknown')

        h = ny_time.hour
        bucket_start = (h // 4) * 4
        bucket_end = min(bucket_start + 4, 24)
        bucket_str = f"{bucket_start:02d}00-{bucket_end:02d}00NY"
        session_key = f"{ny_time.date()}|{session_label}|{bucket_str}"

        # Instrumentation: mémoriser la première clé de session utilisée
        if not self.debug_counts.get("session_key_used"):
            self.debug_counts["session_key_used"] = session_key
        
        cooldown_ok, cooldown_reason = self.risk_engine.check_cooldown_and_session_limit(
            setup, current_time, session_key
        )
        if not cooldown_ok:
            logger.debug(f"⚠️ Setup bloqué (anti-spam): {cooldown_reason}")
            # PATCH D: Tracker les rejets anti-spam
            playbook_name = setup.playbook_name if setup.playbook_name else "UNKNOWN"
            if "Cooldown" in cooldown_reason:
                self.blocked_by_cooldown += 1
                self.blocked_by_cooldown_details[playbook_name] = self.blocked_by_cooldown_details.get(playbook_name, 0) + 1
                self._increment_reject_reason("cooldown_active")
            elif "session" in cooldown_reason.lower():
                self.blocked_by_session_limit += 1
                self.blocked_by_session_limit_details[playbook_name] = self.blocked_by_session_limit_details.get(playbook_name, 0) + 1
                # OPTION B: exposer les limites de session par playbook dans debug_counts
                try:
                    sess_dict = self.debug_counts.get("session_limit_reached_by_playbook")
                    if not isinstance(sess_dict, dict):
                        sess_dict = {}
                        self.debug_counts["session_limit_reached_by_playbook"] = sess_dict
                    sess_dict[playbook_name] = sess_dict.get(playbook_name, 0) + 1
                except Exception:
                    pass
                self._increment_reject_reason("session_limit_reached")
            return False
        
        # Vérifier cap trades par symbole
        allowed, reason = self.risk_engine.check_trades_cap(setup.symbol, current_time.date())
        if not allowed:
            logger.debug(f"⚠️ Setup refusé: {reason}")
            self._increment_reject_reason(reason)
            return
        
        # Position sizing avec 2R/1R
        position_calc = self.risk_engine.calculate_position_size(setup)
        
        if not position_calc.valid:
            reason = position_calc.reason or "position_sizing_invalid"
            logger.info(f"⚠️ Setup non exécuté (position sizing invalide): {reason}")
            self._increment_reject_reason(reason)
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
            # DIAGNOSTIC: Compter trade ouvert
            self.debug_counts["trades_opened_total"] += 1
            # OPTION B: Compter trades ouverts par playbook
            try:
                pb_name = setup.playbook_name if setup.playbook_name else "UNKNOWN"
                opened_dict = self.debug_counts.get("trades_opened_by_playbook")
                if not isinstance(opened_dict, dict):
                    opened_dict = {}
                    self.debug_counts["trades_opened_by_playbook"] = opened_dict
                opened_dict[pb_name] = opened_dict.get(pb_name, 0) + 1
            except Exception:
                pass
            
            # P1: Capturer snapshot de contexte inter-session lors de l'ouverture du trade
            try:
                context_snapshot = self._get_inter_session_context_snapshot(
                    setup.symbol, current_time, session_label, session_key
                )
                snapshots = self.debug_counts.get("trade_context_snapshots", [])
                if not isinstance(snapshots, list):
                    snapshots = []
                    self.debug_counts["trade_context_snapshots"] = snapshots
                if len(snapshots) < 200:  # Limiter à 200 entrées
                    snapshots.append(context_snapshot)
            except Exception:
                pass  # Ne pas faire crasher le backtest sur l'instrumentation
            
            # Incrémenter le compteur de trades pour ce symbole
            self.risk_engine.increment_trades_count(setup.symbol, current_time.date())
            # PATCH A: Record pour anti-spam (cooldown + session limit) avec clé hybride
            self.risk_engine.record_trade_for_cooldown(setup, current_time, session_key)
            logger.debug(f"  ✅ Trade opened: {setup.symbol} {setup.direction} @ {setup.entry_price:.2f} (tier={position_calc.risk_tier}R)")
            return True
        else:
            # P0 FIX: Compter rejet par ExecutionEngine
            reason = order_result.get('reason', 'execution_engine_failed')
            self._increment_reject_reason(reason)
            return False

    # ========================================================================
    # P1: Inter-session state tracking (logging only)
    # ========================================================================
    
    def _update_inter_session_state(self, symbol: str, current_time: datetime, price: float):
        """
        Met à jour l'état inter-session pour un symbole (open/high/low/close/range).
        Détecte les changements de session et calcule les sweeps inter-sessions.
        """
        try:
            from zoneinfo import ZoneInfo
            ny_time = current_time.astimezone(ZoneInfo("America/New_York"))
        except Exception:
            ny_time = current_time

        session_info = get_session_info(ny_time, debug_log=False)
        session_label = session_info.get('session', 'Unknown')
        date_str = str(ny_time.date())

        # Initialiser la structure pour ce symbole si nécessaire
        if symbol not in self._session_states:
            self._session_states[symbol] = {}

        # Détecter changement de session
        session_key = f"{date_str}_{session_label}"
        if session_key not in self._session_states[symbol]:
            # Nouvelle session : initialiser open/high/low/close
            self._session_states[symbol][session_key] = {
                'open': price,
                'high': price,
                'low': price,
                'close': price,
                'range': 0.0,
                'date': date_str,
                'session_label': session_label,
            }
            # Si on changeait de session, finaliser la précédente et calculer le range
            last_label = self._last_session_label.get(symbol)
            if last_label and last_label != session_label:
                # Finaliser la session précédente
                prev_key = None
                for k, v in self._session_states[symbol].items():
                    if v.get('session_label') == last_label and v.get('date') == date_str:
                        prev_key = k
                        break
                if prev_key:
                    prev_state = self._session_states[symbol][prev_key]
                    prev_state['close'] = price  # Dernier prix avant changement
                    prev_state['range'] = prev_state['high'] - prev_state['low']
                    # Ajouter à l'historique pour vol_regime (PAR SYMBOL)
                    if prev_state['range'] > 0:
                        if symbol not in self._session_ranges_history:
                            self._session_ranges_history[symbol] = []
                        self._session_ranges_history[symbol].append(prev_state['range'])
                        # Garder seulement les 20 dernières sessions
                        if len(self._session_ranges_history[symbol]) > 20:
                            self._session_ranges_history[symbol].pop(0)
        else:
            # Mise à jour de la session actuelle
            state = self._session_states[symbol][session_key]
            state['high'] = max(state['high'], price)
            state['low'] = min(state['low'], price)
            state['close'] = price
            state['range'] = state['high'] - state['low']

        self._last_session_label[symbol] = session_label

    def _get_inter_session_context_snapshot(
        self, symbol: str, current_time: datetime, session_label: str, session_key: str
    ) -> Dict[str, Any]:
        """
        Retourne un snapshot de contexte inter-session pour un trade ouvert.
        Inclut : session_label, bucket4h, sweep_flags, vol_regime.
        """
        try:
            from zoneinfo import ZoneInfo
            ny_time = current_time.astimezone(ZoneInfo("America/New_York"))
        except Exception:
            ny_time = current_time

        date_str = str(ny_time.date())
        snapshot = {
            'timestamp': current_time.isoformat(),
            'symbol': symbol,
            'session_label': session_label,
            'session_key': session_key,
            'sweep_flags': {},
            'vol_regime': 'unknown',
            'session_states': {},
        }

        # Récupérer les états des sessions (ASIA/LONDON/NY)
        symbol_states = self._session_states.get(symbol, {})
        for sess_key, state in symbol_states.items():
            if state.get('date') == date_str:
                sess_label = state.get('session_label', '')
                snapshot['session_states'][sess_label] = {
                    'open': state.get('open', 0.0),
                    'high': state.get('high', 0.0),
                    'low': state.get('low', 0.0),
                    'close': state.get('close', 0.0),
                    'range': state.get('range', 0.0),
                }

        # Calculer les sweep flags inter-sessions
        asia_state = snapshot['session_states'].get('ASIA', {})
        london_state = snapshot['session_states'].get('LONDON', {})
        ny_state = snapshot['session_states'].get('NY', {})

        if asia_state and london_state:
            asia_high = asia_state.get('high', 0.0)
            asia_low = asia_state.get('low', 0.0)
            london_high = london_state.get('high', 0.0)
            london_low = london_state.get('low', 0.0)
            snapshot['sweep_flags']['london_sweeps_asia_high'] = london_high > asia_high if asia_high > 0 else False
            snapshot['sweep_flags']['london_sweeps_asia_low'] = london_low < asia_low if asia_low > 0 else False

        if london_state and ny_state:
            london_high = london_state.get('high', 0.0)
            london_low = london_state.get('low', 0.0)
            ny_high = ny_state.get('high', 0.0)
            ny_low = ny_state.get('low', 0.0)
            snapshot['sweep_flags']['ny_sweeps_london_high'] = ny_high > london_high if london_high > 0 else False
            snapshot['sweep_flags']['ny_sweeps_london_low'] = ny_low < london_low if london_low > 0 else False

        # Calculer vol_regime (range session / median range des dernières N sessions) - PAR SYMBOL
        current_session_state = snapshot['session_states'].get(session_label, {})
        current_range = current_session_state.get('range', 0.0)

        symbol_ranges = self._session_ranges_history.get(symbol, [])
        if symbol_ranges:
            median_range = sorted(symbol_ranges)[len(symbol_ranges) // 2]
            if median_range > 0:
                ratio = current_range / median_range
                if ratio > 1.5:
                    snapshot['vol_regime'] = 'high'
                elif ratio < 0.5:
                    snapshot['vol_regime'] = 'low'
                else:
                    snapshot['vol_regime'] = 'normal'
            else:
                snapshot['vol_regime'] = 'unknown'
        else:
            snapshot['vol_regime'] = 'unknown'

        return snapshot
    
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
        
        # R stats (NET by default)
        total_r_net = sum(t.pnl_net_R for t in self.trades)
        total_r_gross = sum(t.pnl_gross_R for t in self.trades)
        total_costs = sum(t.total_costs for t in self.trades)
        
        avg_r = total_r_net / total_trades if total_trades > 0 else 0.0
        avg_win_r = sum(t.pnl_net_R for t in wins) / len(wins) if wins else 0.0
        avg_loss_r = sum(t.pnl_net_R for t in losses) / len(losses) if losses else 0.0
        
        # Expectancy (net)
        win_prob = winrate / 100
        loss_prob = 1 - win_prob
        expectancy_r = (win_prob * avg_win_r) + (loss_prob * avg_loss_r)
        
        # Profit factor (net)
        gross_profit_net = sum(t.pnl_net_dollars for t in wins)
        gross_loss_net = abs(sum(t.pnl_net_dollars for t in losses))
        profit_factor_net = gross_profit_net / gross_loss_net if gross_loss_net > 0 else 0.0
        
        # Profit factor (gross for comparison)
        gross_profit_gross = sum(t.pnl_gross_dollars for t in wins)
        gross_loss_gross = abs(sum(t.pnl_gross_dollars for t in losses))
        profit_factor_gross = gross_profit_gross / gross_loss_gross if gross_loss_gross > 0 else 0.0
        
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
        
        # P0.2: Instrumentation multi-symbol dans debug_counts
        try:
            self.debug_counts["symbols_processed"] = list(stats_by_symbol.keys())
            self.debug_counts["metrics_by_symbol"] = stats_by_symbol
        except Exception:
            pass  # Ne pas faire crasher sur l'instrumentation
        
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
            # PHASE B: Gross vs Net
            total_pnl_gross_dollars=sum(t.pnl_gross_dollars for t in self.trades),
            total_pnl_net_dollars=total_pnl_dollars,
            total_pnl_gross_R=total_r_gross,
            total_pnl_net_R=total_r_net,
            total_costs_dollars=total_costs,
            # Legacy (use net)
            total_pnl_dollars=total_pnl_dollars,
            total_pnl_pct=total_pnl_pct,
            total_pnl_r=total_r_net,
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
            profit_factor=profit_factor_net,  # PHASE B: Use net
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

            # DIAGNOSTIC: Compter trade fermé
            self.debug_counts["trades_closed_total"] += 1

            # Marquer comme traité
            self._journaled_trade_ids.add(trade.id)

            # Récupérer le tier de risque utilisé (default 2 si pas enregistré)
            risk_tier = getattr(trade, 'risk_tier', 2)
            risk_dollars = getattr(trade, 'risk_amount', self.risk_engine.state.base_r_unit_dollars * risk_tier)
            
            # PHASE B: Calculate execution costs
            entry_costs, exit_costs = calculate_total_execution_costs(
                shares=int(trade.position_size),
                entry_price=trade.entry_price,
                exit_price=trade.exit_price,
                commission_model=self.config.commission_model,
                enable_reg_fees=self.config.enable_reg_fees,
                slippage_model=self.config.slippage_model,
                slippage_pct=self.config.slippage_cost_pct,
                slippage_ticks=self.config.slippage_ticks,
                spread_model=self.config.spread_model,
                spread_bps=self.config.spread_bps
            )
            
            total_costs = entry_costs.total + exit_costs.total
            
            # Calculate gross and net PnL
            pnl_gross_dollars = trade.pnl_dollars or 0.0
            pnl_net_dollars = pnl_gross_dollars - total_costs
            pnl_gross_R = pnl_gross_dollars / risk_dollars if risk_dollars > 0 else 0.0
            pnl_net_R = pnl_net_dollars / risk_dollars if risk_dollars > 0 else 0.0
            
            # Outcome based on NET PnL
            trade_result_str = 'win' if pnl_net_dollars > 0 else ('loss' if pnl_net_dollars < 0 else 'breakeven')
            
            # Nom du playbook pour stats
            pb_name = getattr(trade, "playbook", None) or "UNKNOWN"
            
            # Mettre à jour RiskEngine avec 2R/1R money management (use NET PnL)
            current_day = (trade.time_exit or timestamp).date()
            risk_update = self.risk_engine.update_risk_after_trade(
                trade_result=trade_result_str,
                trade_pnl_dollars=pnl_net_dollars,  # PHASE B: Use NET
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
                # PHASE B: Cost breakdown
                entry_commission=entry_costs.commission,
                entry_reg_fees=entry_costs.regulatory_fees,
                entry_slippage=entry_costs.slippage,
                entry_spread_cost=entry_costs.spread_cost,
                entry_total_cost=entry_costs.total,
                exit_commission=exit_costs.commission,
                exit_reg_fees=exit_costs.regulatory_fees,
                exit_slippage=exit_costs.slippage,
                exit_spread_cost=exit_costs.spread_cost,
                exit_total_cost=exit_costs.total,
                total_costs=total_costs,
                # PnL gross vs net
                pnl_gross_dollars=pnl_gross_dollars,
                pnl_net_dollars=pnl_net_dollars,
                pnl_gross_R=pnl_gross_R,
                pnl_net_R=pnl_net_R,
                # Legacy (backward compat, use net)
                pnl_dollars=pnl_net_dollars,
                pnl_r=pnl_net_R,
                outcome=trade_result_str,
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
    
    def _increment_reject_reason(self, reason: str):
        """
        P0 FIX: Incrémente de façon robuste le compteur de rejet de trade.
        
        - Ne dépend d'aucune variable externe (summary_path/trades_path/equity_path).
        - Ne doit jamais lever d'exception (fail-safe pour le backtest).
        - Limite à 10 raisons distinctes pour éviter d'exploser le JSON.
        """
        try:
            # S'assurer que la structure de destination existe
            reasons_dict = self.debug_counts.get("trades_open_rejected_by_reason")
            if not isinstance(reasons_dict, dict):
                reasons_dict = {}
                self.debug_counts["trades_open_rejected_by_reason"] = reasons_dict

            key = str(reason or "").strip() or "UNKNOWN"

            if key not in reasons_dict:
                if len(reasons_dict) >= 10:
                    # Limiter à 10 raisons max, ne rien faire au-delà
                    return
                reasons_dict[key] = 0

            reasons_dict[key] += 1
        except Exception:
            # Fail-safe absolu : ne jamais faire crasher le backtest sur l'instrumentation
            logger.exception("Failed to increment reject reason (ignored).")
    
    def _export_debug_counts(self):
        """Export debug_counts.json pour diagnostic"""
        try:
            output_dir = Path(self.config.output_dir)
            run_id = self.run_id
            
            # Ajouter métadonnées au debug_counts
            debug_data = {
                "run_id": run_id,
                "config": {
                    "start_date": self.config.start_date,
                    "end_date": self.config.end_date,
                    "htf_warmup_days": self.config.htf_warmup_days,
                    "trading_mode": self.config.trading_mode,
                    "trade_types": self.config.trade_types,
                    "symbols": self.config.symbols,
                },
                "counts": self.debug_counts.copy(),
            }
            
            # Convertir les dict en dict simples pour JSON
            if "htf_warmup_bars" in debug_data["counts"]:
                debug_data["counts"]["htf_warmup_bars"] = {
                    k: int(v) if isinstance(v, (int, float)) else str(v)
                    for k, v in debug_data["counts"]["htf_warmup_bars"].items()
                }
            
            debug_path = output_dir / f"debug_counts_{run_id}.json"
            import json
            with open(debug_path, 'w', encoding='utf-8') as f:
                json.dump(debug_data, f, indent=2, ensure_ascii=False)
            
            logger.info("  - Debug counts: %s", debug_path)
        except Exception as e:
            logger.warning(f"Failed to export debug_counts: {e}")
