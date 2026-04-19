# Truth Pack — S1 Opening Range FVG Break

Sources : V054 (L32570), V065 (L44685), V048 (L25567)
Date : 2026-04-19

---

## Core partagé (3 variantes)

1. Définir l'opening range : high/low de la fenêtre 9:30-9:45 EST
2. Attendre un break : au moins 1 candle close outside range sur le TF signal
3. Exiger un pattern qualifiant au break : FVG (V054/V065) ou Marubozu (V048)
4. Entrer sur pullback vers la structure qualifiante, pas sur le break
5. SL sous la structure qualifiante
6. TP à RR fixe (2:1 ou 3:1) ou structural level
7. Session gate : stop après 12h00 (V065) ou 2h de trading (V048)

---

## V065 — 15m Range FVG (la plus mécanique, 100% codable)

| Règle | Détail | Classification |
|-------|--------|---------------|
| Range | First 15m candle (9:30-9:45) high/low | EXPLOITABLE |
| Direction | 5m FVG forms on range break | EXPLOITABLE |
| Entry | Limit order at FVG midpoint | EXPLOITABLE |
| SL | Below FVG candle 1 base | EXPLOITABLE |
| TP | Fixed 2:1 RR | EXPLOITABLE |
| Cutoff | No trades after 12:00 PM EST | EXPLOITABLE |
| No FVG = no trade | Explicit | EXPLOITABLE |

**Truth pack existant dans le repo.** Déjà implémenté comme `FVG_Fill_Scalp` mais pas fidèlement (scoring composite au lieu de binary gates, pas de range tracking).

---

## V054 — 5m Range FVG + Engulfing (haute codabilité)

| Règle | Détail | Classification |
|-------|--------|---------------|
| Range | First 5m candle (9:30-9:35) high/low | EXPLOITABLE |
| Direction | 1m FVG with candle close outside range | EXPLOITABLE |
| Entry | Retest of FVG → engulfing candle close = market order | EXPLOITABLE |
| SL Method 1 | 1 tick below retest candle | EXPLOITABLE |
| SL Method 2 | Below FVG gap candle (expanding markets) | EXPLOITABLE |
| TP Method 1 | Fixed 3:1 RR | EXPLOITABLE |
| TP Method 2 | Trail SL below each 1m candle after 3:1 | EXPLOITABLE |
| Expanding filter | Red folder news OR ATR rising 3+ days | HEURISTIC |

**Différences vs V065 :** range plus court (5 min vs 15 min), confirmation supplémentaire (engulfing), RR plus agressif (3:1 vs 2:1), signal sur 1m au lieu de 5m.

---

## V048 — ORB Marubozu (la moins codable)

| Règle | Détail | Classification |
|-------|--------|---------------|
| Range | First 3x 5m candles (9:30-9:45) high/low | EXPLOITABLE |
| Trend filter | 5m trend line alignment | HEURISTIC |
| Momentum break | 5-7 consecutive candles on 1m | HEURISTIC |
| Entry signal | 1m Marubozu (no-wick candle) at S/D zone | EXPLOITABLE |
| Entry | Limit at Marubozu level | EXPLOITABLE |
| SL | Below range midline | EXPLOITABLE |
| TP | Nearest structural S/R | DISCRETIONARY |
| Session | 2h from 9:30 (~11:30 cutoff) | EXPLOITABLE |

**Moins adapté pour implémentation auto** : trend line = judgment, TP = discretionary.

---

## Recommandation implémentation

**Priorité 1 : V065** (100% exploitable, truth pack existant, FVG_Fill_Scalp à réécrire fidèlement)
**Priorité 2 : V054** (presque 100%, ajoute confirmation engulfing, meilleur RR)
**Priorité 3 : V048** (nécessite Opening Range Tracker + Marubozu gate, TP discretionary)
