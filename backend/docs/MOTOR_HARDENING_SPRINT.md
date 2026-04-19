# MOTOR HARDENING SPRINT — Roadmap

> **Objectif** : Transformer le moteur backtest en base de vérité robuste capable d'évaluer
> 20-50 playbooks en portefeuille. Aucune nouvelle stratégie tant que cette roadmap n'est pas
> validée par le gate final.
>
> **Date** : 2026-04-18
> **Contrainte honnête** : Avec du 1m OHLC, on ne pourra JAMAIS savoir :
> - L'ordre exact des ticks intra-barre (high d'abord ou low d'abord ?)
> - Le carnet d'ordres réel (profondeur, liquidité)
> - Le vrai bid/ask tick-by-tick
> - Le fill probability exact d'un limit order
>
> Ce qu'on PEUT atteindre : un moteur qui applique les bons coûts, refuse les trades
> irréalistes, et dont chaque résultat est auditable et explicable.

---

## A. Inventaire des défauts moteur ouverts

### AXE 1 — EXÉCUTION RÉALISTE

| ID | Défaut | Sévérité | État actuel | Fichier(s) |
|----|--------|----------|-------------|------------|
| E01 | **Intra-bar SL/TP conflict** : si les deux touchés, SL gagne toujours | HAUTE | Fix en cours (bar_open priority logic) mais pas testé | `paper_trading.py:259-330` |
| E02 | **Spread toujours flat** : 2 bps fixe, pas de variation session/volatilité | MOYENNE | `costs.py:167-205` — flat `fixed_bps` | `backtest/costs.py` |
| E03 | **Slippage plat** : 0.05% fixe, pas de modèle opening/closing volatilité | MOYENNE | `costs.py:123-164` — `pct` model | `backtest/costs.py` |
| E04 | **Pas de distinction MARKET/LIMIT/STOP** dans le modèle | HAUTE | Fix en cours (entry_type sur Setup, limit fill check) mais pas propagé | `models/setup.py`, `engine.py:972+` |
| E05 | **Double slippage potentiel** : entry slippage appliqué dans paper_trading.py ($0.02) ET dans costs.py (0.05%) | HAUTE | Garde `entry_slippage_applied` flag existe, mais la logique est fragile | `paper_trading.py:51-57`, `engine.py:2525` |
| E06 | **Limit order assume 100% fill** | HAUTE | Fix en cours (limit fill check) mais pas la probabilité de fill | `engine.py:972+` |
| E07 | **Pas de slippage sur SL** : exit à `trade.stop_loss` exact, pas de slippage | MOYENNE | `paper_trading.py:273` — close_price = trade.stop_loss exact | `paper_trading.py` |
| E08 | **Commission toujours active** : OK, mais jamais vérifiable post-hoc facilement | BASSE | Coûts exportés dans TradeResult mais pas résumés par type | `engine.py:2525+`, `models/backtest.py:99-112` |

### AXE 2 — PORTEFEUILLE RÉALISTE

| ID | Défaut | Sévérité | État actuel | Fichier(s) |
|----|--------|----------|-------------|------------|
| P01 | **Pas de max concurrent positions** | HAUTE | Fix en cours (MAX_CONCURRENT=5, per-symbol=2) mais pas testé | `risk_engine.py:142+` |
| P02 | **Pas de capital réservé** : chaque trade calcule son sizing comme si tout le capital est libre | HAUTE | Fix en cours (committed_capital) mais pas testé | `risk_engine.py:943+`, `models/risk.py:127+` |
| P03 | **Pas de corrélation inter-playbooks** : 3 playbooks long SPY = 3x le risque, non capé | HAUTE | Rien | — |
| P04 | **Pas de max risk global** : somme des R ouverts non limitée | HAUTE | Rien | — |
| P05 | **Session cap non universel** : `max_setups_per_session` existe dans campaign YAML mais le check est dans engine.py, pas risk_engine | MOYENNE | `engine.py:899` — `session_trades_by_playbook` dict | `engine.py` |
| P06 | **Conflits simultanés** : si 5 playbooks matchent sur la même minute, le tri est par playbook_name alphabétique | MOYENNE | `engine.py:1024-1032` — `_execute_candidate_setups` | `engine.py` |

