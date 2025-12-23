"""Gestion des timeframes et sessions"""
from datetime import datetime, time, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd
import pytz
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Debug buffer pour sessions (SCALP A+ instrumentation)
SESSION_DEBUG_BUFFER: List[Dict[str, Any]] = []
SESSION_DEBUG_MAX = 200  # Limite de samples

class TimeframeAggregator:
    """Agrégation de bougies M1 vers timeframes supérieurs"""
    
    TIMEFRAME_MINUTES = {
        '1m': 1,
        '5m': 5,
        '15m': 15,
        '1h': 60,
        '4h': 240,
        '1d': 1440
    }
    
    def __init__(self):
        self.candles_buffer = {tf: [] for tf in self.TIMEFRAME_MINUTES.keys()}
    
    def add_m1_candle(self, candle: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Ajoute une bougie M1 et retourne les bougies agrégées complétées
        
        Returns:
            Dict avec clés = timeframes, valeurs = listes de bougies complétées
        """
        completed_candles = {}
        
        # Ajouter M1
        self.candles_buffer['1m'].append(candle)
        completed_candles['1m'] = [candle]
        
        # Agréger vers timeframes supérieurs
        for tf, minutes in self.TIMEFRAME_MINUTES.items():
            if tf == '1m':
                continue
            
            # Vérifier si on doit compléter une bougie de ce TF
            aggregated = self._aggregate_to_timeframe(candle['timestamp'], minutes)
            if aggregated:
                completed_candles[tf] = [aggregated]
        
        return completed_candles
    
    def _aggregate_to_timeframe(self, timestamp: datetime, minutes: int) -> Optional[Dict[str, Any]]:
        """
        Agrège les bougies M1 pour former une bougie du timeframe spécifié
        """
        # Simplifié pour MVP - à améliorer avec logique de fermeture exacte
        # En production, il faut vérifier si la minute actuelle marque la fin d'une période
        return None  # Placeholder

def get_session_info(timestamp: datetime, debug_log: bool = False) -> Dict[str, Any]:
    """
    Détermine la session de trading pour un timestamp donné.
    
    RÈGLE IMPORTANTE: NY a PRIORITÉ sur London dans la fenêtre de chevauchement (09:30-11:00 ET).
    
    Args:
        timestamp: Datetime (UTC ou timezone-aware)
        debug_log: Si True, ajoute un sample au buffer de debug pour SCALP A+
    
    Returns:
        Dict avec 'name', 'start', 'end', 'description' et metadata debug
    """
    # Convertir en ET (Eastern Time)
    et_tz = pytz.timezone('US/Eastern')
    
    # Gérer les timestamps naïfs
    if timestamp.tzinfo is None:
        # Assumer UTC si naïf
        timestamp = pytz.UTC.localize(timestamp)
    
    et_time = timestamp.astimezone(et_tz)
    current_time = et_time.time()
    
    # Sessions définies avec priorités (NY > London > Asia > off_hours)
    # NY DOIT être évalué AVANT London pour gérer le chevauchement 09:30-11:00
    sessions = [
        {
            'name': 'ny',
            'start': time(9, 30),
            'end': time(16, 0),
            'description': 'New York Session',
            'priority': 1
        },
        {
            'name': 'london',
            'start': time(3, 0),
            'end': time(9, 29),  # CORRIGÉ: London s'arrête à 09:29, NY prend le relais à 09:30
            'description': 'London Session',
            'priority': 2
        },
        {
            'name': 'asia',
            'start': time(18, 0),
            'end': time(2, 59),  # Jusqu'à 02:59
            'description': 'Asian Session',
            'priority': 3
        }
    ]
    
    # Trouver la session actuelle
    matched_session = None
    for session in sessions:
        if session['name'] == 'asia':
            # Session Asie chevauche minuit
            if current_time >= session['start'] or current_time <= session['end']:
                matched_session = session
                break
        else:
            if session['start'] <= current_time <= session['end']:
                matched_session = session
                break
    
    if matched_session is None:
        matched_session = {'name': 'off_hours', 'description': 'Outside trading hours', 'start': None, 'end': None}
    
    # Debug logging pour SCALP A+ (fenêtre 09:20-09:40 ET)
    debug_start = time(9, 20)
    debug_end = time(9, 40)
    if debug_log and debug_start <= current_time <= debug_end and len(SESSION_DEBUG_BUFFER) < SESSION_DEBUG_MAX:
        utc_time = timestamp.astimezone(pytz.UTC)
        is_dst = bool(et_time.dst())
        
        debug_entry = {
            'timestamp_utc': utc_time.isoformat(),
            'timestamp_us_eastern': et_time.isoformat(),
            'tzname': et_time.tzname(),
            'is_dst': is_dst,
            'computed_session': matched_session['name'],
            'current_time_hm': f"{current_time.hour:02d}:{current_time.minute:02d}",
            'london_start': '03:00',
            'london_end': '09:29',
            'ny_start': '09:30',
            'ny_end': '16:00',
        }
        SESSION_DEBUG_BUFFER.append(debug_entry)
    
    return matched_session


def export_session_debug(output_dir: Path, run_id: str) -> Optional[str]:
    """Exporte le buffer de debug des sessions vers un fichier JSONL."""
    if not SESSION_DEBUG_BUFFER:
        return None
    
    output_path = output_dir / f"debug_sessions_{run_id}.jsonl"
    with output_path.open("w", encoding="utf-8") as f:
        for entry in SESSION_DEBUG_BUFFER:
            f.write(json.dumps(entry) + "\n")
    
    logger.info(f"Session debug exported: {len(SESSION_DEBUG_BUFFER)} entries -> {output_path}")
    return str(output_path)

def is_in_kill_zone(timestamp: datetime) -> Dict[str, Any]:
    """
    Vérifie si le timestamp est dans une kill zone
    
    Returns:
        Dict avec 'in_kill_zone' (bool), 'zone_name' (str)
    """
    et_tz = pytz.timezone('US/Eastern')
    et_time = timestamp.astimezone(et_tz)
    current_time = et_time.time()
    
    kill_zones = [
        {
            'name': 'NY Morning',
            'start': time(9, 30),
            'end': time(11, 0)
        },
        {
            'name': 'NY Afternoon',
            'start': time(14, 0),
            'end': time(15, 30)
        }
    ]
    
    for zone in kill_zones:
        if zone['start'] <= current_time <= zone['end']:
            return {'in_kill_zone': True, 'zone_name': zone['name']}
    
    return {'in_kill_zone': False, 'zone_name': None}
