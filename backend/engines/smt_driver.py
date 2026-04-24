"""SMT Cross-Index Driver — bridges SMTCrossIndexTracker to the engine pipeline.

Mirrors the `Aplus01Driver` pattern (stateful orchestrator between feature-
level trackers and the setup_engine_v2 bar-loop), but operates on a **pair**
(SPY, QQQ) rather than per-symbol. When the tracker emits, the driver
returns a synthetic `ICTPattern(pattern_type='smt_cross_index_sequence')`
carrying the SMT signal context + `smt_completion_target` in `details`.

Integration with setup_engine_v2 :
  - The emitted ICTPattern's `symbol` = lagging symbol (QQQ or SPY).
  - `direction` = "bullish" | "bearish" (maps to LONG | SHORT).
  - `price_level` = entry reference (lagging last close).
  - `details["smt_completion_target"]` = TP target fed to tp_resolver via
    the playbook's `tp_logic_params["smt_completion_price"]` at setup-build
    time (setup_engine_v2 knows how to read from synthetic pattern details).
  - Playbook YAML matches via `required_signals: ['SMT_CROSS_INDEX@5m']`
    (maps through playbook_loader's `type_map` to 'smt_cross_index_sequence').

State machine per-pair lives in SMTCrossIndexTracker. The driver holds :
  - one SMTCrossIndexTracker(pair)
  - one PoolFreshnessTracker per symbol of the pair (bootstrap HTF 4h/1h
    pool candidates)
  - rolling k3 pivot cache per symbol (computed from 5m bars)
  - HTF bias snapshot cache per symbol (from §0.B.3)

This driver is stateless beyond the trackers. Per-trading-day reset is
handled automatically by each inner tracker's rollover logic (18:00 ET).
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Iterable, List, Literal, Optional, Sequence, Tuple

from engines.features.htf_bias_structure import HTFBiasResult
from engines.features.pool_freshness_tracker import (
    Pool,
    PoolFreshnessTracker,
    PoolKind,
    PoolTF,
)
from engines.features.smt_cross_index_tracker import (
    SMTCrossIndexTracker,
    SMTSetupCandidate,
    SMTState,
    TrackerOutput,
)
from engines.patterns.fvg_stacking import check_pre_sweep_gate
from engines.patterns.smt_htf import (
    SMTInputs,
    classify_last_pivot,
    detect_smt_divergence,
)
from models.setup import ICTPattern

logger = logging.getLogger(__name__)


class SMTDriver:
    """Pair-level orchestrator producing synthetic ICTPatterns on SMT emit.

    Usage per backtest bar :
        # 1. Register new HTF pools when 4h / 1h bars close.
        driver.on_htf_bar_close(symbol, tf, bar_high, bar_low, bar_close_ts)

        # 2. Each 5m bar, feed sweep detection + pivot updates.
        emission = driver.on_5m_bar(
            symbol_bars={'SPY': spy_bars_5m, 'QQQ': qqq_bars_5m},
            bar_ts=current_ts,
            pivots_k3={'SPY': spy_k3, 'QQQ': qqq_k3},
            htf_bias={'SPY': spy_bias, 'QQQ': qqq_bias},
            attached_swing_prices={'SPY': ..., 'QQQ': ...},
            macro_kill_zone_pass=<bool>,
            daily_profile_allowed=<bool>,
            pre_sweep_window_minutes=30,
        )
        if emission is not None:
            # Synthetic ICTPattern ready for setup_engine_v2.ict_patterns.
            ict_patterns.append(emission)

    Emit cardinality : the tracker emits at most once between IDLE resets
    (linear state machine). Callers should invoke `driver.consume_emission()`
    after using the ICTPattern to reset the tracker for the next cycle.
    """

    def __init__(
        self,
        pair: Tuple[str, str] = ("SPY", "QQQ"),
        pre_sweep_window_minutes: int = 30,
    ) -> None:
        self._pair = pair
        self._tracker = SMTCrossIndexTracker(pair=pair)
        self._freshness: Dict[str, PoolFreshnessTracker] = {
            sym: PoolFreshnessTracker(symbol=sym) for sym in pair
        }
        self._pre_sweep_window_minutes = pre_sweep_window_minutes
        self._emit_count = 0
        self._last_emission: Optional[ICTPattern] = None
        # Instrumentation counters (persisted to debug_counts by BacktestEngine).
        # Written once per on_5m_bar call to localize where signals drop out.
        self._counters: Dict[str, int] = {
            "pair_tick_fired": 0,
            "htf_pool_sweeped": 0,
            "state_pool_sweeped": 0,
            "state_structure_observable": 0,
            # Granular divergence-classification outcomes (v4.0 post-v2 smoke
            # 2026-04-24) : localize why signal_detected=0 despite
            # state_structure_observable>0. Each STRUCTURE_OBSERVABLE tick
            # falls into exactly one bucket below.
            "class_both_none": 0,              # at least one side classify None
            "class_same_direction": 0,         # both HH, both LL, both LH, both HL
            "class_mixed_non_canonical": 0,    # e.g. HH + HL (both bullish-biased)
            "class_canonical_divergent": 0,    # LH+HH or HL+LL (SMT pattern!)
            "class_canonical_no_attached": 0,  # canonical but leading attached_swing None
            "signal_detected": 0,
            "state_smt_signal_emitted": 0,
            "gate_macro_kill_zone_pass": 0,
            "gate_daily_profile_pass": 0,
            "gate_pre_sweep_pass": 0,
            "gate_bias_aligned_pass": 0,
            "emit_setup": 0,
        }

    # -- HTF pool bootstrap ---------------------------------------------

    def on_htf_bar_close(
        self,
        symbol: str,
        tf: str,  # "4h" or "1h"
        bar_high: float,
        bar_low: float,
        bar_close_ts: datetime,
    ) -> None:
        """Register the closing HTF bar's high/low as new fresh pools.

        HTF pools are the primary pool source for SMT (canon TRUE `pKIo-aVic-c`).
        The pool id embeds tf + kind + timestamp for uniqueness.
        """
        if symbol not in self._pair or tf not in ("4h", "1h"):
            return
        tracker = self._freshness[symbol]
        ts_iso = bar_close_ts.isoformat()
        high_pool = Pool(
            id=f"{symbol}_{tf}_high_{ts_iso}",
            tf=tf,
            kind=PoolKind.HIGH.value,
            price=bar_high,
            created_ts=bar_close_ts,
        )
        low_pool = Pool(
            id=f"{symbol}_{tf}_low_{ts_iso}",
            tf=tf,
            kind=PoolKind.LOW.value,
            price=bar_low,
            created_ts=bar_close_ts,
        )
        tracker.register_pool(high_pool)
        tracker.register_pool(low_pool)

    # -- 5m bar tick ----------------------------------------------------

    def on_5m_bar(
        self,
        *,
        bar_ts: datetime,
        symbol_bars: Dict[str, Any],  # latest 5m bar per symbol (.high/.low/.close)
        pivots_k3: Dict[str, Sequence[Any]],  # k3 pivots per symbol up to bar_ts
        last_closes: Dict[str, float],
        attached_swing_prices: Dict[str, Optional[float]],
        htf_bias: Dict[str, Optional[HTFBiasResult]],
        macro_kill_zone_pass: bool,
        daily_profile_allowed: bool,
    ) -> Optional[ICTPattern]:
        """Per-5m bar tick. Returns synthetic ICTPattern on emit, else None.

        The driver runs these substeps in order :
          1. Update PoolFreshnessTracker for each symbol with the current
             bar ; collect swept pool ids.
          2. Forward HTF sweeps (4h / 1h only) to the SMT tracker.
          3. If tracker in POOL_SWEEPED and enough post-sweep structure
             observed, advance to STRUCTURE_OBSERVABLE.
          4. If tracker in STRUCTURE_OBSERVABLE, run detect_smt_divergence.
             If a signal emits, forward to tracker.
          5. Tick bar (timeouts, rollover).
          6. If SMT_SIGNAL_EMITTED, try gates + emit setup.
          7. On EMIT_SETUP, produce synthetic ICTPattern.
        """
        self._counters["pair_tick_fired"] += 1

        # 1. Sweep detection per symbol.
        swept_by_symbol: Dict[str, List[str]] = {}
        pool_state_by_id: Dict[str, Pool] = {}
        for sym in self._pair:
            bar = symbol_bars.get(sym)
            if bar is None:
                swept_by_symbol[sym] = []
                continue
            swept_ids = self._freshness[sym].update(
                bar_ts, float(bar.high), float(bar.low)
            )
            swept_by_symbol[sym] = swept_ids
            # Cache a snapshot of swept pool objects for downstream bootstrap.
            for pid in swept_ids:
                p = self._freshness[sym].get_pool(pid)
                if p is not None:
                    pool_state_by_id[pid] = p

        # 2. Forward HTF sweep events to SMT tracker.
        # Count any HTF (4h/1h) sweep regardless of whether tracker is idle
        # (diagnostic — shows how often HTF pools get touched in the corpus).
        for sym in self._pair:
            for pid in swept_by_symbol.get(sym, []):
                p = pool_state_by_id.get(pid)
                if p is None or p.tf not in ("4h", "1h"):
                    continue
                self._counters["htf_pool_sweeped"] += 1
        if self._tracker.state == SMTState.IDLE:
            for sym in self._pair:
                for pid in swept_by_symbol.get(sym, []):
                    p = pool_state_by_id.get(pid)
                    if p is None or p.tf not in ("4h", "1h"):
                        continue
                    self._tracker.on_pool_sweeps(
                        swept_pool_ids=[pid], symbol=sym, tf=p.tf, bar_ts=bar_ts
                    )
                    if self._tracker.state == SMTState.POOL_SWEEPED:
                        self._counters["state_pool_sweeped"] += 1
                        break
                if self._tracker.state == SMTState.POOL_SWEEPED:
                    break

        # 3. Advance to STRUCTURE_OBSERVABLE if enough post-sweep structure.
        if self._tracker.state == SMTState.POOL_SWEEPED:
            sweep_ts = self._tracker.pool_sweep_ts
            if sweep_ts is not None and self._has_structure_post_sweep(
                pivots_k3, sweep_ts
            ):
                self._tracker.advance_to_structure_observable(bar_ts)
                if self._tracker.state == SMTState.STRUCTURE_OBSERVABLE:
                    self._counters["state_structure_observable"] += 1

        # 4. Run SMT detection.
        if self._tracker.state == SMTState.STRUCTURE_OBSERVABLE:
            a_sym, b_sym = self._pair
            a_inputs = SMTInputs(
                symbol=a_sym,
                pivots_k3=pivots_k3.get(a_sym, []),
                last_close=last_closes.get(a_sym, 0.0),
                attached_swing_price=attached_swing_prices.get(a_sym),
            )
            b_inputs = SMTInputs(
                symbol=b_sym,
                pivots_k3=pivots_k3.get(b_sym, []),
                last_close=last_closes.get(b_sym, 0.0),
                attached_swing_price=attached_swing_prices.get(b_sym),
            )

            # Granular classification bucket counter (diagnostic).
            sweep_ts = self._tracker.pool_sweep_ts
            a_class = classify_last_pivot(a_inputs.pivots_k3, since_ts=sweep_ts)
            b_class = classify_last_pivot(b_inputs.pivots_k3, since_ts=sweep_ts)
            canonical_pairs = ({"LH", "HH"}, {"HL", "LL"})
            if a_class is None or b_class is None:
                self._counters["class_both_none"] += 1
            elif a_class == b_class:
                self._counters["class_same_direction"] += 1
            elif {a_class, b_class} in canonical_pairs:
                # Canonical divergence pattern detected.
                leading = a_inputs if a_class in ("LH", "HL") else b_inputs
                if leading.attached_swing_price is None:
                    self._counters["class_canonical_no_attached"] += 1
                else:
                    self._counters["class_canonical_divergent"] += 1
            else:
                self._counters["class_mixed_non_canonical"] += 1

            signal = detect_smt_divergence(
                a=a_inputs, b=b_inputs,
                detection_ts=bar_ts,
                sweep_ts=self._tracker.pool_sweep_ts,
            )
            if signal is not None:
                self._counters["signal_detected"] += 1
                self._tracker.on_signal(signal, bar_ts)
                if self._tracker.state == SMTState.SMT_SIGNAL_EMITTED:
                    self._counters["state_smt_signal_emitted"] += 1

        # 5. Tick bar (timeouts + rollover).
        tick_out = self._tracker.on_bar_tick(bar_ts)
        if tick_out.reason is not None:
            # Timeout or rollover caused a reset — no emission this bar.
            return None

        # 6. Try setup emission.
        if self._tracker.state != SMTState.SMT_SIGNAL_EMITTED:
            return None

        # §0.5bis entrée #1 v4.0 refactor 2026-04-24 : bypass pre_sweep_gate
        # for SMT path. The pre_sweep_gate was spec'd for IFVG entry (TRUE
        # `BdBxXKGWVjk` : IFVG flip requires fresh pool sweep within N min).
        # SMT divergence has a fundamentally different horizon :
        #   POOL_SWEEPED timeout 150 min + STRUCTURE_OBSERVABLE 100 min +
        #   SMT_SIGNAL_EMITTED 30 min = 280 min total state machine lifecycle.
        # The tracker's internal timeouts ALREADY enforce freshness via state
        # chain expiry — adding pre_sweep_gate on top is redundant and
        # architecturally blocks emission for SMT (empirically : v4+v5 smoke
        # nov_w4 produced signal_detected=1 but gate_pre_sweep_pass=0).
        # We pass True unconditionally to try_emit_setup. The
        # check_pre_sweep_gate helper remains available in fvg_stacking.py
        # for IFVG-specific playbooks that need it.
        pre_sweep_ok = True

        # HTF bias alignment : use the leading symbol's bias (non-neutral
        # required — SMT divergence against a directional macro bias is the
        # canonical reversal signal). _is_bias_aligned_for_signal reads the
        # tracker's locked signal to know which symbol is leading.
        bias_aligned = self._is_bias_aligned_for_signal(htf_bias)

        # Count individual gate outcomes BEFORE the AND-combination in try_emit_setup,
        # to allow localization of blocking gate(s).
        if macro_kill_zone_pass:
            self._counters["gate_macro_kill_zone_pass"] += 1
        if daily_profile_allowed:
            self._counters["gate_daily_profile_pass"] += 1
        if pre_sweep_ok:
            self._counters["gate_pre_sweep_pass"] += 1
        if bias_aligned:
            self._counters["gate_bias_aligned_pass"] += 1

        out = self._tracker.try_emit_setup(
            bar_ts=bar_ts,
            htf_bias_aligned=bias_aligned,
            macro_kill_zone_pass=macro_kill_zone_pass,
            daily_profile_allowed=daily_profile_allowed,
            pre_sweep_gate_pass=pre_sweep_ok,
        )

        # 7. Synthesize ICTPattern on emit.
        if out.state != SMTState.EMIT_SETUP or out.setup is None:
            return None
        self._counters["emit_setup"] += 1
        return self._synthesize_ict_pattern(out.setup, bar_ts)

    def _synthesize_ict_pattern(
        self, setup: SMTSetupCandidate, bar_ts: datetime
    ) -> ICTPattern:
        direction_word = "bullish" if setup.direction == "LONG" else "bearish"
        pattern = ICTPattern(
            symbol=setup.symbol,
            timeframe="5m",
            pattern_type="smt_cross_index_sequence",
            direction=direction_word,
            price_level=float(setup.entry_reference_price),
            details={
                "leading_symbol": setup.leading_symbol,
                "lagging_symbol": setup.symbol,
                "divergence_type": setup.divergence_type,
                "smt_completion_target": float(setup.smt_completion_price),
                "pool_sweep_tf": setup.pool_sweep_tf,
                "pool_sweep_ts": setup.pool_sweep_ts.isoformat(),
                "signal_ts": setup.signal_ts.isoformat(),
                "emit_ts": bar_ts.isoformat(),
            },
            strength=1.0,
            confidence=0.95,
        )
        self._emit_count += 1
        self._last_emission = pattern
        logger.info(
            "[SMT] emit %s dir=%s entry=%.4f target=%.4f (leading=%s, tf=%s)",
            setup.symbol, setup.direction,
            setup.entry_reference_price, setup.smt_completion_price,
            setup.leading_symbol, setup.pool_sweep_tf,
        )
        return pattern

    def consume_emission(self) -> None:
        """Called after the caller has consumed the emitted pattern.

        Resets tracker to IDLE (preserves trading date — retrigger allowed
        intraday on another sweep).
        """
        self._tracker.reset_after_emit()
        self._last_emission = None

    # -- Helpers --------------------------------------------------------

    @staticmethod
    def _has_structure_post_sweep(
        pivots_k3: Dict[str, Sequence[Any]],
        sweep_ts: datetime,
    ) -> bool:
        """True iff each symbol has enough post-sweep structure for
        classify_last_pivot() to return HH/LH/HL/LL (i.e. ≥ 2 same-type
        pivots in the post-sweep window).

        The function needs **2 high pivots OR 2 low pivots** per symbol
        because `classify_last_pivot` compares the latest pivot against
        the previous pivot of the same type. A single high + single low
        is insufficient (cannot classify relative to a predecessor of
        the same type).

        Fix 2026-04-24 post-smoke instrumentation (nov_w4 counter
        state_structure_observable=6 but signal_detected=0 → prior
        permissive criterion ≥1 high AND ≥1 low advanced prematurely,
        then classify_last_pivot returned None on both sides).
        """
        for sym_pivots in pivots_k3.values():
            post = [p for p in sym_pivots if p.timestamp >= sweep_ts]
            highs = [p for p in post if p.type == "high"]
            lows = [p for p in post if p.type == "low"]
            # Need ≥2 of AT LEAST one type (either 2 highs or 2 lows).
            if len(highs) < 2 and len(lows) < 2:
                return False
        return True

    def _is_bias_aligned_for_signal(
        self, htf_bias: Dict[str, Optional[HTFBiasResult]]
    ) -> bool:
        """Gate helper : leading symbol's HTF bias.

        v8.2 relaxation (2026-04-24, post 4w Stage 1 diagnostic) : accept
        neutral HTF bias. Rationale :
          - TimeframeAggregator produces sparse 4h bars (30 bars even with
            3 months 1m corpus) → k9 pivots routinely 0, k3 2-4.
          - compute_htf_bias requires ≥2H + ≥2L → typically returns
            "insufficient" / "neutral" on current infra.
          - Gate_bias_aligned_pass was 0 across 4 weeks Stage 1 v8 run.
          - Architectural Cas A (infra gap : HTF aggregator short window).
        Gate now : require last_signal non-None AND HTFBiasResult non-None
        for the leading symbol. Doesn't require non-neutral — the SMT signal
        itself carries directional info via the leading/lagging identification.
        """
        last_sig_result = self._tracker._data.last_signal  # internal — ok for driver
        if last_sig_result is None:
            return False
        leading_bias = htf_bias.get(last_sig_result.leading_symbol)
        if leading_bias is None:
            return False
        # Accept any HTFBiasResult (including neutral) — gate reduced to
        # "bias computable" rather than "bias directional".
        return True

    # -- Introspection --------------------------------------------------

    @property
    def state(self) -> SMTState:
        return self._tracker.state

    @property
    def emit_count(self) -> int:
        return self._emit_count

    @property
    def last_emission(self) -> Optional[ICTPattern]:
        return self._last_emission

    def get_counters(self) -> Dict[str, int]:
        """Return a copy of instrumentation counters. Called by BacktestEngine
        at end-of-run to persist into debug_counts for offline localization."""
        return dict(self._counters)

    def reset(self) -> None:
        self._tracker = SMTCrossIndexTracker(pair=self._pair)
        self._freshness = {
            sym: PoolFreshnessTracker(symbol=sym) for sym in self._pair
        }
        self._emit_count = 0
        self._last_emission = None
