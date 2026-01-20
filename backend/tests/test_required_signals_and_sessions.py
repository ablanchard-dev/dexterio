"""
Tests pour vérifier le fonctionnement de `required_signals` et du filtre
`session_window` dans DexterioBOT.  Ces tests utilisent
PlaybookDefinition et PlaybookEvaluator pour s'assurer que la logique
rejecte correctement les setups en absence de signaux ou en dehors des
fenêtres de session définies.

Instructions : exécuter avec `pytest` à la racine du backend.
"""

from datetime import datetime, timezone

import pytest

from engines.playbook_loader import PlaybookDefinition, PlaybookEvaluator


def _minimal_playbook_data(name: str) -> dict:
    """Crée un dict minimal pour construire un PlaybookDefinition."""
    return {
        'playbook_name': name,
        'category': 'SCALP',
        'description': '',
        'enabled_in_modes': ['AGGRESSIVE'],
        'instruments': ['SPY'],
        'timefilters': {
            'session': 'NY',
            'time_range': [],
            'time_windows': [],
            'news_events_only': False,
        },
        'context_requirements': {
            'htf_bias_allowed': ['bullish', 'bearish'],
            'day_type_allowed': [],
            'structure_htf': [],
            'london_sweep_required': False,
            'volatility_min': None,
            'volatility_max': None,
        },
        'ict_confluences': {
            'require_sweep': False,
            'allow_fvg': False,
            'require_bos': False,
            'smt_bonus': False,
        },
        'candlestick_patterns': {
            'required_families': [],
            'direction': 'any',
        },
        'entry_logic': {
            'type': 'LIMIT',
            'zone': 'pattern_close',
        },
        'stop_loss_logic': {
            'type': 'FIXED',
            'distance': 'structure',
        },
        'take_profit_logic': {
            'min_rr': 1.0,
            'tp1_rr': 1.0,
            'tp2_rr': 2.0,
            'breakeven_at_rr': 0.5,
        },
        'scoring': {
            'weights': {
                'liquidity_sweep': 0.1,
                'pattern_quality': 0.4,
                'bos_strength': 0.2,
                'fvg_quality': 0.3,
            },
            'grade_thresholds': {
                'A_plus': 0.8,
                'A': 0.6,
                'B': 0.4,
            },
        },
    }


def test_required_signals_missing():
    """Vérifie qu'un playbook avec required_signals rejette en absence de pattern."""
    data = _minimal_playbook_data('Test_Required')
    data['required_signals'] = ['IFVG_BEAR@5m']
    playbook = PlaybookDefinition(data)
    evaluator = PlaybookEvaluator(None)  # loader optional for internal methods
    # Aucun pattern ICT disponible
    ict_patterns: list = []
    # Market state minimal
    market_state = {
        'bias': 'neutral',
        'daily_structure': 'unknown',
    }
    # _evaluate_playbook_conditions retourne (None, None) si manquant
    score, details = evaluator._evaluate_playbook_conditions(playbook, market_state, ict_patterns, [])
    assert score is None and details is None


def test_session_window_pre_market():
    """Vérifie que le filtre session_window PRE_MARKET accepte/rejette selon l'heure."""
    # Playbook demandant une fenêtre PRE_MARKET
    data = _minimal_playbook_data('Test_Session')
    data['timefilters']['session_window'] = 'PRE_MARKET'
    playbook = PlaybookDefinition(data)
    evaluator = PlaybookEvaluator(None)
    # Market state minimal
    market_state = {
        'bias': 'neutral',
        'current_session': 'NY',
        'daily_structure': 'unknown',
    }
    # Cas 1 : 08:00 ET (dans la fenêtre)
    # Convertir 08:00 New York en UTC
    import zoneinfo
    ny_tz = zoneinfo.ZoneInfo('America/New_York')
    dt_ny = datetime(2025, 6, 1, 8, 0, tzinfo=ny_tz)
    dt_utc = dt_ny.astimezone(timezone.utc)
    result, reason = evaluator._check_basic_filters(playbook, 'SPY', dt_utc, market_state)
    assert result is True
    # Cas 2 : 10:30 ET (hors fenêtre)
    dt_ny2 = datetime(2025, 6, 1, 10, 30, tzinfo=ny_tz)
    dt_utc2 = dt_ny2.astimezone(timezone.utc)
    result2, reason2 = evaluator._check_basic_filters(playbook, 'SPY', dt_utc2, market_state)
    assert result2 is False