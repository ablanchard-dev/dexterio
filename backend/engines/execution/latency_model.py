"""Latency-model abstraction for execution engine.

§0.7 G2 of plan v3.1.2 — models broker/network latency between signal trigger and
order fill. Pairs with §0.7 G1 `ConservativeFillModel` to form the minimum realism
stack required before §0.5bis entrée #1 runs (Aplus_01 Family A v2 TRUE HTF).

Three implementations, same Protocol:

- `IdealLatency`: 0 ms. Byte-identical to pre-G2 behavior.
- `RealisticLatency(ms=200, jitter=50, seed=42)`: samples a latency in
  `[ms - jitter, ms + jitter]` per order (deterministic via seed).
- `IBKRLatency`: placeholder for empirical calibration post-Sprint 4 paper
  (inherits RealisticLatency defaults until real broker data is available).

Design notes:

- On 1m bars the 200±50 ms figure is structurally a no-op for bar-granular
  shift (200 ms << 60 000 ms bar duration). `shift_bars()` returns 0 in that
  regime. The scaffold still logs `latency_ms_simulated` on every trade so the
  backtest→paper→live reconcile has a comparable series (paper/live will log
  actual broker round-trip latency on the same field).
- For high-latency fixtures (tick bars, congested routing, ≥ bar duration),
  `shift_bars(bar_duration_seconds)` returns the integer bar shift to apply.
  Wired consumers (ExecutionEngine / BacktestEngine fill path) can use this to
  advance the target fill bar accordingly.

Interaction with §0.6.0 metrics substitution: G2 does not alter E[R] on 1m
corpus (no bar shift). The budget slippage re-quantification is deferred to
G3 (spread bps) where realistic spread + G1 Conservative + G2 latency scaffold
are reconciled together on calib_corpus_v1.
"""
from __future__ import annotations

import random
from typing import Optional, Protocol


class LatencyModel(Protocol):
    """Contract for order-fill latency simulation.

    `sample_ms()` is called once per `place_order` and cached (`_last_sample`
    on stateful models). `shift_bars(bar_duration_seconds)` returns the integer
    number of bars the last-sampled latency crosses, enabling bar-granular
    shift of the target fill bar in ExecutionEngine.
    """

    def sample_ms(self) -> float: ...
    def shift_bars(self, bar_duration_seconds: float) -> int: ...


class IdealLatency:
    """0 ms latency. Reproduces pre-G2 ExecutionEngine behavior byte-identically."""

    def sample_ms(self) -> float:
        return 0.0

    def shift_bars(self, bar_duration_seconds: float) -> int:
        return 0


class RealisticLatency:
    """Samples a latency in [ms - jitter, ms + jitter] per call.

    Default `ms=200, jitter=50` reflects typical retail broker round-trip to
    a US equities matching engine (cf. plan §3.2.2). Seeded for deterministic
    test reproduction.
    """

    def __init__(
        self,
        ms: float = 200.0,
        jitter: float = 50.0,
        seed: Optional[int] = 42,
    ):
        if ms < 0:
            raise ValueError(f"ms must be >= 0, got {ms}")
        if jitter < 0:
            raise ValueError(f"jitter must be >= 0, got {jitter}")
        if jitter > ms:
            # Clamp via lower bound only — allow jitter > ms but floor sample at 0
            pass
        self.ms = float(ms)
        self.jitter = float(jitter)
        self._rng = random.Random(seed)
        self._last_sample: Optional[float] = None

    def sample_ms(self) -> float:
        low = max(0.0, self.ms - self.jitter)
        high = self.ms + self.jitter
        self._last_sample = self._rng.uniform(low, high)
        return self._last_sample

    def shift_bars(self, bar_duration_seconds: float) -> int:
        if bar_duration_seconds <= 0:
            raise ValueError(
                f"bar_duration_seconds must be > 0, got {bar_duration_seconds}"
            )
        sample = self._last_sample if self._last_sample is not None else self.sample_ms()
        return int(sample / (bar_duration_seconds * 1000.0))


class IBKRLatency(RealisticLatency):
    """Placeholder for IBKR-calibrated latency (post-Sprint 4 paper).

    Keeps RealisticLatency defaults until empirical calibration data is
    available from the paper/live adapter. Distinct class so consumers can
    pin on it via isinstance checks once calibrated.
    """

    pass


__all__ = ["LatencyModel", "IdealLatency", "RealisticLatency", "IBKRLatency"]