### AXE 3 — DONNÉES / TEMPS / SESSIONS

| ID | Défaut | Sévérité | État actuel | Fichier(s) |
|----|--------|----------|-------------|------------|
| D01 | **Pas de calendrier holidays/half-days** : les jours fériés ne sont pas filtrés. Early close days (13:00 ET) marqués comme "corrupted" par quality_gates | MOYENNE | Seul commentaire : `quality_gates.py:73` "market holidays are not filtered out" | `scripts/quality_gates.py` |
| D02 | **Session definitions dispersées** : NY=09:30-16:00 défini dans `timeframe_aggregator.py:11-12`, `quality_gates.py:28-30`, `master_candle.py:17` indépendamment | MOYENNE | Pas de source unique | Multiples |
| D03 | **Timezone mixing CRITIQUE** : `pytz.timezone('US/Eastern')` (engine.py:1806) ET `ZoneInfo("America/New_York")` (engine.py:1964, 2086, etc.) | **HAUTE** | pytz deprecated, DST transitions peuvent diverger | `engine.py:9,1806` |
| D04 | **Quality gates non intégrées** : `quality_gates.py` valide UTC, duplicates, NaN, missing bars — mais n'est **jamais appelé** par engine.py | **HAUTE** | Script standalone, pas pre-flight | `scripts/quality_gates.py` |
| D05 | **HTF aggregation : 4H candle close times incorrects** : `hour in [13, 17, 19]` UTC — 13:59 UTC = 9:59 ET = PRE-MARKET | **HAUTE** | `timeframe_aggregator.py:89` | `engines/timeframe_aggregator.py` |
| D06 | **HTF aggregation : 1D close time hardcoded UTC** : `hour == 19` assume toujours EDT, incorrect en EST (nov-mars) | **HAUTE** | `timeframe_aggregator.py:92` | `engines/timeframe_aggregator.py` |
| D07 | **5m/10m incluent AH, 15m+ excluent AH** : incohérence dans le filtrage RTH | MOYENNE | `timeframe_aggregator.py:94-105` — is_rth check seulement pour 15m+ | `engines/timeframe_aggregator.py` |
| D08 | **Pas de dedup après concat** : `pd.concat(all_dfs)` sans `drop_duplicates()` | **HAUTE** | `engine.py:370` — duplicate bars traitées 2x | `engine.py` |
| D09 | **Pas de validation OHLCV bounds** : high < low, prix négatifs, volume négatifs non détectés | MOYENNE | Rien dans engine.py | `engine.py` |
| D10 | **Pas de gap detection pendant le run** : gaps >5min dans les données non signalés | MOYENNE | `quality_gates.py` a la logique mais pas branchée | `engine.py` |
| D11 | **Session date weekend carryover** : 3h lundi ET → `ny_date - 1 = dimanche` au lieu de vendredi | BASSE | `master_candle.py:56-57` | `engines/master_candle.py` |

### AXE 4 — REPORTING VÉRITÉ

| ID | Défaut | Sévérité | État actuel | Fichier(s) |
|----|--------|----------|-------------|------------|
| R01 | **Equity curve = realized only** : ne reflète pas l'unrealized P&L des positions ouvertes | HAUTE | `engine.py:2315-2336` — `_track_equity` somme les trades closés | `engine.py` |
| R02 | **Pas de MAE/MFE** : Max Adverse Excursion / Max Favorable Excursion non trackés | HAUTE | Aucun code | — |
| R03 | **Pas de raison d'entrée lisible** : on sait le playbook mais pas quels signaux spécifiques ont matché | MOYENNE | `PlaybookMatch.matched_conditions` existe mais contient des strings génériques | `models/setup.py:74-78` |
| R04 | **Sanity report existe** mais n'est pas systématiquement vérifié par les scripts | BASSE | `engine.py:3518+` — génère JSON mais personne ne le vérifie | `engine.py` |
| R05 | **Pas de replay lisible** : pas de log bar-by-bar pour un trade spécifique (entrée → bars intermédiaires → sortie) | MOYENNE | Rien | — |
| R06 | **Coûts résumés par type manquent** : total_costs agrégé mais pas breakdown commission vs slippage vs spread | BASSE | TradeResult a le breakdown mais le summary ne l'agrège pas | `engine.py:3570-3574` |

