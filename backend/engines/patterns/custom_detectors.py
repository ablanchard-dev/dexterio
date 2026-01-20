"""
Custom detectors wrapper for DexterioBOT.

This module provides a centralized interface to run the custom ICT detectors
introduced in Phase 2 (inverse FVG, order blocks, equilibrium and breaker
blocks).  It loads configuration parameters from ``patterns_config.yml`` and
exposes a single function to run all detectors on a candle sequence.  The
result is a dictionary keyed by pattern type containing lists of ``ICTPattern``
objects.  Using this wrapper decouples SetupEngine and other components from
the individual detector implementations.
"""

from typing import List, Dict, Any
from pathlib import Path
import yaml  # type: ignore

from models.market_data import Candle
from models.setup import ICTPattern

# Import individual detectors
from .ifvg import detect_ifvg
from .order_block import detect_order_blocks
from .equilibrium import detect_equilibrium
from .breaker_block import detect_breaker_blocks

# Import the core ICTPatternEngine to reuse existing BOS/FVG/SMT/CHOCH logic.
from .ict import ICTPatternEngine
from typing import Optional

# Lazy singleton instance of ICTPatternEngine.  Using a global avoids
# re-creating the engine on every call while still deferring import until
# needed.
_ICT_ENGINE: Optional[ICTPatternEngine] = None

def _get_ict_engine() -> ICTPatternEngine:
    """
    Lazily instantiate and return a singleton ICTPatternEngine.

    The ICTPatternEngine is stateful only with respect to configuration.
    Using a singleton avoids repeatedly reloading config on every call.
    """
    global _ICT_ENGINE
    if _ICT_ENGINE is None:
        _ICT_ENGINE = ICTPatternEngine()
    return _ICT_ENGINE


def _load_config() -> Dict[str, Any]:
    """
    Load pattern configuration from backend/knowledge/patterns_config.yml.
    If the file does not exist or cannot be parsed, returns an empty dict.
    """
    cfg: Dict[str, Any] = {}
    try:
        cfg_path = Path(__file__).resolve().parent.parent.parent / "knowledge" / "patterns_config.yml"
        if cfg_path.exists():
            with open(cfg_path, "r") as f:
                cfg = yaml.safe_load(f) or {}
    except Exception:
        cfg = {}
    return cfg


def detect_custom_patterns(candles: List[Candle], timeframe: str) -> Dict[str, List[ICTPattern]]:
    """
    Run all custom detectors on the given candles/timeframe.

    :param candles: List of Candle objects (ascending chronological order).
    :param timeframe: Timeframe label (e.g. "5m", "15m").
    :return: Dict mapping pattern type to list of ICTPattern detections.

    Example:
    >>> results = detect_custom_patterns(candles, "5m")
    >>> ifvg_patterns = results["ifvg"]
    >>> order_blocks = results["order_block"]
    """
    cfg = _load_config()
    # Each detector receives the global config section relevant to it (if defined)
    ifvg_cfg = cfg.get("ifvg") or {}
    ob_cfg = cfg.get("order_block") or {}
    eq_cfg = cfg.get("equilibrium") or {}
    brkr_cfg = cfg.get("breaker_block") or {}

    ict_engine = _get_ict_engine()
    # BOS and FVG detections via the core ICT engine
    bos_list = ict_engine.detect_bos(candles, timeframe)
    fvg_list = ict_engine.detect_fvg(candles, timeframe)
    return {
        "bos": bos_list,
        "fvg": fvg_list,
        "ifvg": detect_ifvg(candles, timeframe, ifvg_cfg),
        "order_block": detect_order_blocks(candles, timeframe, ob_cfg),
        "equilibrium": detect_equilibrium(candles, timeframe, eq_cfg),
        "breaker_block": detect_breaker_blocks(candles, timeframe, brkr_cfg),
    }

def detect_smt_pattern(spy_candles: List[Candle], qqq_candles: List[Candle]) -> List[ICTPattern]:
    """
    Wrapper around ICTPatternEngine.detect_smt() that always returns a list.

    :param spy_candles: 1h candles for SPY
    :param qqq_candles: 1h candles for QQQ
    :return: list of SMT patterns (0 or 1 element)
    """
    ict_engine = _get_ict_engine()
    pattern = ict_engine.detect_smt(spy_candles, qqq_candles)
    return [pattern] if pattern else []

def detect_choch_pattern(candles: List[Candle], last_sweep: Dict[str, Any]) -> List[ICTPattern]:
    """
    Wrapper around ICTPatternEngine.detect_choch() that always returns a list.

    :param candles: recent 5m candles
    :param last_sweep: last sweep dictionary
    :return: list of CHOCH patterns (0 or 1 element)
    """
    ict_engine = _get_ict_engine()
    pattern = ict_engine.detect_choch(candles, last_sweep)
    return [pattern] if pattern else []