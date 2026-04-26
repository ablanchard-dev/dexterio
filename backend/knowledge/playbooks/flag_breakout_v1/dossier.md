# Flag_Breakout_5m_v1 — Dossier §18 (pièces A-D + H)

**Plan v4.0 J4** (post-TSMOM ARCHIVED, 2026-04-25). User a tranché Option C (#1 Flags / #2 crypto / #3 Aplus single-filter).

---

## Pièce A — Fiche d'identité

| Champ | Valeur |
|---|---|
| Nom canonique | Flag_Breakout_5m_v1 |
| Version | v1 |
| Famille | Indicator-based intraday continuation (pas ICT) |
| Type | Stateless instant detector (pas state machine) |
| Instruments | SPY + QQQ |
| Timeframes | 5m setup, 5m entry |
| Direction | Long + Short (mirror) |
| Régime visé | Toutes vol_band, sessions NY RTH 09:30-15:00 ET |
| Statut initial | SPECIFIED_READY (briques §0.B + détecteur livré) |
| Auteur / origine | Plan v4.0 §0.5bis Priorité #1 (post-TSMOM ARCHIVED 2026-04-25, user choice C) |
| Dernière review | 2026-04-25 |

## Pièce B — Hypothèse formelle

**Thèse** : sur SPY/QQQ 5m intraday RTH, une impulsion directionnelle nette suivie d'une consolidation flag tight précède statistiquement une continuation 1R (60%+ hit rate visé) dans le sens de l'impulsion.

**Mécanisme** : l'impulsion = absorption forte de l'order flow dans une direction (institutional move ou stop run). La consolidation flag = pause de digestion sans contre-impulsion (pas de profit-taking massif). Le breakout volume-confirmé = reprise du flow dans la direction initiale par les participants qui rejoignent / les stops opposés qui se déclenchent. Pattern intraday continuation classique documenté technical analysis (Edwards & Magee, Bulkowski).

**Conditions de fertilité** :
- Volatilité moyenne (ATR 14 stable, pas régime panic VIX≥30 ni ultra-low <13)
- Session NY RTH 09:30-15:00 ET (liquidité + volume ample pour signal vol_ratio fiable)
- Pas de news macro 5min avant breakout (élimine faux signaux post-news)

**Conditions de stérilité** :
- Premarket / post-market (volume distribution distordu, vol_ratio gate non-fiable)
- Lunch 12:00-13:30 ET très calme (impulsions rares, signaux faibles)
- Régime panic (impulsions chaotiques sans flag clean)

**Risque principal** (= falsifiabilité) : pattern flag breakout est documenté décennies → arbitrage public probable. Si Sharpe net 6.5y < 0.6 ou permutation p > 0.10 → signal arbitré, hypothèse réfutée empiriquement. Si E[R]_pre_reconcile ≤ 0 sur 4w canonical → signal absent localement.

## Pièce C — Spécification d'état décisionnel

**Stateless** : pas de state machine. Détecteur scan window à chaque nouvelle bougie 5m :

1. **Armement** = nouvelle bougie 5m fermée
2. **Confirmation** = pattern flag breakout détecté (impulsion + flag + breakout + volume)
3. **Émission setup** = ICTPattern(`flag_breakout`, direction, price_level=SL) injecté
4. **Invalidation** = pas de pattern si :
   - Insufficient bars (< 41)
   - Pas d'impulsion (< 1.5×ATR)
   - Flag trop wide (> 0.6× impulse range) ou wrong size (< 3 ou > 5 bars)
   - Volume insufficient (< 1.2× avg 20)
   - SL = 0 (risk inválido)
5. **Timeouts** : N/A (stateless)

## Pièce D — Dépendances moteur + audit infra

| Brique | Fichier | Statut |
|---|---|---|
| Détecteur | [flag_breakout.py](backend/engines/patterns/flag_breakout.py) | ✅ LIVRÉ J4.2 |
| Wire-up custom_detectors | [custom_detectors.py](backend/engines/patterns/custom_detectors.py) | ✅ LIVRÉ J4.2 |
| Wire-up playbook_loader type_map | [playbook_loader.py](backend/engines/playbook_loader.py) FLAG/FLAGBREAK/FLAGBREAKOUT | ✅ LIVRÉ J4.2 |
| ATR helper interne | inline `_atr()` | ✅ LIVRÉ J4.2 |
| Volume avg | inline | ✅ LIVRÉ J4.2 |
| SL logic SWING via signal price_level | existant `_calculate_price_levels` | ✅ EXISTANT |
| TP logic fixed_rr 1.0 | existant | ✅ EXISTANT |
| Breakeven 0.5R | existant | ✅ EXISTANT |
| Tests unit | [test_flag_breakout.py](backend/tests/test_flag_breakout.py) 6/6 PASS | ✅ LIVRÉ J4.3 |
| YAML campaign | [flag_breakout_v1.yml](backend/knowledge/campaigns/flag_breakout_v1.yml) | ✅ LIVRÉ J4.4 |

**Verdict audit infra** : `full infra exists` → statut SPECIFIED_READY.

## Pièce H — Kill rules pré-écrites (non-négociables, plan v4.0 J5)

Si l'un des points ci-dessous arrive sur smoke nov_w4 OU sur 4w Stage 1 canonical :

1. **n < 15 sur 4w canonical** → ARCHIVE Cas A1 §20 (signal structurellement rare, non-calibrable)
2. **E[R]_pre_reconcile ≤ 0** → ARCHIVE Cas C §20 (edge absent)
3. **Sharpe net annualisé < 0.6** (si convertible portfolio) → ARCHIVE
4. **Permutation p > 0.10** (si exécuté Stage 2 J6) → ARCHIVE par pattern méthodologique convergent (F2 J&T + TSMOM)
5. **> 70% des trades concentrés sur 1 semaine** → ARCHIVE (lucky window, pas signal stable)
6. **peak_R p60 < 0.5R** → ARCHIVE Cas C signal faible

**Pas de re-shoot, pas de single-filter retest, pas de grid search lookback/threshold**. Si fail → bascule Priorité #2 crypto J6-J7 immédiatement.

**PASS bar Stage 1** :
- n ≥ 15
- E[R]_pre_reconcile > 0.05R
- peak_R p60 > 0.5R
- 0 weeks < -0.5R
- 0 weeks zéro trade (≥1 trade par semaine pour preuve robustesse)

**PASS bar Stage 2 (J6 conditional)** :
- n ≥ 30 sur 12w extended
- E[R]_net > 0.10R post-G3 budget (= E[R]_pre_reconcile > 0.197R)
- PF > 1.2
- Permutation p < 0.05
- ≥3 régimes positifs sur 5
- Sub-sample stable (delta E[R] < 0.05R entre 1ère et 2ème moitié)