### AXE 5 — TESTS D'ACCEPTATION

| ID | Défaut | Sévérité | État actuel | Fichier(s) |
|----|--------|----------|-------------|------------|
| T01 | **Pas de test unitaire SL/TP intra-bar** | HAUTE | Rien | — |
| T02 | **Pas de test d'intégration limit order** | HAUTE | Rien | — |
| T03 | **Pas de test position sizing + capital committed** | HAUTE | `test_risk_engine_p0.py` existe mais ne teste pas concurrent positions | `tests/test_risk_engine_p0.py` |
| T04 | **Pas de test HTF aggregation boundaries** | HAUTE | Rien | — |
| T05 | **Pas de test synthétique "known outcome"** : on devrait pouvoir donner 10 barres prédéfinies et vérifier que le moteur produit exactement le trade attendu | HAUTE | Rien | — |
| T06 | **Test costs existe** mais ne couvre que la formule, pas l'intégration end-to-end | MOYENNE | `tests/test_backtest_costs.py` | — |
| T07 | **Pas de test anti-regression pour les fixes E01-E08** | HAUTE | Rien | — |

---

## B. Sévérité et impact

| Sévérité | Nb défauts | Impact sur vérité backtest |
|----------|-----------|---------------------------|
| **HAUTE** | 22 | Résultats potentiellement faux (SL/TP order, capital illimité, HTF DST bugs, dedup, timezone) |
| **MOYENNE** | 11 | Résultats biaisés mais dans une direction connue (spread flat, sessions dispersées, OHLCV) |
| **BASSE** | 4 | Cosmétique ou tolérable (weekend carryover, cost summary format) |

---

## C. Ordre optimal — blocs P0 / P1 / P2

### P0 — CRITIQUE (résultats potentiellement faux)

Sans ces fixes, tout backtest est suspect.

| Bloc | Défauts | Livrable | Fichiers à modifier | Tests à écrire | Effort |
|------|---------|----------|--------------------|----|--------|
| **P0-1: SL/TP intra-bar fix** | E01 | bar_open priority quand SL+TP same bar | `paper_trading.py` | `test_intrabar_sl_tp.py` : 4 cas (LONG SL-first, LONG TP-first, SHORT SL-first, SHORT TP-first) | S |
| **P0-2: Double slippage guard** | E05 | Audit et fix du flag `entry_slippage_applied`. Unifier : slippage UNIQUEMENT dans costs.py, plus dans paper_trading.py | `paper_trading.py`, `costs.py`, `engine.py` | `test_slippage_no_double_count.py` : vérifier qu'un trade a exactement 1x slippage, pas 2x | M |
| **P0-3: SL exit slippage** | E07 | Appliquer slippage adverse sur SL exit (SL touché → close_price = SL ± slippage, pas SL exact) | `paper_trading.py:270-275` | Ajouter cas dans `test_intrabar_sl_tp.py` | S |
| **P0-4: Max concurrent + capital** | P01, P02 | Valider les fixes déjà écrits (concurrent positions, committed capital) | `risk_engine.py`, `models/risk.py` | `test_concurrent_positions.py` : 3 cas (cap global, cap per-symbol, capital exhaustion) | M |
| **P0-5: Max risk global** | P04 | Sommer les R ouverts. Bloquer si somme > MAX_OPEN_RISK_R (default: 6R) | `risk_engine.py` | Ajouter cas dans `test_concurrent_positions.py` | S |
| **P0-6: Known-outcome synthetic test** | T05 | Test avec 10 barres synthétiques, entry/SL/TP prédéfinis, vérifier le résultat exact | Nouveau : `tests/test_engine_synthetic.py` | Le test EST le livrable | L |
| **P0-7: HTF aggregation fix + verification** | D05, D06, D07, T04 | Fix 4H close times (DST-aware). Fix 1D close time (EST/EDT). Décider 5m RTH filter. Tests boundaries. | `engines/timeframe_aggregator.py` | `test_timeframe_aggregator.py` : boundaries check, DST, overnight | L |
| **P0-8: Equity curve unrealized** | R01 | Tracker mark-to-market (prix courant des positions ouvertes) dans equity curve | `engine.py:2315-2336` | `test_equity_curve.py` : vérifier que l'equity reflète l'unrealized | M |
| **P0-9: Data dedup + validation pre-flight** | D08, D09, D04 | Dedup après concat. Validation OHLCV bounds. Intégrer quality_gates comme pre-flight. | `engine.py:370+` | `test_data_preflight.py` | M |
| **P0-10: Timezone unification** | D03 | Supprimer TOUTE utilisation de `pytz`. Migrer vers `zoneinfo` uniquement. | `engine.py:9,1806`, multiples | `test_timezone_consistency.py` : vérifier conversions ET/UTC | S |

