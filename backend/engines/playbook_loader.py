"""
Playbook Loader - Charge et évalue les playbooks DAYTRADE & SCALP
Phase 2.2 - Intégration complète des playbooks YAML
"""
import yaml
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, time, timezone
from models.setup import Setup, ICTPattern, CandlestickPattern

logger = logging.getLogger(__name__)

# Debug timefilters pour SCALP A+
TIMEFILTER_DEBUG: Dict[str, Dict[str, Any]] = {
    'SCALP_Aplus_1_Mini_FVG_Retest_NY_Open': {
        'total_checked': 0,
        'pass_session': 0,
        'pass_time_range': 0,
        'pass_both': 0,
        'samples': [],
    }
}

# Debug scoring DAY A+ (échantillon limité)
DEBUG_DAY_APLUS: list = []

# Debug scoring détaillé avec "reason for zero score" (20 samples max)
DEBUG_DAY_APLUS_SCORING: list = []
DEBUG_DAY_APLUS_SCORING_MAX = 20

# Helpers TZ
try:
    # Python 3.9+ zoneinfo si dispo
    from zoneinfo import ZoneInfo
    _NY_TZ = ZoneInfo("America/New_York")
except Exception:
    _NY_TZ = None

PLAYBOOKS_PATH = Path(__file__).parent.parent / "knowledge" / "playbooks.yml"
APLUS_SETUPS_PATH = Path(__file__).parent.parent / "knowledge" / "aplus_setups.yml"


class PlaybookDefinition:
    """Représente un playbook chargé depuis le YAML"""
    
    def __init__(self, data: Dict[str, Any]):
        self.name = data['playbook_name']
        self.category = data['category']  # DAYTRADE ou SCALP
        self.description = data['description']
        self.enabled_modes = data['enabled_in_modes']
        self.instruments = data['instruments']
        
        # Time filters
        # Le champ `session` est la session principale (NY/London/Asia/etc.) mais peut
        # également être utilisé pour des fenêtres personnalisées comme PREMARKET ou
        # MKT_OPEN_WINDOW.  Certains playbooks utilisent un champ `session_window`
        # dans le YAML ; dans ce cas, ce champ est prioritaire.
        timefilters = data.get('timefilters', {})
        sess = timefilters.get('session')
        # Préférence au champ session_window si défini
        if timefilters.get('session_window'):
            sess = timefilters.get('session_window')
        self.session = sess
        # Support both time_range (legacy) and time_windows (new)
        self.time_range = timefilters.get('time_range', [])
        self.time_windows = timefilters.get('time_windows', [])
        self.news_events_only = timefilters.get('news_events_only', False)
        
        # Context requirements
        ctx = data['context_requirements']
        self.htf_bias_allowed = ctx.get('htf_bias_allowed', [])
        self.day_type_allowed = ctx.get('day_type_allowed', [])
        self.structure_htf = ctx.get('structure_htf', [])
        self.london_sweep_required = ctx.get('london_sweep_required', False)
        self.volatility_min = ctx.get('volatility_min')
        self.volatility_max = ctx.get('volatility_max')
        
        # ICT confluences
        ict = data['ict_confluences']
        self.require_sweep = ict.get('require_sweep', False)
        self.allow_fvg = ict.get('allow_fvg', False)
        self.require_bos = ict.get('require_bos', False)
        self.smt_bonus = ict.get('smt_bonus', False)
        
        # Candlestick patterns
        candles = data['candlestick_patterns']
        self.required_pattern_families = candles.get('required_families', [])
        self.pattern_direction = candles.get('direction', 'any')
        
        # Entry/SL/TP logic
        self.entry_type = data['entry_logic']['type']
        self.entry_zone = data['entry_logic']['zone']
        self.sl_type = data['stop_loss_logic']['type']
        self.sl_distance = data['stop_loss_logic']['distance']
        self.min_rr = data['take_profit_logic']['min_rr']
        self.tp1_rr = data['take_profit_logic']['tp1_rr']
        self.tp2_rr = data['take_profit_logic']['tp2_rr']
        self.breakeven_at_rr = data['take_profit_logic']['breakeven_at_rr']
        
        # Scoring
        self.scoring_weights = data['scoring']['weights']
        self.grade_thresholds = data['scoring']['grade_thresholds']
        
        # Max duration (pour scalps)
        self.max_duration_minutes = data.get('max_duration_minutes')

        # Signaux obligatoires (ex : ["IFVG_BEAR@5m", "OB_BULL@15m"]).
        # Si présents, le playbook n'est considéré que si TOUS ces signaux
        # sont détectés par les moteurs de patterns.  Absent ou liste vide = aucun filtre.
        self.required_signals: List[str] = data.get('required_signals', [])


