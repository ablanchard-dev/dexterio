# STRATEGY_EXTRACTION_MATRIX — Stratégies distinctes extraites du MASTER

Date : 2026-04-19
Source : 71 vidéos triées → 18 STRATEGY → 8 stratégies distinctes + 3 entry models V056

---

## 8 stratégies distinctes

| ID | Nom | Sources | Codabilité | Gaps moteur | Priorité implémentation |
|----|-----|---------|------------|-------------|------------------------|
| **S1** | Opening Range FVG Break | V054, V065, V048 | HAUTE (V065=100%) | Opening Range Tracker | **P0** |
| **S2** | Full Checklist Séquentiel | V022, V061, V070 | MOYENNE (~70%) | EventChainTracker, HTF level tracker, 79% Fib | **P1** |
| **S3** | London/Session Fakeout | V066, V051 | HAUTE (V051=86%) | Session range tracker | **P0** |
| **S4** | iFVG Setups | V010 | MOYENNE (~57%) | Discount zone filter, HTF FVG anchor | **P1** |
| **S5** | Daily Bias (contexte) | V016 | N/A | Session profile detector | Couche — pas un playbook |
| **S6** | AoI Multi-Confluence | V024, V055, V062, V064, V068 | BASSE (40-55%) | AoI 3+ touches detector, engulfing quality | **P2** (swing) |
| **S7** | OB Retest | V004, V056 | HAUTE (V056 M2=90%) | OB quality scoring, equal H/L detector | **P0** |
| **S8** | NQ Power of Three | V071 | MOYENNE (55-65%) | 10am manipulation detector, SMT divergence | **P2** (NQ only) |

---

## ⭐ DISCOVERY : V056 Model 2 — Liquidity Raid (90% codable)

**Le modèle le plus codable après V065.** Toute la logique est close-based :

1. Détecter equal highs/lows (pool de liquidité)
2. Détecter sweep (prix trade en-dessous)
3. Détecter closure confirmation (candle CLOSE au-dessus du level swept)
4. Entry sur le close
5. SL au sweep extreme
6. TP à l'external range liquidity

**Zéro discrétion.** Le seul paramètre libre est le TF (le modèle est TF-agnostic dans la vidéo).

---

## Ranking codabilité complet (toutes stratégies)

| Rang | Modèle | Stratégie | Codabilité | Action |
|------|--------|-----------|------------|--------|
| 1 | V065 (15m Range FVG) | S1a | **100%** | RÉÉCRIRE FVG_Fill_Scalp |
| 2 | V056 M2 (Liquidity Raid) | S7 | **90%** | **NOUVEAU** campaign |
| 3 | V054 (5m Range FVG + Engulfing) | S1b | **~95%** | NOUVEAU campaign |
| 4 | V051 (3-Step Asia Sweep strict) | S3b | **86%** | NOUVEAU campaign |
| 5 | V056 M1 (Engulfing Bar) | S7 | **85%** | NOUVEAU campaign |
| 6 | V066 (London Fakeout simple) | S3a | **83%** | NOUVEAU campaign |
| 7 | V004 (OB Retest + 1m BOS) | S7 | **80-85%** | NOUVEAU campaign |
| 8 | V056 M3 (FVG Fill) | S7 | **75%** | NOUVEAU campaign |
| 9 | V070 (Clean Protocol 6-step) | S2 | **~70%** | Phase 5b (EventChain) |
| 10 | V010 (iFVG Setups) | S4 | **~57%** | RÉÉCRIRE IFVG_5m_Sweep |
| 11 | V071 (NQ Power of Three) | S8 | **55-65%** | P2 (NQ seulement) |
| 12 | S6 (AoI Multi-Confluence) | S6 | **40-55%** | P2 (swing, AoI non résolu) |

---

## Disposition des 13 playbooks actuels

| Playbook actuel | Statut | Stratégie MASTER | Action |
|----------------|--------|-----------------|--------|
| `NY_Open_Reversal` | ALLOWLIST | ~S2 (V022) mais pas fidèle | **RÉÉCRIRE** fidèle V070 protocol |
| `FVG_Fill_Scalp` | ALLOWLIST | ~S1 (V065) mais pas fidèle | **RÉÉCRIRE** fidèle V065 (range + FVG binary) |
| `Session_Open_Scalp` | ALLOWLIST | ~S1 (V048) variante | **RÉÉCRIRE** fidèle V048 ou V054 |
| `IFVG_5m_Sweep` | ALLOWLIST | ~S4 (V010) mais pas fidèle | **RÉÉCRIRE** fidèle V010 (discount zone + HTF FVG) |
| `News_Fade` | ALLOWLIST | **AUCUNE** (invention user) | **GARDER** tel quel, non-MASTER |
| `Morning_Trap_Reversal` | quarantine | ~S3 (V066) mais pas fidèle | **FUSIONNER** dans S3 campaign |
| `Liquidity_Sweep_Scalp` | quarantine | Concept, pas stratégie | **SUPPRIMER** |
| `HTF_Bias_15m_BOS` | ALLOWLIST | ~S2 (V022) variante | **FUSIONNER** dans S2 campaign |
| `London_Sweep_NY_Cont` | DENYLIST | ~S3 sous-cas | **SUPPRIMER** |
| `Trend_Cont_FVG_Retest` | DENYLIST | ~S1 sous-cas | **SUPPRIMER** |
| `BOS_Momentum_Scalp` | DENYLIST | Pas de source | **SUPPRIMER** |
| `Power_Hour_Expansion` | DENYLIST | Pas de source | **SUPPRIMER** |
| `Lunch_Range_Scalp` | DISABLED | Pas de source | **SUPPRIMER** |