**Total P0 : 10 blocs, ~22 défauts couverts**

### P1 — IMPORTANT (biais connus mais tolérables court terme)

| Bloc | Défauts | Livrable | Fichiers à modifier | Tests | Effort |
|------|---------|----------|--------------------|----|--------|
| **P1-1: MAE/MFE tracking** | R02 | Tracker max drawdown et max favorable par trade pendant sa durée | `paper_trading.py`, `models/trade.py`, `models/backtest.py` | `test_mae_mfe.py` | M |
| **P1-2: Limit order simulation** | E04, E06 | Valider les fixes entry_type/limit_price. Ajouter limit_fill_bars counter dans debug. Pas de fill probability (impossible sans tick data) | `models/setup.py`, `engine.py`, `setup_engine_v2.py` | `test_limit_order.py` : fill, expiry, no-fill | M |
| **P1-3: Inter-playbook correlation** | P03 | Si >1 position ouverte même symbole même direction, alerter et caper le sizing cumulé | `risk_engine.py` | `test_correlation_cap.py` | M |
| **P1-4: Session definitions centralisées** | D02 | Fichier unique `config/sessions.py` avec NY/London/Asia/PM/AH + sessions comme constantes | Nouveau fichier + refactor imports | `test_sessions.py` | S |
| **P1-5: Data validation pre-flight** | D04 | Avant le run, valider coverage, gaps, duplicates. WARN si >5% missing, FAIL si >15% | `engine.py` (au début de `run()`) | `test_data_preflight.py` | S |
| **P1-6: Trade entry/exit reasons enrichies** | R03, R05 | Ajouter `entry_signals: List[str]` au Setup, propager jusqu'au TradeResult. Log bar-by-bar pour debug | `models/setup.py`, `models/backtest.py` | — | S |
| **P1-7: Conflits simultanés** | P06 | Priorité par score/quality au lieu de nom alphabétique. Highest quality d'abord, puis highest score | `engine.py` (`_execute_candidate_setups`) | `test_priority_tiebreak.py` | S |
| **P1-8: Cost summary par type** | R06 | Résumé agrégé commission/slippage/spread/reg_fees dans le BacktestResult | `engine.py:3570+`, `models/backtest.py` | — | XS |

**Total P1 : 8 blocs, ~11 défauts couverts**

### P2 — NICE-TO-HAVE (améliore la confiance mais pas bloquant)

| Bloc | Défauts | Livrable | Effort |
|------|---------|----------|--------|
| **P2-1: Spread dynamique** | E02 | Spread variable : plus large à 9:30-9:45 (opening), plus serré 10:00-15:00, plus large 15:30-16:00 | S |
| **P2-2: Slippage variable** | E03 | Slippage plus élevé sur les 15 premières minutes, et sur les market orders vs limit | S |
| **P2-3: Holiday calendar** | D01 | Table des jours fériés NYSE 2024-2026 + early close days. Filtrer dans data loading | M |
| **P2-4: Timezone unification** | D03 | Migrer tout vers `zoneinfo` (supprimer `pytz`) | S |
| **P2-5: Sanity report auto-check** | R04 | Après chaque run, parser le sanity report et FAIL si des checks critiques échouent | S |
| **P2-6: Replay trade debugger** | R05 | Script CLI : donner un trade_id, voir toutes les barres de sa vie (entry → chaque minute → exit) avec P&L, SL, TP, prix | L |

