"""
P1 Test: Master Candle Calculation (Sprint 2)
Vérifie que la Master Candle est calculée correctement sans lookahead.
"""
import sys
from pathlib import Path
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

# Ajouter le chemin backend au PYTHONPATH
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from engines.master_candle import (
    calculate_master_candle,
    get_ny_rth_session_date,
    get_session_labels,
    NY_TZ,
    NY_OPEN_TIME
)


def test_master_candle_calculation():
    """Test que MC est calculée correctement sur la fenêtre 09:30-09:45 NY"""
    
    # Créer une série de candles artificielles pour une session NY
    session_date = datetime(2025, 8, 4, tzinfo=NY_TZ).date()
    ny_open = datetime.combine(session_date, NY_OPEN_TIME, NY_TZ)
    
    candles = []
    # Fenêtre MC: 09:30-09:45 (15 minutes)
    for i in range(20):  # 20 minutes de données
        ts = ny_open + timedelta(minutes=i)
        # Simuler un range: high augmente, low diminue légèrement
        base_price = 500.0
        high = base_price + (i * 0.1)  # Augmente
        low = base_price - (i * 0.05)  # Diminue légèrement
        close = base_price + (i * 0.02)
        
        candles.append({
            'timestamp': ts,
            'high': high,
            'low': low,
            'close': close,
        })
    
    # Calculer MC
    mc = calculate_master_candle(candles, window_minutes=15, session_date=session_date.isoformat())
    
    # Vérifications
    assert mc is not None, "MC doit être calculée"
    assert mc.mc_valid, "MC doit être valide (range > 0)"
    assert mc.session_date == session_date.isoformat(), "Session date doit correspondre"
    assert mc.start_ts == ny_open, "Start TS doit être NY open (09:30)"
    assert mc.end_ts == ny_open + timedelta(minutes=15), "End TS doit être 09:45"
    
    # MC high/low doivent être les extrêmes de la fenêtre 09:30-09:45
    mc_window_candles = candles[:15]  # Premières 15 minutes
    expected_high = max(c['high'] for c in mc_window_candles)
    expected_low = min(c['low'] for c in mc_window_candles)
    
    assert mc.mc_high == expected_high, f"MC high doit être {expected_high}, got {mc.mc_high}"
    assert mc.mc_low == expected_low, f"MC low doit être {expected_low}, got {mc.mc_low}"
    assert mc.mc_range == (expected_high - expected_low), "MC range doit être correct"
    assert mc.mc_window_minutes == 15, "Window minutes doit être 15"
    
    # Breakout: après 09:45, close > mc_high ou < mc_low
    # Dans notre test, close continue d'augmenter, donc devrait breakout LONG
    # Mais seulement APRÈS la fin de la fenêtre MC
    post_mc_candles = candles[15:]  # Après 09:45
    if post_mc_candles:
        first_post_close = post_mc_candles[0]['close']
        if first_post_close > mc.mc_high:
            assert mc.mc_breakout_dir == 'LONG', "Breakout doit être LONG si close > mc_high"
        elif first_post_close < mc.mc_low:
            assert mc.mc_breakout_dir == 'SHORT', "Breakout doit être SHORT si close < mc_low"
    
    print("✓ Test Master Candle calculation: OK")


def test_no_lookahead():
    """Test que breakout n'est pas calculé avant la fin de la fenêtre MC"""
    
    session_date = datetime(2025, 8, 4, tzinfo=NY_TZ).date()
    ny_open = datetime.combine(session_date, NY_OPEN_TIME, NY_TZ)
    
    # Seulement 10 minutes (moins que window_minutes=15)
    candles = []
    for i in range(10):
        ts = ny_open + timedelta(minutes=i)
        candles.append({
            'timestamp': ts,
            'high': 500.0 + i * 0.1,
            'low': 500.0 - i * 0.05,
            'close': 500.0 + i * 0.02,
        })
    
    # MC ne peut pas être calculée (pas assez de candles)
    mc = calculate_master_candle(candles, window_minutes=15, session_date=session_date.isoformat())
    
    # Si MC est None, c'est OK (pas assez de données)
    # Si MC existe mais fenêtre incomplète, breakout doit être NONE
    if mc:
        # Si on n'a pas assez de candles dans la fenêtre, breakout ne peut pas être calculé
        assert mc.mc_breakout_dir in ['NONE', None] or not mc.mc_valid, "Breakout ne doit pas être calculé si fenêtre incomplète"
    
    print("✓ Test no lookahead: OK")


def test_session_labels():
    """Test que get_session_labels fonctionne correctement"""
    
    # Timestamp dans killzone (09:30-10:30 NY)
    ts_killzone = datetime(2025, 8, 4, 9, 45, tzinfo=NY_TZ)
    labels = get_session_labels(ts_killzone)
    
    assert labels['session_label'] == 'ny', "Session label doit être 'ny'"
    assert labels['killzone_label'] == 'ny_open', "Killzone doit être 'ny_open' entre 09:30-10:30"
    
    # Timestamp hors killzone
    ts_outside = datetime(2025, 8, 4, 14, 0, tzinfo=NY_TZ)
    labels2 = get_session_labels(ts_outside)
    
    assert labels2['session_label'] == 'ny', "Session label doit être 'ny'"
    assert labels2['killzone_label'] == 'none', "Killzone doit être 'none' hors 09:30-10:30"
    
    print("✓ Test session labels: OK")


if __name__ == "__main__":
    test_master_candle_calculation()
    test_no_lookahead()
    test_session_labels()
    print("All Master Candle tests passed!")
