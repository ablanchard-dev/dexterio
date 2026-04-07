"""
Master Candle Engine - Sprint 2
Calcule la Master Candle (MC) pour chaque session NY RTH
"""
import logging
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# Timezone NY
NY_TZ = ZoneInfo("America/New_York")

# NY RTH Open (09:30 ET)
NY_OPEN_TIME = time(9, 30)


@dataclass
class MasterCandle:
    """Master Candle pour une session NY RTH"""
    session_date: str  # YYYY-MM-DD
    start_ts: datetime  # Début fenêtre MC (NY open)
    end_ts: datetime  # Fin fenêtre MC
    mc_high: float
    mc_low: float
    mc_range: float
    mc_valid: bool  # True si MC calculée correctement
    mc_breakout_dir: str  # LONG, SHORT, ou NONE (calculé APRÈS fin MC)
    mc_retest: bool = False  # Optionnel: retest après breakout
    mc_window_minutes: int = 15  # Fenêtre MC en minutes


def get_ny_rth_session_date(timestamp: datetime) -> str:
    """
    Retourne la date de session NY RTH pour un timestamp donné.
    Si avant 09:30 NY, la session est celle du jour précédent.
    
    Args:
        timestamp: Timestamp tz-aware (converti en NY si nécessaire)
    
    Returns:
        Date de session au format YYYY-MM-DD
    """
    # Convertir en timezone NY
    if timestamp.tzinfo is None:
        ny_ts = timestamp.replace(tzinfo=NY_TZ)
    else:
        ny_ts = timestamp.astimezone(NY_TZ)
    
    ny_date = ny_ts.date()
    ny_time = ny_ts.time()
    
    # Si avant 09:30 NY, la session est celle du jour précédent
    if ny_time < NY_OPEN_TIME:
        ny_date = ny_date - timedelta(days=1)
    
    return ny_date.isoformat()


def get_session_labels(timestamp: datetime) -> Dict[str, str]:
    """
    Retourne les labels de session pour un timestamp.
    
    Args:
        timestamp: Timestamp tz-aware
    
    Returns:
        Dict avec 'session_label' et 'killzone_label'
    """
    # Convertir en timezone NY
    if timestamp.tzinfo is None:
        ny_ts = timestamp.replace(tzinfo=NY_TZ)
    else:
        ny_ts = timestamp.astimezone(NY_TZ)
    
    ny_time = ny_ts.time()
    
    # Session label: toujours 'ny' pour RTH (v1 simplifié)
    session_label = 'ny'
    
    # Killzone: 09:30-10:30 NY
    killzone_label = 'none'
    if time(9, 30) <= ny_time <= time(10, 30):
        killzone_label = 'ny_open'
    
    return {
        'session_label': session_label,
        'killzone_label': killzone_label
    }


def calculate_master_candle(
    candles: List[Dict[str, Any]],
    window_minutes: int = 15,
    session_date: Optional[str] = None
) -> Optional[MasterCandle]:
    """
    Calcule la Master Candle pour une session NY RTH.
    
    Règle v1:
    - MC = range des N premières minutes après NY open (09:30 ET)
    - breakout = close au-dessus mc_high ou en dessous mc_low APRÈS la fenêtre MC
    - Pas de lookahead: breakout calculé uniquement après end_ts
    
    Args:
        candles: Liste de candles avec 'timestamp', 'high', 'low', 'close'
                 Les timestamps doivent être tz-aware (NY ou UTC)
        window_minutes: Durée de la fenêtre MC en minutes (défaut: 15)
        session_date: Date de session YYYY-MM-DD (optionnel, calculé si None)
    
    Returns:
        MasterCandle ou None si calcul impossible
    """
    if not candles:
        return None
    
    # Convertir timestamps en NY et trier
    ny_candles = []
    for candle in candles:
        ts = candle.get('timestamp')
        if ts is None:
            continue
        
        # Convertir en NY
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        
        if ts.tzinfo is None:
            ny_ts = ts.replace(tzinfo=NY_TZ)
        else:
            ny_ts = ts.astimezone(NY_TZ)
        
        ny_candles.append({
            'timestamp': ny_ts,
            'high': float(candle.get('high', 0)),
            'low': float(candle.get('low', 0)),
            'close': float(candle.get('close', 0)),
        })
    
    if not ny_candles:
        return None
    
    # Trier par timestamp
    ny_candles.sort(key=lambda x: x['timestamp'])
    
    # Trouver la première bougie après 09:30 NY
    ny_open_ts = None
    for candle in ny_candles:
        ny_time = candle['timestamp'].time()
        if ny_time >= NY_OPEN_TIME:
            # Créer timestamp exact 09:30 pour cette date
            ny_date = candle['timestamp'].date()
            ny_open_ts = datetime.combine(ny_date, NY_OPEN_TIME, NY_TZ)
            break
    
    if ny_open_ts is None:
        logger.debug("No candle found after NY open (09:30)")
        return None
    
    # Calculer session_date si non fourni
    if session_date is None:
        session_date = get_ny_rth_session_date(ny_open_ts)
    
    # Fenêtre MC: de 09:30 à 09:30 + window_minutes
    mc_end_ts = ny_open_ts + timedelta(minutes=window_minutes)
    
    # Extraire les bougies dans la fenêtre MC
    mc_candles = [
        c for c in ny_candles
        if ny_open_ts <= c['timestamp'] < mc_end_ts
    ]
    
    if not mc_candles:
        logger.debug(f"No candles in MC window ({ny_open_ts} to {mc_end_ts})")
        return None
    
    # Calculer MC high/low/range
    mc_high = max(c['high'] for c in mc_candles)
    mc_low = min(c['low'] for c in mc_candles)
    mc_range = mc_high - mc_low
    
    # Vérifier validité (range > 0)
    mc_valid = mc_range > 0
    
    # Calculer breakout APRÈS la fin de la fenêtre MC (pas de lookahead)
    mc_breakout_dir = 'NONE'
    mc_retest = False
    
    # Bougies après la fenêtre MC (P0 Fix #3: utiliser > strict pour éviter lookahead)
    post_mc_candles = [
        c for c in ny_candles
        if c['timestamp'] > mc_end_ts  # STRICT > pour éviter lookahead si timestamp égal
    ]
    
    if post_mc_candles and mc_valid:
        # Chercher le premier breakout
        for candle in post_mc_candles:
            close = candle['close']
            
            # Breakout LONG: close > mc_high
            if close > mc_high:
                mc_breakout_dir = 'LONG'
                # Vérifier retest (simplifié: prix revient sous mc_high)
                for later_candle in post_mc_candles[post_mc_candles.index(candle) + 1:]:
                    if later_candle['low'] <= mc_high:
                        mc_retest = True
                        break
                break
            
            # Breakout SHORT: close < mc_low
            elif close < mc_low:
                mc_breakout_dir = 'SHORT'
                # Vérifier retest (simplifié: prix revient au-dessus mc_low)
                for later_candle in post_mc_candles[post_mc_candles.index(candle) + 1:]:
                    if later_candle['high'] >= mc_low:
                        mc_retest = True
                        break
                break
    
    return MasterCandle(
        session_date=session_date,
        start_ts=ny_open_ts,
        end_ts=mc_end_ts,
        mc_high=mc_high,
        mc_low=mc_low,
        mc_range=mc_range,
        mc_valid=mc_valid,
        mc_breakout_dir=mc_breakout_dir,
        mc_retest=mc_retest,
        mc_window_minutes=window_minutes
    )