**Total P2 : 6 blocs**

---

## D. Ordre d'implémentation recommandé

```
Semaine 1 — FONDATIONS (données + timezone) :
  P0-10 Timezone unification (pytz → zoneinfo) ─────────┐
  P0-9  Data dedup + OHLCV validation + quality gates ──┤ Parallèle
  P0-7  HTF aggregation fix (DST, 4H, 1D close times) ──┘
  GATE: run 1 semaine de données, vérifier HTF candles visuellement

Semaine 2 — EXÉCUTION (SL/TP + slippage) :
  P0-1  SL/TP intra-bar fix + tests ────────────────────┐
  P0-2  Double slippage guard ───────────────────────────┤ Parallèle
  P0-3  SL exit slippage ───────────────────────────────┘
  P0-6  Known-outcome synthetic test ──── GATE: 10/10 cas synthétiques OK

Semaine 3 — PORTEFEUILLE (capital + risque) :
  P0-4  Concurrent positions + capital ──────────────────┐
  P0-5  Max risk global ────────────────────────────────┤ Parallèle
  P0-8  Equity curve unrealized ────────────────────────┘

Semaine 4 — REPORTING + POLISH (P1) :
  P1-1  MAE/MFE tracking
  P1-2  Limit order simulation
  P1-3  Inter-playbook correlation cap
  P1-7  Conflits simultanés (priority sorting)
  P1-4  Sessions centralisées
  P1-8  Cost summary par type

P2 : après validation gate finale, au besoin.
```

---

## E. Fichiers à modifier (inventaire complet)

| Fichier | Blocs concernés |
|---------|----------------|
| `engines/execution/paper_trading.py` | P0-1, P0-2, P0-3, P1-1 |
| `backtest/engine.py` | P0-2, P0-6, P0-8, P0-9, P0-10, P1-2, P1-7 |
| `backtest/costs.py` | P0-2, P2-1, P2-2 |
| `engines/risk_engine.py` | P0-4, P0-5, P1-3 |
| `models/risk.py` | P0-4, P0-5 |
| `models/setup.py` | P1-2, P1-6 |
| `models/trade.py` | P1-1 |
| `models/backtest.py` | P0-8, P1-1, P1-6, P1-8 |
| `engines/timeframe_aggregator.py` | P0-7, P0-10 |
| `engines/master_candle.py` | P0-10 |
| `config/settings.py` | P1-4 |

### Fichiers à créer

| Fichier | Bloc |
|---------|------|
| `tests/test_intrabar_sl_tp.py` | P0-1, P0-3 |
| `tests/test_slippage_no_double_count.py` | P0-2 |
| `tests/test_concurrent_positions.py` | P0-4, P0-5 |
| `tests/test_engine_synthetic.py` | P0-6 |
| `tests/test_timeframe_aggregator.py` | P0-7 |
| `tests/test_equity_curve.py` | P0-8 |
| `tests/test_data_preflight.py` | P0-9 |
| `tests/test_timezone_consistency.py` | P0-10 |
| `tests/test_mae_mfe.py` | P1-1 |
| `tests/test_limit_order.py` | P1-2 |
| `tests/test_correlation_cap.py` | P1-3 |
| `tests/test_priority_tiebreak.py` | P1-7 |
| `config/sessions.py` | P1-4 |

---

## F. Gate finale — "Moteur acceptable / non acceptable"

### Critères de validation obligatoires (TOUS doivent passer)

