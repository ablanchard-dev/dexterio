"""Pool Freshness Tracker — §0.B.7 brique canon (prérequis §0.B.1 tp_resolver upgrade).

Tracks per-symbol sweep/unswept state of candidate liquidity pools (BSL/SSL)
across multiple timeframes and sessions. Source TRUE `pKIo-aVic-c` +
MASTER ligne 21490-21552 : "freshness first" = non-sweeped dans sessions
précédentes + PM + London. TF hierarchy 4H > 1H > 15m > 5m > 1m.

A "pool" is a liquidity level where stops/orders cluster — typically a prior
high/low of a session or higher-TF swing. A pool is "swept" when a bar's range
crosses the pool price after its creation. A pool is "fresh" when it has
never been swept. Freshness is **the primary freshness condition** of canon
TP logic (TRUE `pKIo-aVic-c`): a previously-swept pool has already delivered
its liquidity and is no longer a high-quality draw.

Contract:
    tracker = PoolFreshnessTracker(symbol="SPY")
    tracker.register_pool(Pool(id="4h_high_...", tf="4h", kind="high",
                                price=..., created_ts=...))
    tracker.update(bar_ts, bar_high, bar_low)  # detects sweeps
    tracker.is_fresh(pool_id) -> bool  # never swept since creation
    tracker.is_unswept_since(pool_id, since_ts) -> bool
    tracker.get_fresh_pools(tf_filter=["4h","1h"], direction="short_target",
                             as_of=ts) -> list[Pool]
    tracker.mark_swept(pool_id, swept_ts)  # manual override (tests)

Reset: trading-day rollover 18:00 ET (same semantics as SessionRangeTracker).
This clears session-scoped pools (asian/london/premarket/prev_session); daily,
weekly, and longer-tf pools persist across days.

Notes:
- Pure logic, no I/O. Picklable for paper/live continuity.
- Caller (tp_resolver / htf_sweep detector) is responsible for registering
  pools at creation time. Tracker does not auto-discover pivots.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date, time, timedelta
from enum import Enum
from typing import Dict, Iterable, List, Optional, Sequence
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
_TRADING_DAY_ROLLOVER = time(18, 0)  # 18:00 ET (matches SessionRangeTracker)


class PoolKind(str, Enum):
    """BSL = buy-side liquidity = pool above price (highs). SSL = sell-side = lows."""

    HIGH = "high"
    LOW = "low"


class PoolTF(str, Enum):
    """Canonical TF labels. Higher-TF pools are prioritized per TRUE pKIo-aVic-c."""

    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    PREV_D = "prev_D"
    PREV_W = "prev_W"
    ASIAN = "asian"
    LONDON = "london"
    PREMARKET = "premarket"
    NY_SESSION = "ny_session"
    PREV_SESSION = "prev_session"


# Session-scoped TFs are wiped on trading-day rollover.
# Daily/weekly/hourly pools persist across days.
_SESSION_SCOPED_TFS: frozenset[str] = frozenset({
    PoolTF.ASIAN.value,
    PoolTF.LONDON.value,
    PoolTF.PREMARKET.value,
    PoolTF.NY_SESSION.value,
    PoolTF.PREV_SESSION.value,
})


@dataclass
class Pool:
    """Immutable descriptor of a liquidity pool candidate."""

    id: str
    tf: str  # PoolTF value
    kind: str  # PoolKind value (high/low)
    price: float
    created_ts: datetime
    session_created: Optional[str] = None  # e.g. "asian", "london" — diagnostic
    swept_ts: Optional[datetime] = None  # None → unswept

    @property
    def is_swept(self) -> bool:
        return self.swept_ts is not None

    @property
    def direction_target(self) -> str:
        """Which entry direction this pool targets as TP.

        HIGH pool (BSL above) → target for LONG entries (price reaches up to take it out).
        LOW pool (SSL below) → target for SHORT entries.
        """
        return "long_target" if self.kind == PoolKind.HIGH.value else "short_target"


def compute_trading_date(ts: datetime) -> date:
    """Trading-day ET convention: 18:00 ET rollover.

    Times at or after 18:00 ET belong to the *next* calendar date's trading day.
    Times before 18:00 ET belong to the current calendar date.
    """
    ts_et = ts.astimezone(ET) if ts.tzinfo else ts.replace(tzinfo=ET)
    if ts_et.time() >= _TRADING_DAY_ROLLOVER:
        return ts_et.date() + timedelta(days=1)
    return ts_et.date()


def _bar_sweeps_pool(pool: Pool, bar_ts: datetime, bar_high: float, bar_low: float) -> bool:
    """True iff the bar's range crosses the pool price after creation.

    HIGH pool: bar_high > pool.price (price reached up and took the liquidity).
    LOW pool:  bar_low  < pool.price.

    Sweeps at the exact price (equality) do NOT count — a touch without
    penetration is not a sweep (canon TRUE: sweep = penetration + reaction).
    Reaction confirmation is enforced downstream by `tp_resolver`.
    """
    if bar_ts <= pool.created_ts:
        return False  # pool not yet armed at this bar
    if pool.kind == PoolKind.HIGH.value:
        return bar_high > pool.price
    return bar_low < pool.price


class PoolFreshnessTracker:
    """Per-symbol state machine tracking pool freshness over time.

    Owns a dict of Pool objects keyed by pool.id. Updates via `update()` with
    each bar; queries via `is_fresh()` / `get_fresh_pools()` etc.
    """

    def __init__(self, symbol: str) -> None:
        self._symbol = symbol
        self._pools: Dict[str, Pool] = {}
        self._trading_date: Optional[date] = None

    @property
    def symbol(self) -> str:
        return self._symbol

    def register_pool(self, pool: Pool) -> None:
        """Register a new pool candidate.

        If a pool with the same id already exists, it is replaced (caller's
        responsibility to avoid id collisions across sessions — convention is
        to embed created_ts in id).
        """
        self._pools[pool.id] = pool

    def get_pool(self, pool_id: str) -> Optional[Pool]:
        return self._pools.get(pool_id)

    def is_fresh(self, pool_id: str) -> bool:
        """True iff the pool exists and has never been swept."""
        pool = self._pools.get(pool_id)
        if pool is None:
            return False
        return not pool.is_swept

    def is_unswept_since(self, pool_id: str, since_ts: datetime) -> bool:
        """True iff the pool is either unswept OR was swept strictly before since_ts.

        Useful for gates like "pool must be unswept since session_prior open".
        Unknown pool id → False.
        """
        pool = self._pools.get(pool_id)
        if pool is None:
            return False
        if pool.swept_ts is None:
            return True
        return pool.swept_ts < since_ts

    def mark_swept(self, pool_id: str, swept_ts: datetime) -> bool:
        """Manually mark a pool swept (testing / replay).

        Returns True if the pool exists and was updated, False otherwise.
        Idempotent: marking an already-swept pool with an earlier timestamp
        keeps the *earliest* sweep timestamp recorded.
        """
        pool = self._pools.get(pool_id)
        if pool is None:
            return False
        if pool.swept_ts is None or swept_ts < pool.swept_ts:
            pool.swept_ts = swept_ts
        return True

    def get_fresh_pools(
        self,
        tf_filter: Optional[Sequence[str]] = None,
        direction: Optional[str] = None,
        as_of: Optional[datetime] = None,
    ) -> List[Pool]:
        """Return fresh (unswept) pools matching filters, ordered by TF priority.

        tf_filter : restrict to these TF labels (e.g. ["4h", "1h"]). None → all TFs.
        direction : "long_target" | "short_target" | None. Filters by kind.
        as_of     : if provided, also require pool.created_ts <= as_of (pool must
                    have existed at that time).

        Order: by TF hierarchy (4h > 1h > 15m > 5m > 1m; prev_W > prev_D;
        session-scoped last). Within same TF, by created_ts ascending (older
        pool = more "fresh" historically). Canon TRUE pKIo-aVic-c.
        """
        tf_set = frozenset(tf_filter) if tf_filter is not None else None
        results: List[Pool] = []
        for pool in self._pools.values():
            if pool.is_swept:
                continue
            if tf_set is not None and pool.tf not in tf_set:
                continue
            if direction is not None and pool.direction_target != direction:
                continue
            if as_of is not None and pool.created_ts > as_of:
                continue
            results.append(pool)
        results.sort(key=lambda p: (_tf_priority(p.tf), p.created_ts))
        return results

    def update(self, bar_ts: datetime, bar_high: float, bar_low: float) -> List[str]:
        """Feed a bar. Returns list of pool_ids that were swept by this bar.

        Side effect: marks each swept pool with swept_ts = bar_ts.
        Handles trading-day rollover (clears session-scoped pools).
        """
        self._maybe_rollover(bar_ts)
        just_swept: List[str] = []
        for pool in self._pools.values():
            if pool.is_swept:
                continue
            if _bar_sweeps_pool(pool, bar_ts, bar_high, bar_low):
                pool.swept_ts = bar_ts
                just_swept.append(pool.id)
        return just_swept

    def _maybe_rollover(self, bar_ts: datetime) -> None:
        """Clear session-scoped pools on trading-day rollover."""
        td = compute_trading_date(bar_ts)
        if self._trading_date is None:
            self._trading_date = td
            return
        if td == self._trading_date:
            return
        # New trading day: wipe session-scoped pools, keep longer-TF pools.
        self._pools = {
            pid: p for pid, p in self._pools.items()
            if p.tf not in _SESSION_SCOPED_TFS
        }
        self._trading_date = td

    def reset(self) -> None:
        """Full reset (tests / replay boundaries)."""
        self._pools.clear()
        self._trading_date = None

    def snapshot(self) -> Dict[str, Pool]:
        """Return a shallow copy of the pool dict (diagnostic / persistence)."""
        return dict(self._pools)

    def __len__(self) -> int:
        return len(self._pools)


# TF priority for get_fresh_pools ordering. Lower number = higher priority.
_TF_PRIORITY: Dict[str, int] = {
    PoolTF.PREV_W.value: 0,
    PoolTF.H4.value: 1,
    PoolTF.PREV_D.value: 2,
    PoolTF.H1.value: 3,
    PoolTF.M15.value: 4,
    PoolTF.M5.value: 5,
    PoolTF.M1.value: 6,
    PoolTF.LONDON.value: 7,
    PoolTF.ASIAN.value: 8,
    PoolTF.PREMARKET.value: 9,
    PoolTF.NY_SESSION.value: 10,
    PoolTF.PREV_SESSION.value: 11,
}


def _tf_priority(tf: str) -> int:
    return _TF_PRIORITY.get(tf, 99)
