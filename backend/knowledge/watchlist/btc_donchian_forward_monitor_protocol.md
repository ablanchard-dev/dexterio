# BTC Donchian Forward-Monitor Protocol

**Status** : WATCHLIST non-promoted forward-only
**Created** : 2026-04-27
**Source backtest** : `data/backtest_results/s3_t4_donchian_breakout_verdict.md` (S+3-bis T4)

## Backtest summary (frozen, NO re-backtest)

- **Stratégie** : Donchian breakout daily 20d high / 10d low
- **Asset** : BTCUSDT spot
- **Backtest 6.5y** (2019-06 → 2025-11, 2375 bars)
- **Sharpe** : 0.761 vs BTC buy-hold 0.744 (beat by +0.017 marginal)
- **CAGR** : 32.66% vs BTC BH 43.75% (loses 11% CAGR for risk reduction)
- **Max DD** : -54.3% vs BTC BH -76.6% (DD divisé par 1.4×)
- **Calmar** : 0.60 vs BTC BH 0.57 (légèrement meilleur risk-adjusted)
- **Sub-sample** : ΔSharpe -0.05 (stable cross-régime, atypique sur ce projet)
- **Permutation 500 iter** : real 0.761 vs perm mean 0.45, **z-score +1.23**, **p-value 0.12**

## Pourquoi WATCHLIST et non promoted

Per discipline plan S+3-bis : "Borderline (Sharpe 0.5-0.8, p>0.10) → ARCHIVE strict, pas tuning". p=0.12 > 0.10 gate = pas significatif.

Mais z-score +1.23 = signal réel mesuré, pas zéro. Le signal n'est juste pas assez fort statistiquement pour franchir le seuil discipline.

## Forward-monitor protocol (zero capital, no re-backtest)

### Setup initial (one-time)

État Donchian au 2025-11-30 (last training date) :
- Position : à recalculer en début monitoring
- 20d high : à recalculer
- 10d low : à recalculer

### Daily monitoring loop (forward 6 mois)

Chaque jour de trading (Mon-Sun pour BTC 24/7) :

1. **Fetch** BTC daily close via Binance public API (`https://api.binance.com/api/v3/klines`)
2. **Compute** rolling 20d max(close) and 10d min(close)
3. **Apply rule** :
   - If `current_close > prior_20d_max` AND `position == 0` → **virtual entry** (no real trade)
   - If `current_close < prior_10d_min` AND `position == 1` → **virtual exit**
4. **Log** : date, close, position, virtual_pnl_R, eq_curve

### Ledger fields per day

```json
{
  "date": "YYYY-MM-DD",
  "btc_close": float,
  "rolling_20d_high": float,
  "rolling_10d_low": float,
  "position": 0 | 1,
  "position_change": "ENTRY" | "EXIT" | "HOLD",
  "daily_ret": float,
  "equity_curve": float,
  "drawdown_from_peak": float
}
```

Fichier : `results/watchlist/btc_donchian_forward_ledger.parquet`

### 6-month checkpoint criteria

Après 6 mois forward (target : 2026-10-30) :

| Metric | PASS threshold | KILL threshold |
|---|---:|---:|
| Forward Sharpe (6m × √2 = annualized) | ≥ 0.5 | < 0.0 |
| Forward CAGR vs BTC BH | competitive | clearly lose |
| Forward max DD | < 30% | > 50% |
| Number of round-trips | 3-10 (similar to backtest density) | 0 or > 20 |
| Permutation forward (500 iter) | p < 0.10 | p > 0.20 |

**Si PASS** : reconsider Stage 2 backtest extension + Sprint 4 paper deploy candidate.
**Si KILL ou marginal** : ARCHIVE final, document "forward-validated null", remove from watchlist.

### Anti-data-mining

- **No re-backtest** during monitoring period (would be hindsight bias)
- **No parameter tuning** (frozen 20/10 Donchian)
- **No scope expansion** to other crypto assets (this is BTC-specific test)
- If forward results are mixed, do NOT add new criteria — apply pre-declared thresholds only

### Ownership and review

- Forward ledger updated daily (automated fetch + append)
- Mid-checkpoint (3 months) : informational only, no decision
- Final checkpoint (6 months) : binary decision PASS/KILL/MARGINAL per criteria above

### Honnêteté méthodologique

Cette watchlist documente que **un signal réel mais non-significatif** existait sur BTC Donchian dans le backtest. Le forward-monitor est un test honnête "le signal continue-t-il post-decision-date ?" sans biais hindsight.

Si le signal continue forward avec Sharpe ≥ 0.5 sur 6m, c'est une **preuve out-of-sample** plus forte que le backtest in-sample. Si pas, le verdict ARCHIVE est confirmé sans regret.

**Aucun trade réel ne sera placé pendant cette période de monitoring.** Zero capital risk. Pure validation forward.