| # | Critère | Test | Acceptable si... |
|---|---------|------|------------------|
| G1 | **Known-outcome synthetic** | `test_engine_synthetic.py` | 10/10 cas synthétiques donnent le résultat exact attendu |
| G2 | **Intra-bar SL/TP** | `test_intrabar_sl_tp.py` | 4/4 cas (LONG/SHORT × SL-first/TP-first) corrects |
| G3 | **No double slippage** | `test_slippage_no_double_count.py` | Slippage total = exactement 1x le taux configuré |
| G4 | **SL slippage** | Cas dans `test_intrabar_sl_tp.py` | SL exit = SL ± slippage (pas SL exact) |
| G5 | **Concurrent positions cap** | `test_concurrent_positions.py` | Jamais >MAX_CONCURRENT trades ouverts |
| G6 | **Capital reservation** | `test_concurrent_positions.py` | Trade refusé si committed_capital > buying_power |
| G7 | **Max open risk** | `test_concurrent_positions.py` | Trade refusé si somme R ouverts > MAX_OPEN_RISK_R |
| G8 | **HTF boundaries** | `test_timeframe_aggregator.py` | 5m candle[0] = 9:30-9:35 ET, 15m[0] = 9:30-9:45, etc. |
| G9 | **HTF DST correct** | `test_timeframe_aggregator.py` | 1D candle close correct en EST (nov-mars) ET EDT (mars-nov) |
| G10 | **Equity curve unrealized** | `test_equity_curve.py` | Equity reflète positions ouvertes, pas juste les closes |
| G11 | **MAE/MFE tracked** | `test_mae_mfe.py` | Chaque trade a mae_r et mfe_r non-nuls |
| G12 | **Costs always applied** | Smoke run | total_costs > 0 pour chaque trade |
| G13 | **Limit order fill check** | `test_limit_order.py` | Limit non rempli si prix ne touche pas le niveau |
| G14 | **No duplicate bars** | `test_data_preflight.py` | Dedup appliqué, 0 duplicates après load |
| G15 | **Timezone unified** | `test_timezone_consistency.py` | Zéro import pytz dans le codebase (sauf tests legacy) |
| G16 | **Data bounds valid** | `test_data_preflight.py` | OHLCV bounds respectés (high >= low, prix > 0) |
| G17 | **Replay test** | Manual | Pouvoir retracer bar-by-bar au moins 1 trade et confirmer le résultat |

### Verdict

- **17/17 = MOTEUR ACCEPTABLE** → Lancer edge discovery avec confiance totale
- **15-16/17 = MOTEUR ACCEPTABLE AVEC RÉSERVE** → Documenter les cas manquants, continuer
- **<15/17 = MOTEUR NON ACCEPTABLE** → Corriger avant tout autre travail

---

## G. Ce qui restera IMPOSSIBLE sans tick/bid-ask/order book

Même après le hardening complet, ces limitations persistent :

1. **Ordre réel des ticks intra-barre** : On utilise bar_open comme proxy, mais on ne saura jamais si high a été touché avant low dans la même minute.

2. **Fill probability des limit orders** : On vérifie que le prix a traversé le niveau, mais en réalité un limit à $450.50 peut ne pas être rempli même si le prix touche $450.50 (pas de profondeur).

3. **Slippage réel** : Le slippage dépend du volume, de la profondeur du carnet, du moment exact. Notre modèle est statistique, pas physique.

4. **Spread bid/ask réel** : Le spread varie à chaque seconde. Notre modèle est flat ou session-based, jamais tick-accurate.

5. **Impact de marché** : Nos ordres n'impactent pas le prix. Avec 500 shares SPY à $580, l'impact est négligeable, mais avec des positions plus grosses c'est faux.

6. **Latence d'exécution** : En live, il y a un délai entre signal et fill. Le backtest assume remplissage instantané.

**Mitigation** : Ces limitations biaisent dans des directions CONNUES. Le slippage/spread flat rend le backtest légèrement OPTIMISTE. On compense par des coûts conservateurs (2 bps spread, 0.05% slippage, SL wins par défaut). Si un playbook est positif APRÈS ces coûts conservateurs, il a de bonnes chances d'être positif en live.
