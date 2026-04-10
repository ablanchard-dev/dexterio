# FEATURE DICTIONARY

## Market context features
- `daily_structure`, `h4_structure`, `h1_structure`: HTF trend labels from structure detection.
- `bias`, `bias_confidence`: directional context from HTF voting.
- `session_profile`: profile class (1/2/3 model in market state engine).
- `day_type`: trend/manipulation_reversal/range/unknown.

## Liquidity features
- `pdh`, `pdl`, `asia_high`, `asia_low`, `london_high`, `london_low`, `weekly_high`, `weekly_low`.
- `equal_highs`, `equal_lows`, `pivot_high`, `pivot_low`.
- `swept` flag and `sweep_details` on liquidity levels.

## ICT/pattern features
- ICT `pattern_type`: `bos`, `fvg`, `smt`, `choch`, `ifvg`, `order_block`, `breaker_block`, `equilibrium` (depending on detector path).
- Candle pattern families: engulfing, pin_bar, doji, morning/evening star, etc.

## Setup features
- `quality`: A+/A/B/C.
- `final_score`, component scores (`ict_score`, `pattern_score`, `playbook_score`).
- `confluences_count`.
- `playbook_name`, `match_score`, `match_grade`, `grade_thresholds`.
- Trade recommendation fields: direction, entry, stop, TPs, RR.

## Risk features
- `current_risk_pct`, `risk_tier_state`.
- `daily_pnl_r`, `max_drawdown_r`, `disabled_playbooks`.
- cooldown/session counters and cap states.

## Execution features
- Trade state: `open/pending/closed`.
- lifecycle metrics: `r_multiple`, `pnl_dollars`, `duration_minutes`, `exit_reason`.
- paper runtime status: `running`, `execution_backend`, `live_trading_enabled`.

