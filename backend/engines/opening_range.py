"""
Opening Range Tracker — G01

Captures the high/low of the first N minutes after session open.
Used by strategies V065 (15m range), V054 (5m range), V048 (15m range from 3x5m).

Usage:
    tracker = OpeningRangeTracker(duration_minutes=15, session_start_et="09:30")
    for candle in candles_1m:
        tracker.update(candle)
    if tracker.is_formed:
        print(tracker.range_high, tracker.range_low, tracker.midline)
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, time, date
from typing import Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")


@dataclass
class OpeningRangeState:
    """Immutable snapshot of a formed opening range."""
    range_high: float
    range_low: float
    session_date: date
    formed_at: datetime  # timestamp when range completed

    @property
    def midline(self) -> float:
        return (self.range_high + self.range_low) / 2

    @property
    def size(self) -> float:
        return self.range_high - self.range_low


class OpeningRangeTracker:
    """
    Tracks opening range formation for a single symbol.

    Parameters
    ----------
    duration_minutes : int
        How many minutes after session_start to capture.
        V065: 15 (1 candle 15m = 3 candles 5m = 15 candles 1m)
        V054: 5  (1 candle 5m = 5 candles 1m)
        V048: 15 (same window as V065)
    session_start_et : str
        Session start in ET, e.g. "09:30".
    """

    def __init__(self, duration_minutes: int = 15, session_start_et: str = "09:30"):
        self.duration_minutes = duration_minutes
        h, m = session_start_et.split(":")
        self._session_start_time = time(int(h), int(m))

        # Mutable state
        self._current_date: Optional[date] = None
        self._high: float = -float("inf")
        self._low: float = float("inf")
        self._bar_count: int = 0
        self._formed: bool = False
        self._formed_at: Optional[datetime] = None

        # Completed range (available after formation)
        self._state: Optional[OpeningRangeState] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_formed(self) -> bool:
        return self._formed

    @property
    def range_high(self) -> Optional[float]:
        return self._state.range_high if self._state else None

    @property
    def range_low(self) -> Optional[float]:
        return self._state.range_low if self._state else None

    @property
    def midline(self) -> Optional[float]:
        return self._state.midline if self._state else None

    @property
    def state(self) -> Optional[OpeningRangeState]:
        return self._state

    def update(self, timestamp: datetime, high: float, low: float) -> bool:
        """
        Feed a 1-minute candle. Returns True if the range just became formed.

        Parameters
        ----------
        timestamp : datetime
            UTC timestamp of the candle.
        high : float
            Candle high.
        low : float
            Candle low.

        Returns
        -------
        bool
            True if range was just completed on this call.
        """
        # Convert to ET for session logic
        if timestamp.tzinfo is None:
            from datetime import timezone
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        ts_et = timestamp.astimezone(ET)
        candle_date = ts_et.date()
        candle_time = ts_et.time()

        # New day → reset
        if candle_date != self._current_date:
            self._reset(candle_date)

        # Already formed for today → no-op
        if self._formed:
            return False

        # Before session start → ignore
        if candle_time < self._session_start_time:
            return False

        # Compute end time
        start_minutes = self._session_start_time.hour * 60 + self._session_start_time.minute
        end_minutes = start_minutes + self.duration_minutes
        end_time = time(end_minutes // 60, end_minutes % 60)

        # After range window → mark as formed with whatever we have
        if candle_time >= end_time:
            if self._bar_count > 0:
                return self._finalize(timestamp)
            return False

        # Inside range window → accumulate
        self._high = max(self._high, high)
        self._low = min(self._low, low)
        self._bar_count += 1

        # Check if we've accumulated enough minutes
        if self._bar_count >= self.duration_minutes:
            return self._finalize(timestamp)

        return False

    def reset(self) -> None:
        """Force reset (e.g. between backtest runs)."""
        self._current_date = None
        self._formed = False
        self._state = None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _reset(self, new_date: date) -> None:
        self._current_date = new_date
        self._high = -float("inf")
        self._low = float("inf")
        self._bar_count = 0
        self._formed = False
        self._formed_at = None
        self._state = None

    def _finalize(self, timestamp: datetime) -> bool:
        if self._high <= self._low:
            # Degenerate range (shouldn't happen with real data)
            return False
        self._formed = True
        self._formed_at = timestamp
        self._state = OpeningRangeState(
            range_high=self._high,
            range_low=self._low,
            session_date=self._current_date,
            formed_at=timestamp,
        )
        logger.debug(
            "Opening range formed: date=%s high=%.4f low=%.4f mid=%.4f size=%.4f",
            self._current_date,
            self._state.range_high,
            self._state.range_low,
            self._state.midline,
            self._state.size,
        )
        return True