class PlaybookLoader:
    """Charge tous les playbooks depuis le fichier YAML"""
    
    def __init__(self, playbooks_path: Path = PLAYBOOKS_PATH, aplus_path: Path = APLUS_SETUPS_PATH):
        self.playbooks_path = playbooks_path
        self.aplus_path = aplus_path
        self.playbooks: List[PlaybookDefinition] = []
        # Stockera les playbooks A+ séparément afin de ne pas les compter dans le total
        self.aplus_playbooks: List[PlaybookDefinition] = []
        self.load_playbooks()
    
    def load_playbooks(self):
        """Charge les playbooks CORE + ajoute les setups A+ depuis aplus_setups.yml"""
        try:
            # 1) Playbooks historiques (playbooks.yml)
            with open(self.playbooks_path, 'r') as f:
                data = yaml.safe_load(f)
            
            if not data:
                logger.warning(f"No playbooks found in {self.playbooks_path}")
            else:
                for pb_data in data:
                    playbook = PlaybookDefinition(pb_data)
                    self.playbooks.append(playbook)
            
            # 2) Setups A+ (aplus_setups.yml) -> conversion en PlaybookDefinition
            try:
                if self.aplus_path.exists():
                    with open(self.aplus_path, 'r') as f:
                        aplus_cfg = yaml.safe_load(f) or {}
                    day_setups = aplus_cfg.get('day_setups', [])
                    scalp_setups = aplus_cfg.get('scalp_setups', [])

                    def build_aplus_playbook(setup_cfg: Dict[str, Any]) -> PlaybookDefinition:
                        """Transforme une entrée A+ YAML en structure PlaybookDefinition compatible.

                        On mappe les champs A+ sur le schéma existant (category, timefilters, context, ict, candles, rr).
                        """
                        name = setup_cfg['name']
                        trade_type = setup_cfg.get('trade_type', 'DAILY')
                        category = 'DAYTRADE' if trade_type == 'DAILY' else 'SCALP'
                        symbols = setup_cfg.get('symbols', ['SPY', 'QQQ'])

                        # Timefilters
                        sess = setup_cfg.get('session', {})
                        session_name = sess.get('name', 'ANY')
                        time_range = sess.get('time_range', [])

                        # Contexte (on reste permissif, SAFE filtrera ensuite par min_grade)
                        bias_cfg = setup_cfg.get('bias', {})
                        direction = bias_cfg.get('direction', 'both')
                        require_bos = bias_cfg.get('require_bos', False)

                        ctx_req = {
                            'htf_bias_allowed': ['bullish', 'bearish'] if direction == 'both' else [direction],
                            'day_type_allowed': ['trend', 'range', 'manipulation_reversal'],
                            'structure_htf': ['uptrend', 'downtrend', 'range'],
                            'london_sweep_required': False,
                            'volatility_min': None,
                            'volatility_max': None,
                        }

                        # ICT
                        ict_cfg = setup_cfg.get('ict', {})
                        use_fvg = ict_cfg.get('use_fvg', False)

                        ict_confluences = {
                            'require_sweep': setup_cfg.get('liquidity', {}).get('require_sweep', False),
                            'allow_fvg': bool(ict_cfg.get('allow_fvg', False) or use_fvg),
                            'require_bos': bool(require_bos),
                            'smt_bonus': False,
                        }

                        # Candles
                        candles_cfg = setup_cfg.get('candles', {})
                        long_fams = candles_cfg.get('long_required_families', [])
                        short_fams = candles_cfg.get('short_required_families', [])
                        # On fusionne long/short pour rester compatible avec le schéma existant
                        required_families = sorted(list(set(long_fams + short_fams)))

                        candlestick_patterns = {
                            'required_families': required_families,
                            'direction': candles_cfg.get('direction', 'any'),
                        }

                        # Entry / SL / TP / scoring par défaut "A+"
                        rr_cfg = setup_cfg.get('rr', {})
                        min_rr = float(rr_cfg.get('min_rr', 2.0))
                        tp1_rr = float(rr_cfg.get('tp1_rr', min_rr))
                        tp2_rr = float(rr_cfg.get('tp2_rr', max(min_rr * 1.5, tp1_rr)))
                        breakeven_at_rr = float(rr_cfg.get('breakeven_at_rr', min_rr / 2))

                        # Scoring spécifique pour les A+ (plus permissif que les playbooks CORE)
                        if name == "DAY_Aplus_1_Liquidity_Sweep_OB_Retest":
                            # IMPORTANT: En attendant que sweep/BOS soient correctement détectés,
                            # on rééquilibre les poids vers FVG+pattern qui sont actuellement fonctionnels
                            scoring_cfg = {
                                'weights': {
                                    'liquidity_sweep': 0.15,  # Réduit car sweep souvent absent
                                    'bos_strength': 0.15,     # Réduit car BOS souvent absent
                                    'fvg_quality': 0.35,      # Augmenté - fonctionne bien
                                    'pattern_quality': 0.35,  # Augmenté - fonctionne bien
                                },
                                'grade_thresholds': {
                                    'A_plus': 0.50,  # Abaissé pour permettre plus de trades
                                    'A': 0.30,       # Abaissé
                                    'B': 0.20,       # Abaissé
                                },
                            }
                        elif name == "SCALP_Aplus_1_Mini_FVG_Retest_NY_Open":
                            # SCALP A+ scoring
                            # NOTE: Le scoring actuel ne permet pas de générer des grades A/B
                            # car les composantes FVG/pattern ne donnent pas des scores assez élevés.
                            # Mode SAFE ne génère pas de trades en attendant calibration fine.
                            scoring_cfg = {
                                'weights': {
                                    'fvg_quality': 0.45,
                                    'pattern_quality': 0.30,
                                    'liquidity_sweep': 0.15,
                                    'context_strength': 0.10,
                                },
                                'grade_thresholds': {
                                    'A_plus': 0.60,
                                    'A': 0.35,
                                    'B': 0.25,
                                },
                            }
                        else:
                            scoring_cfg = {
                                'weights': {
                                    'liquidity_sweep': 0.3 if setup_cfg.get('liquidity', {}).get('require_sweep', False) else 0.1,
                                    'pattern_quality': 0.3,
                                    'bos_strength': 0.2 if require_bos else 0.1,
                                    'fvg_quality': 0.2 if ict_confluences['allow_fvg'] else 0.1,
                                },
                                'grade_thresholds': {
                                    'A_plus': 0.85,
                                    'A': 0.75,
                                    'B': 0.65,
                                },
                            }

                        data_pb = {
                            'playbook_name': name,
                            'category': category,
                            'description': setup_cfg.get('description', ''),
                            'enabled_in_modes': ['SAFE', 'AGGRESSIVE'],
                            'instruments': symbols,
                            'timefilters': {
                                'session': session_name,
                                'time_range': time_range,
                                'news_events_only': False,
                            },
                            'context_requirements': ctx_req,
                            'ict_confluences': ict_confluences,
                            'candlestick_patterns': candlestick_patterns,
                            'entry_logic': {
                                'type': 'LIMIT',
                                'zone': 'pattern_close',
                                'confirmation_tf': setup_cfg.get('entry', {}).get('confirmation_tf', '1m'),
                            },
                            'stop_loss_logic': {
                                'type': 'FIXED',
                                'distance': 'structure',
                                'padding_ticks': 1,
                            },
                            'take_profit_logic': {
                                'min_rr': min_rr,
                                'tp1_rr': tp1_rr,
                                'tp2_rr': tp2_rr,
                                'breakeven_at_rr': breakeven_at_rr,
                            },
                            'scoring': scoring_cfg,
                        }

                        if category == 'SCALP':
                            data_pb['max_duration_minutes'] = 20

                        pb_def = PlaybookDefinition(data_pb)
                        return pb_def

                    # Construire et stocker dans aplus_playbooks au lieu de self.playbooks
                    self.aplus_playbooks = []
                    for cfg in day_setups:
                        try:
                            self.aplus_playbooks.append(build_aplus_playbook(cfg))
                        except Exception:
                            pass
                    for cfg in scalp_setups:
                        try:
                            self.aplus_playbooks.append(build_aplus_playbook(cfg))
                        except Exception:
                            pass

                    # Log debug pour vérifier présence des A+ dans une liste séparée
                    try:
                        names = [p.name for p in self.aplus_playbooks]
                        logger.info(f"Playbooks A+ chargés (exclus du total): {names}")
                    except Exception:
                        logger.info("Playbooks A+ chargés - debug names skipped")

                    logger.info(f"   + Loaded {len(day_setups) + len(scalp_setups)} A+ setups from {self.aplus_path}")
            except Exception as e:
                logger.error(f"Error loading A+ setups: {e}", exc_info=True)

            logger.info(f"✅ Loaded {len(self.playbooks)} playbooks (CORE + A+)")
            
            # Stats
            daytrade = [p for p in self.playbooks if p.category == 'DAYTRADE']
            scalp = [p for p in self.playbooks if p.category == 'SCALP']
            logger.info(f"   DAYTRADE: {len(daytrade)}, SCALP: {len(scalp)}")
        
        except Exception as e:
            logger.error(f"Error loading playbooks: {e}", exc_info=True)
    
    def get_playbooks_for_mode(self, mode: str) -> List[PlaybookDefinition]:
        """Retourne les playbooks activés pour un mode donné (SAFE/AGGRESSIVE)"""
        return [p for p in self.playbooks if mode in p.enabled_modes]
    
    def get_playbook_by_name(self, name: str) -> Optional[PlaybookDefinition]:
        """Récupère un playbook par son nom"""
        for p in self.playbooks:
            if p.name == name:
                return p
        return None


