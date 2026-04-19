"""
Session Range Tracker — tracks Asian/London/NY session high/low.

Used by:
  - S3 V066 London Fakeout: needs Asian session H/L (sweeps during London)
  - S3 V051 Asia Sweep: needs Asian session H/L (sweeps during London 02:00-05:00)

Session definitions (all times in ET / America/New_York):
  - Asian:  18:00 (prev day) to 03:00
  - London: 03:00 to 08:00
  - NY:     09:30 to 16:00

Usage:
    tracker = SessionRangeTracker()
    for candle_1m in candles:
        tracker.update(candle_1m.timestamp, candle_1m.high, candle_1m.low)
    asian = tracker.get_range("asian")  # SessionRangeState or None
    london = tracker.get_range("london")
"""
import logging
from dataclasses import dataclass
from datetime import datetime, time, date, timedelta
from typing import Optional, Dict
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")

# Session boundaries in ET
_SESSIONS = {
    "asian": (time(18, 0), time(3, 0)),    # 18:00 prev day to 03:00
    "london": (time(3, 0), time(8, 0)),     # 03:00 to 08:00
    "ny": (time(9, 30), time(16, 0)),       # 09:30 to 16:00
}


@dataclass
class SessionRangeState:
    """Immutable snapshot of a completed session range."""
    session_name: str
    range_high: float
    range_low: float
    session_date: date  # trading date (the NY date)
    formed: bool = True

    @property
    def midline(self) -> float:
        return (self.range_high + self.range_low) / 2

    @property
    def size(self) -> float:
        return self.range_high - self.range_low


class SessionRangeTracker:
    """
    Tracks session high/low for Asian, London, and NY sessions.

    Updates minute by minute. Once a session closes, its range is frozen
    and available via get_range().

    The Asian session spans midnight (18:00 prev day → 03:00), so the
    tracker handles the day-boundary crossing.
    """

    def __init__(self):
        # Current trading date (resets at 18:00 ET when Asian opens)
        self._trading_date: Optional[date] = None

        # In-progress tracking: {session_name: {high, low, bar_count}}
        self._building: Dict[str, dict] = {}

        # Completed ranges: {session_name: SessionRangeState}
        self._completed: Dict[str, SessionRangeState] = {}

        # Track which session was last active to detect transitions
        self._last_session: Optional[str] = None

    def get_range(self, session_name: str) -> Optional[SessionRangeState]:
        """Get the completed range for a session. None if not yet formed."""
        return self._completed.get(session_name)

    @property
    def asian_high(self) -> Optional[float]:
        r = self._completed.get("asian")
        return r.range_high if r else None

    @property
    def asian_low(self) -> Optional[float]:
        r = self._completed.get("asian")
        return r.range_low if r else None

    def update(self, timestamp: datetime, high: float, low: float) -> Optional[str]:
        """
        Feed a 1-minute candle.

        Returns the name of a session that just completed (froze), or None.
        """
        if timestamp.tzinfo is None:
            from datetime import timezone
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        ts_et = timestamp.astimezone(ET)
        t = ts_et.time()

        # Determine which session this bar belongs to
        current_session = self._classify_time(t)

        # Determine trading date: resets at 18:00 ET (Asian session start)
        if t >= time(18, 0):
            trading_date = ts_et.date() + timedelta(days=1)
        else:
            trading_date = ts_et.date()

        # New trading date → reset all
        if trading_date != self._trading_date:
            self._trading_date = trading_date
            self._building.clear()
            self._completed.clear()
            self._last_session = None

        completed_session = None

        # If session changed, freeze the previous session
        if current_session != self._last_session and self._last_session is not None:
            prev = self._last_session
            if prev in self._building and self._building[prev]["bar_count"] > 0:
                self._freeze(prev)
                completed_session = prev

        # Accumulate into current session
        if current_session is not None:
            if current_session not in self._building:
                self._building[current_session] = {
                    "high": -float("inf"),
                    "low": float("inf"),
                    "bar_count": 0,
                }
            b = self._building[current_session]
            b["high"] = max(b["high"], high)
            b["low"] = min(b["low"], low)
            b["bar_count"] += 1

        self._last_session = current_session
        return completed_session

    def reset(self) -> None:
        """Force reset between runs."""
        self._trading_date = None
        self._building.clear()
        self._completed.clear()
        self._last_session = None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _classify_time(self, t: time) -> Optional[str]:
        """Classify an ET time into a session name."""
        # Asian: 18:00 to 03:00 (spans midnight)
        if t >= time(18, 0) or t < time(3, 0):
            return "asian"
        # London: 03:00 to 08:00
        if time(3, 0) <= t < time(8, 0):
            return "london"
        # Pre-market gap: 08:00 to 09:30 — not a session, skip
        if time(8, 0) <= t < time(9, 30):
            return None
        # NY: 09:30 to 16:00
        if time(9, 30) <= t < time(16, 0):
            return "ny"
        # Post-market: 16:00 to 18:00 — not a session
        return None

    def _freeze(self, session_name: str) -> None:
        """Freeze a building session into a completed range."""
        b = self._building[session_name]
        if b["high"] <= b["low"]:
            return  # degenerate
        self._completed[session_name] = SessionRangeState(
            session_name=session_name,
            range_high=b["high"],
            range_low=b["low"],
            session_date=self._trading_date,
        )
        logger.debug(
            "Session range frozen: %s date=%s high=%.4f low=%.4f bars=%d",
            session_name,
            self._trading_date,
            b["high"],
            b["low"],
            b["bar_count"],
        )
