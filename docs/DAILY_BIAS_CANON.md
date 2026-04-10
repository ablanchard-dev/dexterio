# DAILY BIAS CANON

## Implemented bias model (repo truth)

### B1 - HTF structure voting
- Source: `backend/engines/market_state.py`
- Logic: bias is derived from daily/h4/h1 structure scores.
  - daily weight 3
  - h4 weight 2
  - h1 weight 1
- Output: `bullish` / `bearish` / `neutral` + confidence.
- Confidence: high

### B2 - Session profile classifier exists
- Source: `market_state.py::classify_session_profile`
- Logic: 3-profile model implemented:
  1. consolidation -> manipulation + reversal
  2. manipulation (no trend) -> reversal
  3. manipulation + trend -> continuation
- Confidence: medium (inputs currently partly placeholder in runtime call).

### B3 - HTF levels included
- Source: `market_state.py::mark_htf_levels`
- Levels tracked: PDH/PDL, Asia/London highs/lows, weekly highs/lows.
- Confidence: high

## Corpus-aligned bias hypotheses (not fully proven in code)
- Draw-on-liquidity hierarchy (session highs/lows, prior day, 1H/4H).
- Sweep state (swept vs untapped) as a directional narrative pivot.
- These are partially represented via liquidity engine + playbooks but not yet a single dedicated `BiasEngine` output schema.

## Canonical daily-bias output schema (recommended target)
```json
{
  "primary_bias": "bullish|bearish|neutral",
  "confidence": 0.0,
  "htf_context": {
    "daily_structure": "uptrend|downtrend|range|unknown",
    "h4_structure": "uptrend|downtrend|range|unknown",
    "h1_structure": "uptrend|downtrend|range|unknown"
  },
  "liquidity_map": {
    "key_levels": ["PDH","PDL","ASIA_HIGH","ASIA_LOW","LONDON_HIGH","LONDON_LOW"],
    "swept_levels": [],
    "untapped_targets": []
  },
  "session_profile": 1,
  "invalidation": "text",
  "no_trade_reasons": []
}
```

## Ambiguities to resolve
- Which source is authoritative for profile definitions when transcript and code diverge.
- Exact precedence among liquidity draws when multiple targets conflict.