class PlaybookEvaluator:
    """Évalue si un setup correspond à un playbook"""
    
    def __init__(self, playbook_loader: PlaybookLoader):
        self.loader = playbook_loader
    
    def evaluate_all_playbooks(
        self,
        symbol: str,
        market_state: Dict,
        ict_patterns: List[ICTPattern],
        candle_patterns: List[CandlestickPattern],
        current_time: datetime,
        trading_mode: str
    ) -> List[Dict]:
        """
        Évalue tous les playbooks pour un contexte donné
        
        Returns:
            Liste de matches avec playbook_name, score, grade
        """
        playbooks = self.loader.get_playbooks_for_mode(trading_mode)
        matches = []
        
        for playbook in playbooks:
            # Vérifier si le playbook est applicable
            basic_pass, basic_reason = self._check_basic_filters(playbook, symbol, current_time, market_state)
            if not basic_pass:
                continue
            
            # Évaluer les conditions
            score, details = self._evaluate_playbook_conditions(
                playbook,
                market_state,
                ict_patterns,
                candle_patterns
            )
            
            if score is None:
                continue
            
            # Calculer le grade
            grade = self._calculate_grade(score, playbook.grade_thresholds)
            
            # Debug DAY A+ : capturer jusqu'à 20 entrées avec composantes de score
            if playbook.name == 'DAY_Aplus_1_Liquidity_Sweep_OB_Retest' and len(DEBUG_DAY_APLUS) < 20:
                dbg = details.get('debug_components', {}) if isinstance(details, dict) else {}
                DEBUG_DAY_APLUS.append({
                    'timestamp': current_time.isoformat(),
                    'symbol': symbol,
                    'trade_type': 'DAILY',
                    'playbook': playbook.name,
                    'quality': grade,
                    'score_total': score,
                    'liquidity_sweep_score': dbg.get('liquidity_sweep_score', 0.0),
                    'bos_strength_score': dbg.get('bos_strength_score', 0.0),
                    'fvg_quality_score': dbg.get('fvg_quality_score', 0.0),
                    'pattern_quality_score': dbg.get('pattern_quality_score', 0.0),
                    'sweep_detected': dbg.get('has_sweep', False),
                    'bos_detected': dbg.get('has_bos', False),
                    'fvg_detected': dbg.get('has_fvg', False),
                    'pattern_detected': dbg.get('has_pattern', False),
                })
            
            # Debug DAY A+ SCORING: capturer les cas où detected=True mais score était 0 (avant plancher)
            if playbook.name == 'DAY_Aplus_1_Liquidity_Sweep_OB_Retest' and len(DEBUG_DAY_APLUS_SCORING) < DEBUG_DAY_APLUS_SCORING_MAX:
                dbg = details.get('debug_components', {}) if isinstance(details, dict) else {}
                # On capture si BOS ou FVG détecté ET qu'il y avait un reason_*_score_zero
                has_reason = dbg.get('reason_bos_score_zero') or dbg.get('reason_fvg_score_zero')
                if has_reason or (dbg.get('has_bos') and dbg.get('bos_strength_score', 0) > 0) or (dbg.get('has_fvg') and dbg.get('fvg_quality_score', 0) > 0):
                    DEBUG_DAY_APLUS_SCORING.append({
                        'timestamp': current_time.isoformat(),
                        'symbol': symbol,
                        'quality': grade,
                        'score_total': score,
                        'bos_detected': dbg.get('has_bos', False),
                        'bos_raw_strength': dbg.get('bos_raw_strength', None),
                        'bos_strength_score': dbg.get('bos_strength_score', 0.0),
                        'reason_bos_score_zero': dbg.get('reason_bos_score_zero'),
                        'fvg_detected': dbg.get('has_fvg', False),
                        'fvg_raw_strength': dbg.get('fvg_raw_strength', None),
                        'fvg_quality_score': dbg.get('fvg_quality_score', 0.0),
                        'reason_fvg_score_zero': dbg.get('reason_fvg_score_zero'),
                        'pattern_quality_score': dbg.get('pattern_quality_score', 0.0),
                        'liquidity_sweep_score': dbg.get('liquidity_sweep_score', 0.0),
                    })
            
            matches.append({
                'playbook_name': playbook.name,
                'playbook_category': playbook.category,
                'score': score,
                'grade': grade,
                'details': details,
                'min_rr': playbook.min_rr,
                'tp1_rr': playbook.tp1_rr,
                'tp2_rr': playbook.tp2_rr,
                'entry_type': playbook.entry_type,
                'max_duration_minutes': playbook.max_duration_minutes
            })
        
        return matches
    
    def _check_basic_filters(
        self,
        playbook: PlaybookDefinition,
        symbol: str,
        current_time: datetime,
        market_state: Dict,
        debug: Optional[Dict[str, int]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Vérifie les filtres de base (session / horaire) selon les définitions du playbook.
        
        Returns:
            Tuple[bool, Optional[str]]: (pass, reason_code)
            - Si pass=True: reason_code=None
            - Si pass=False: reason_code contient la raison exacte du rejet
        """
        
        # Instrument
        if symbol not in playbook.instruments:
            return False, "instrument_not_supported"
        
        # Récupérer éventuel debug pour ce playbook (SCALP A+ uniquement)
        if debug is None:
            debug = TIMEFILTER_DEBUG.get(playbook.name)
        if debug is not None:
            debug['total_checked'] += 1
        
        # Session & Time range: MUST evaluate in US/Eastern, not UTC
        # Step 1: Convert current_time to ET
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)
        if _NY_TZ is not None:
            current_time_et = current_time.astimezone(_NY_TZ)
        else:
            # Fallback: keep UTC if zoneinfo unavailable (should not happen in prod)
            current_time_et = current_time
        
        # Step 2: Re-compute session based on ET time (not market_state which was computed elsewhere)
        from utils.timeframes import get_session_info
        session_info_et = get_session_info(current_time_et, debug_log=False)
        current_session = str(session_info_et.get('name', 'off_hours')).upper()
        
        # Normalize session names
        if current_session in ['NY', 'NEW_YORK']:
            current_session = 'NY'
        elif current_session in ['LONDON']:
            current_session = 'LONDON'
        elif current_session in ['ASIA']:
            current_session = 'ASIA'
        elif current_session in ['OFF_HOURS']:
            current_session = 'OFF_HOURS'
        
        required_session_raw = (playbook.session or 'ANY').upper()
        
        # Gestion des sessions personnalisées (ex : Market Open, Pre‑Market)
        # Mappe certaines sessions à une session de base et des fenêtres horaires spécifiques.
        # Définir les fenêtres personnalisées (ex : Market Open, Pre‑Market).
        # On charge d'abord la configuration depuis patterns_config.yml.  S'il
        # existe une section "sessions" dans ce fichier, elle doit
        # contenir des clés de type PREMARKET / MKT_OPEN_WINDOW avec des
        # valeurs "HH:MM-HH:MM".  On convertit ensuite vers la structure
        # attendue (session de base + liste de fenêtres).  À défaut, on
        # utilise des valeurs par défaut.
        custom_session_windows: Dict[str, Any] = {}
        try:
            from pathlib import Path
            import yaml  # type: ignore
            cfg_path = Path(__file__).resolve().parent.parent / 'knowledge' / 'patterns_config.yml'
            if cfg_path.exists():
                with open(cfg_path, 'r') as f:
                    cfg = yaml.safe_load(f) or {}
                sess_cfg = (cfg.get('sessions') or {}) if isinstance(cfg, dict) else {}
                # Build mapping: key -> ('NY', [(start,end)])
                for key, window_str in sess_cfg.items():
                    key_up = key.upper()
                    if key_up == 'TIMEZONE':
                        continue
                    if isinstance(window_str, str) and '-' in window_str:
                        try:
                            start_str, end_str = window_str.split('-', 1)
                            custom_session_windows[key_up] = ('NY', [(start_str, end_str)])
                        except Exception:
                            pass
        except Exception:
            custom_session_windows = {}
        # Fallback par défaut si config non trouvée
        if not custom_session_windows:
            # Default windows if no configuration is provided.  Support both
            # PRE_MARKET and PREMARKET as aliases to avoid naming confusion.
            custom_session_windows = {
                'MKT_OPEN_WINDOW': ('NY', [('09:30', '10:00')]),
                'MARKET_OPEN_WINDOW': ('NY', [('09:30', '10:00')]),
                'PREMARKET': ('NY', [('07:00', '09:30')]),
                'PRE_MARKET': ('NY', [('07:00', '09:30')]),
            }
        # Normaliser les sessions classiques
        if required_session_raw in ['NY', 'NEW_YORK']:
            required_session = 'NY'
        elif required_session_raw == 'LONDON':
            required_session = 'LONDON'
        elif required_session_raw == 'ASIA':
            required_session = 'ASIA'
        elif required_session_raw == 'OFF_HOURS':
            required_session = 'OFF_HOURS'
        elif required_session_raw in custom_session_windows:
            # Session personnalisée : on applique la session de base et on activera la fenêtre horaire custom
            required_session = custom_session_windows[required_session_raw][0]
        else:
            required_session = required_session_raw

        pass_session = True
        # Ne vérifier la session que si ce n'est pas une custom window
        # Les custom windows (PRE_MARKET, MKT_OPEN_WINDOW, etc.) définissent leurs propres fenêtres horaires
        # indépendamment de la session globale
        is_custom_window = required_session_raw in custom_session_windows
        if not is_custom_window:
            if required_session != 'ANY' and required_session != current_session:
                pass_session = False
        if debug is not None and pass_session:
            debug['pass_session'] += 1
        
        # Time range (already in ET from Step 1)
        pass_time_range = True

        # Support time_windows (list of [start, end] pairs) or legacy time_range.  Si la session
        # demandée est une session personnalisée (Market Open / Pre‑Market), on utilise
        # custom_session_windows pour calculer la fenêtre horaire.
        custom_windows = []
        if required_session_raw in custom_session_windows:
            custom_windows = custom_session_windows[required_session_raw][1]
        
        
        if playbook.time_windows or custom_windows:
            # Liste de fenêtres : soit provenant du playbook, soit d'une session personnalisée
            # PRIORITÉ: si le playbook définit ses propres time_windows, on les utilise
            # custom_windows n'est utilisé que pour les sessions sans time_windows explicites
            windows = playbook.time_windows if playbook.time_windows else custom_windows
            current_hour = current_time_et.hour
            current_minute = current_time_et.minute
            current_t = time(current_hour, current_minute)
            in_any_window = False
            for window in windows:
                if len(window) != 2:
                    continue
                start_str, end_str = window[0], window[1]
                start_h, start_m = map(int, start_str.split(':'))
                end_h, end_m = map(int, end_str.split(':'))
                start_time = time(start_h, start_m)
                end_time = time(end_h, end_m)
                if start_time <= current_t <= end_time:
                    in_any_window = True
                    if debug is not None and len(debug.get('samples', [])) < 10:
                        ts_utc_orig = current_time.astimezone(timezone.utc) if current_time.tzinfo else current_time
                        ts_ny = current_time_et
                        tzname = ts_ny.tzname() if hasattr(ts_ny, 'tzname') else 'ET'
                        debug['samples'].append({
                            'timestamp_iso': current_time_et.isoformat(),
                            'timestamp_utc': ts_utc_orig.isoformat(),
                            'timestamp_ny': ts_ny.isoformat(),
                            'tzname': tzname,
                            'session_computed_et': current_session,
                            'current_time_hm': f"{current_hour:02d}:{current_minute:02d}",
                            'window': f"{start_str}-{end_str}"
                        })
                    break
            pass_time_range = in_any_window
        elif playbook.time_range:
            # Legacy format: ["09:30", "09:45", "15:00", "15:15"]
            current_hour = current_time_et.hour
            current_minute = current_time_et.minute
            in_range = False
            for i in range(0, len(playbook.time_range), 2):
                if i + 1 >= len(playbook.time_range):
                    break
                start_str = playbook.time_range[i]
                end_str = playbook.time_range[i + 1]
                start_h, start_m = map(int, start_str.split(':'))
                end_h, end_m = map(int, end_str.split(':'))
                start_time = time(start_h, start_m)
                end_time = time(end_h, end_m)
                current_t = time(current_hour, current_minute)
                if start_time <= current_t <= end_time:
                    in_range = True
                    if debug is not None and len(debug.get('samples', [])) < 10:
                        ts_utc_orig = current_time.astimezone(timezone.utc) if current_time.tzinfo else current_time
                        ts_ny = current_time_et
                        tzname = ts_ny.tzname() if hasattr(ts_ny, 'tzname') else 'ET'
                        debug['samples'].append({
                            'timestamp_iso': current_time_et.isoformat(),
                            'timestamp_utc': ts_utc_orig.isoformat(),
                            'timestamp_ny': ts_ny.isoformat(),
                            'tzname': tzname,
                            'session_computed_et': current_session,
                            'current_time_hm': f"{current_hour:02d}:{current_minute:02d}",
                            'start': start_str,
                            'end': end_str
                        })
                    break
            pass_time_range = in_range
        if debug is not None and pass_time_range:
            debug['pass_time_range'] += 1
        
        
        ok = pass_session and pass_time_range
        if debug is not None and ok:
            debug['pass_both'] += 1
        
        if not ok:
            if not pass_session:
                return False, "session_outside_window"
            else:
                return False, "timefilter_outside_window"
        
        # PATCH C FINAL: Vérifier news_events_only (FAIL-CLOSE strict)
        if playbook.news_events_only:
            day_type = market_state.get('day_type', '')
            # FAIL-CLOSE: Si day_type n'est pas défini ou n'est pas dans les autorisés, rejeter
            if not day_type or day_type not in playbook.day_type_allowed:
                return False, "news_events_day_type_mismatch"
        
        # PATCH C FINAL: Vérifier volatility_min (FAIL-CLOSE strict)
        if playbook.volatility_min is not None:
            volatility = market_state.get('volatility')
            # FAIL-CLOSE: Si volatilité non définie ou insuffisante, rejeter
            if volatility is None or volatility < playbook.volatility_min:
                return False, "volatility_insufficient"
        
        return True, None
    
    def _evaluate_playbook_conditions(
        self,
        playbook: PlaybookDefinition,
        market_state: Dict,
        ict_patterns: List[ICTPattern],
        candle_patterns: List[CandlestickPattern]
    ) -> tuple:
        """
        Évalue toutes les conditions du playbook
        
        Returns:
            (score, details) ou (None, None) si conditions non remplies
        """
        details = {}
        
        # AGGRESSIVE BACKTEST MODE: Relaxation des exigences strictes
        # Tant que sweep/day_type/candlestick engines ne sont pas câblés,
        # on ne bloque pas les playbooks sur ces confluences manquantes.
        # CONDITION STRICTE: TRADING_MODE=='AGGRESSIVE' uniquement
        # Interdit en LIVE/PAPER (SAFE mode garde les checks stricts)
        from config.settings import settings
        is_backtest_aggressive = (settings.TRADING_MODE == 'AGGRESSIVE')
        
        bypasses_applied = []
        if is_backtest_aggressive:
            details['aggressive_relaxation_active'] = True

        # 0. Vérifier les signaux obligatoires (required_signals).
        # Si le playbook définit des signaux obligatoires, on exige que chaque
        # signal déclaré soit présent parmi les patterns ICT détectés.  Un signal
        # est de la forme "TYPE_DIR@tf" (par exemple "IFVG_BEAR@5m").  Le type
        # est mappé à un pattern_type interne (ifvg, order_block, equilibrium,
        # breaker_block), et le suffixe de direction est facultatif.  Si la
        # direction est 'BULL' ou 'BULLISH', on attend une direction 'bullish';
        # si 'BEAR' ou 'BEARISH', direction 'bearish'.  Pour les signaux comme
        # EQ_REJECT, la direction est ignorée.
        if getattr(playbook, 'required_signals', None):
            # Construire un ensemble de patterns disponibles pour recherche rapide
            available = []  # tuples (type, direction, timeframe)
            for p in ict_patterns:
                # Assurer cohérence lower-case
                available.append((p.pattern_type.lower(), p.direction.lower(), p.timeframe.lower()))
            # Vérifier chaque signal
            for req in playbook.required_signals:
                try:
                    sig, tf = req.split('@')
                    tf = tf.lower()
                except ValueError:
                    sig = req
                    tf = None
                sig_parts = sig.split('_')
                base = sig_parts[0].upper()
                dir_seg = sig_parts[1].upper() if len(sig_parts) > 1 else None
                # Mapping abréviations → pattern_type
                type_map = {
                    'IFVG': 'ifvg',
                    'OB': 'order_block',
                    'EQ': 'equilibrium',
                    'BRKR': 'breaker_block',
                    'BRKRBLK': 'breaker_block',
                    'BRKRBLOCK': 'breaker_block',
                }
                p_type = type_map.get(base, base.lower())
                dir_required = None
                if dir_seg:
                    if dir_seg in ['BEAR', 'BEARISH']:
                        dir_required = 'bearish'
                    elif dir_seg in ['BULL', 'BULLISH']:
                        dir_required = 'bullish'
                    # 'REJECT' ne spécifie pas de direction pour EQ
                # Chercher correspondance
                found = False
                for (t0, d0, tf0) in available:
                    if t0 == p_type and (dir_required is None or d0 == dir_required) and (tf is None or tf0 == tf):
                        found = True
                        break
                if not found:
                    # Signal requis manquant → playbook inapplicable
                    return None, None
        
        # 1. Vérifier HTF Bias
        htf_bias = market_state.get('bias', 'neutral')
        # On ne rejette que si le biais est explicite ET incompatible.
        # Si le biais est 'neutral', on laisse passer et le scoring de contexte
        # (context_strength) fera la différence.
        if htf_bias != 'neutral' and htf_bias not in playbook.htf_bias_allowed:
            return None, None
        
        # 2. Vérifier structure HTF
        structure = market_state.get('daily_structure', 'unknown')
        # Même logique: si la structure est inconnue, on ne bloque pas, mais
        # le critère trend_strength reflètera la clarté de la tendance.
        
        # AGGRESSIVE: Relaxer structure_htf (MarketStateEngine produit 'bullish'/'bearish'
        # mais playbooks attendent 'uptrend'/'downtrend' - P1: normaliser le vocabulaire)
        if not is_backtest_aggressive:
            if playbook.structure_htf and structure not in playbook.structure_htf and structure != 'unknown':
                return None, None
        else:
            # BYPASS actif : on trace la raison
            if playbook.structure_htf and structure not in playbook.structure_htf and structure != 'unknown':
                bypasses_applied.append(f'structure_htf_mismatch:{structure}_not_in_{playbook.structure_htf}')
        
        # 3. Vérifier ICT confluences (assoupli en mode labo AGGRESSIVE)
        has_sweep = any(p.pattern_type == 'sweep' for p in ict_patterns)
        has_fvg = any(p.pattern_type == 'fvg' for p in ict_patterns)
        has_bos = any(p.pattern_type == 'bos' for p in ict_patterns)
        has_smt = any(p.pattern_type == 'smt' for p in ict_patterns)

        # Debug : initialiser les composantes pour DAY A+
        debug_components = {
            'has_sweep': has_sweep,
            'has_fvg': has_fvg,
            'has_bos': has_bos,
            'has_pattern': False,
            'liquidity_sweep_score': 0.0,
            'bos_strength_score': 0.0,
            'fvg_quality_score': 0.0,
            'pattern_quality_score': 0.0,
        }
        
        # Pour l'instant en backtest AGGRESSIVE, on ne bloque plus sur
        # require_sweep / require_bos pour éviter d'étouffer tous les playbooks
        # tant que les moteurs de sweep/day_type ne sont pas pleinement câblés.
        # On exige simplement au moins un pattern ICT présent (relaxé en AGGRESSIVE).
        if not is_backtest_aggressive and not ict_patterns:
            return None, None
        elif is_backtest_aggressive and not ict_patterns:
            bypasses_applied.append('ict_patterns_empty')
        
        # 4. Vérifier patterns candlestick OBLIGATOIRES (relaxé en AGGRESSIVE)
        matching_patterns = [
            p for p in candle_patterns
            if p.family in playbook.required_pattern_families
        ]
        
        # En mode AGGRESSIVE backtest, on ne rejette pas si aucun pattern chandelle
        if not is_backtest_aggressive and not matching_patterns:
            return None, None
        elif is_backtest_aggressive and not matching_patterns:
            bypasses_applied.append('candlestick_patterns_missing')
        
        debug_components['has_pattern'] = bool(matching_patterns)
        
        # Tracer les bypasses appliqués
        if bypasses_applied:
            details['bypasses_applied'] = bypasses_applied
        
        # 5. Calculer le score basé sur les weights
        score = 0.0
        
        for criterion, weight in playbook.scoring_weights.items():
            criterion_score = 0.0
            
            if criterion == 'liquidity_sweep':
                criterion_score = 1.0 if has_sweep else 0.0
                debug_components['liquidity_sweep_score'] = criterion_score
            
            elif criterion == 'pattern_quality':
                if matching_patterns:
                    # Moyenne des qualités des patterns matchés
                    criterion_score = sum(p.strength for p in matching_patterns) / len(matching_patterns)
                    debug_components['pattern_quality_score'] = criterion_score
            
            elif criterion == 'fvg_alignment':
                if has_fvg and playbook.allow_fvg:
                    criterion_score = 0.8
            
            elif criterion == 'smt_divergence':
                if has_smt and playbook.smt_bonus:
                    criterion_score = 1.0
            
            elif criterion == 'context_strength':
                # Basé sur la clarté du bias HTF
                if htf_bias in ['bullish', 'bearish']:
                    criterion_score = 0.9
                else:
                    criterion_score = 0.5
            
            elif criterion == 'bos_strength':
                if has_bos:
                    bos_patterns = [p for p in ict_patterns if p.pattern_type == 'bos']
                    if bos_patterns:
                        raw_strength = bos_patterns[0].strength
                        # CORRECTIF: Si détecté mais strength=0, appliquer un plancher de 0.3
                        if raw_strength <= 0.0:
                            criterion_score = 0.3  # Plancher minimal si BOS détecté
                            debug_components['reason_bos_score_zero'] = f"raw_strength={raw_strength}, applied_floor=0.3"
                        else:
                            criterion_score = raw_strength
                        debug_components['bos_strength_score'] = criterion_score
                        debug_components['bos_raw_strength'] = raw_strength
            
            elif criterion == 'fvg_quality':
                if has_fvg:
                    fvg_patterns = [p for p in ict_patterns if p.pattern_type == 'fvg']
                    if fvg_patterns:
                        raw_strength = fvg_patterns[0].strength
                        # CORRECTIF: Si détecté mais strength=0, appliquer un plancher de 0.3
                        if raw_strength <= 0.0:
                            criterion_score = 0.3  # Plancher minimal si FVG détecté
                            debug_components['reason_fvg_score_zero'] = f"raw_strength={raw_strength}, applied_floor=0.3"
                        else:
                            criterion_score = raw_strength
                        debug_components['fvg_quality_score'] = criterion_score
                        debug_components['fvg_raw_strength'] = raw_strength
            
            elif criterion == 'trend_strength':
                # Basé sur la structure
                if structure in ['uptrend', 'downtrend']:
                    criterion_score = 0.8
                else:
                    criterion_score = 0.3
            
            elif criterion == 'rejection_strength':
                # Basé sur les patterns de rejection (hammer, shooting star)
                rejection_patterns = [p for p in matching_patterns if p.family in ['pin_bar', 'hammer', 'shooting_star']]
                if rejection_patterns:
                    criterion_score = max(p.strength for p in rejection_patterns)
            
            elif criterion == 'day_momentum':
                # Basé sur le mouvement du jour
                criterion_score = 0.7  # Placeholder
            
            elif criterion == 'rejection_speed':
                criterion_score = 0.8  # Placeholder
            
            elif criterion == 'momentum':
                criterion_score = 0.7  # Placeholder
            
            elif criterion == 'range_quality':
                criterion_score = 0.6  # Placeholder
            
            elif criterion == 'volume':
                criterion_score = 0.5  # Placeholder
            
            elif criterion == 'range_touches':
                criterion_score = 0.6  # Placeholder
            
            elif criterion == 'wick_size':
                criterion_score = 0.7  # Placeholder
            
            elif criterion == 'volume_spike':
                criterion_score = 0.5  # Placeholder
            
            details[criterion] = criterion_score
            score += criterion_score * weight
        
        # Attacher les composants de debug pour DAY A+
        if playbook.name == 'DAY_Aplus_1_Liquidity_Sweep_OB_Retest':
            details = {'debug_components': debug_components}

        return score, details
    
    def _calculate_grade(self, score: float, thresholds: Dict) -> str:
        """Calcule le grade (A+/A/B) basé sur le score"""
        if score >= thresholds['A_plus']:
            return 'A+'
        elif score >= thresholds['A']:
            return 'A'
        elif score >= thresholds['B']:
            return 'B'
        else:
            return 'C'  # Ne devrait pas arriver si filtres bien faits


# Singleton loader
_playbook_loader = None

def get_playbook_loader() -> PlaybookLoader:
    """Retourne l'instance singleton du PlaybookLoader"""
    global _playbook_loader
    if _playbook_loader is None:
        _playbook_loader = PlaybookLoader()
    return _playbook_loader