---

## Nouveaux campaign YAMLs fidèles

| Campaign YAML | Stratégie | Source | Codabilité | Priorité |
|--------------|-----------|--------|------------|----------|
| `campaign_range_fvg_v065.yml` | S1a (15m range) | V065 | 100% | **P0** — EXISTS, à réécrire fidèle |
| `campaign_liquidity_raid_v056.yml` | S7 (Liquidity Raid) | V056 M2 | 90% | **P0** — DISCOVERY |
| `campaign_range_fvg_v054.yml` | S1b (5m range + engulfing) | V054 | ~95% | **P0** |
| `campaign_asia_sweep_v051.yml` | S3b (strict, daily bias) | V051 | 86% | **P0** |
| `campaign_engulfing_bar_v056.yml` | S7 (Engulfing Bar) | V056 M1 | 85% | P0 |
| `campaign_london_fakeout_v066.yml` | S3a (simple) | V066 | 83% | **P0** |
| `campaign_ob_retest_v004.yml` | S7 (OB Retest) | V004 | 80-85% | P1 |
| `campaign_fvg_fill_v056.yml` | S7 (FVG Fill) | V056 M3 | 75% | P1 |
| `campaign_checklist_v070.yml` | S2 (6-step protocol) | V070 | ~70% | P1 (EventChain requis) |
| `campaign_ifvg_v010.yml` | S4 (fidèle) | V010 | ~57% | P1 |
| `campaign_orb_marubozu_v048.yml` | S1c (Marubozu) | V048 | P1 | P1 |
| `campaign_nq_power3_v071.yml` | S8 | V071 | 55-65% | P2 (NQ only) |
| `campaign_aoi_confluence_v064.yml` | S6 | V064 | 40-55% | P2 (swing) |

---

## Gaps moteur par priorité

| Gap | Stratégies | Complexité | Priorité |
|-----|-----------|------------|----------|
| **Opening Range Tracker** | S1 (V054, V065, V048) | ~100 lignes | **P0** |
| **Session Range Tracker** | S3 (V066, V051) | ~80 lignes | **P0** |
| **Equal Highs/Lows Detector** | S7 (V056 M2) | ~60 lignes | **P0** |
| **Binary gate YAML** (pas scoring composite) | S1, S3, S4, S7 | Refactor playbook_loader | **P0** |
| **Marubozu signal gate** | S1c (V048) | ~20 lignes | P0 |
| **Discount zone filter (50%)** | S4 (V010) | ~30 lignes | P1 |
| **HTF FVG anchor check** | S4 (V010) | ~50 lignes | P1 |
| **EventChainTracker** | S2 (V022, V070) | ~200 lignes | P1 |
| **79% Fibonacci** | S2 (V061, V070) | ~40 lignes | P1 |
| **SMT divergence NQ/ES** | S8 (V071) | ~80 lignes | P2 |
| **AoI detector (3+ touches)** | S6 | ~150 lignes | P2 |

---

## Critères de fidélité

Un playbook est "fidèle" quand :
1. **Chaque règle EXPLOITABLE** du truth pack est implémentée comme binary gate (pas scoring)
2. **Le TF de chaque step** correspond exactement à la vidéo source
3. **SL/TP** sont calculés selon la méthode de la vidéo, pas fixe %
4. **La session window** correspond exactement
5. **Les filtres** (discount zone, daily bias, etc.) sont implémentés

Un playbook "infidèle" c'est ce qu'on a aujourd'hui : des approximations qui mélangent des concepts de plusieurs vidéos, avec un scoring composite qui noie tout.

---

## Ordre d'implémentation recommandé (Phase 5a)

```
1. V065 (100%) — réécrire FVG_Fill_Scalp fidèlement
2. V056 M2 (90%) — NOUVEAU Liquidity Raid (discovery majeure)
3. V054 (~95%) — Range FVG + engulfing confirmation
4. V051 (86%) — Asia sweep strict avec daily bias
5. V056 M1 (85%) — Engulfing Bar pattern
6. V066 (83%) — London Fakeout simple
7. V004 (80-85%) — OB Retest avec 1m BOS

--- Phase 5b ---
8. V070 (~70%) — Full Checklist (nécessite EventChainTracker)
9. V010 (~57%) — iFVG fidèle (discount zone + HTF anchor)

--- Phase 6 (P2) ---
10. V071 (55-65%) — NQ Power of Three
11. S6 (40-55%) — AoI Multi-Confluence
```

Les 7 premiers (≥80% codabilité) sont implémentables avec le moteur actuel + Opening Range Tracker + Session Range Tracker + Equal H/L Detector.
