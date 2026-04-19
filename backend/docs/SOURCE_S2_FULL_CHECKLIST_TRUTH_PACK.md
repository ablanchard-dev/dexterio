# Truth Pack — S2 Full Checklist Sequential

Sources : V022 (L9648), V061 (L35144), V070 (L46474)
Date : 2026-04-19

---

## Core partagé (3 variantes)

Thèse identique : price sweeps HTF liquidity → change de direction → entry sur 5m/1m retrace dans une confluence → target next HTF draw.

### Event Chain commune

```
HTF levels marqués (1H/4H/session H/L)
    → HTF liquidity sweep (prix traverse un level)
        → Confirmation LTF (BOS / IFVG / 79% Fib / SMT)
            → Continuation confluence (FVG fill / equilibrium / OB / breaker)
                → Entry trigger (candle close hors de la confluence)
                    → TP aux draws HTF opposés
```

### Confluences identiques dans les 3 vidéos

**Confirmation :** BOS, IFVG, 79% Fib closure, SMT divergence
**Continuation :** FVG fill, equilibrium fill, OB fill, breaker fill

---

## V022 — Building Blocks (9h course, la plus formalisée)

| Step | TF | Règle | Classification |
|------|----|-------|---------------|
| 1. Bias | 4H | Trend direction (HH/HL = bull, LH/LL = bear) | EXPLOITABLE |
| 2. Alignment | 1H | Si 1H aligné avec 4H → 5m. Si opposé → 15m | EXPLOITABLE |
| 3. HTF sweep | 1H/4H | Attendre sweep de high/low 1H ou 4H | EXPLOITABLE |
| 4. Working-TF BOS | 5m/15m | BOS dans la direction du bias | EXPLOITABLE |
| 5. Confluence | 5m/15m | FVG, OB, breaker, equilibrium | HEURISTIC |
| 6. Entry | 1m | 1m BOS dans la confluence | EXPLOITABLE |
| SL | — | Au-dessus du sweep (invalidation) | HEURISTIC (3 niveaux) |
| TP | — | 1H/4H draws on liquidity | HEURISTIC |

**Spécificité V022 :** Gate 1H alignment → détermine le TF de travail (5m vs 15m). Pré-market exception : si sweep déjà fait en London, utiliser HTF confluences comme trigger.

---

## V061 — Aggressive (skip 5m, direct 1m)

| Step | TF | Règle | Classification |
|------|----|-------|---------------|
| 1. Bias | HTF | "Strong bias" + dual draw on liquidity | HEURISTIC |
| 2. HTF draw hit | 1H/4H | Ou LTF low-res liquidity swept | EXPLOITABLE |
| 3. Confirmation | 1m | BOS / IFVG / 79% Fib closure | EXPLOITABLE |
| 4. Continuation | 1m | FVG / equil / OB / breaker fill | HEURISTIC |
| 5. Entry | 1m | Candle close hors de confluence | EXPLOITABLE |
| SL | — | Sous swing low 1m | HEURISTIC |
| TP | — | LTF low-res liq + HTF draws | HEURISTIC |
| Sizing | — | HALF risk (réserve pour 5m entry) | DISCRETIONARY |

**Spécificité V061 :** Skip le 5m complètement. Plus agressif, meilleur entry prix, pire WR. Nécessite "super strong bias". Demi-risque.

---

## V070 — Clean Protocol (6 steps, la plus complète)

| Step | TF | Règle | Classification |
|------|----|-------|---------------|
| 1. Mark levels | 1H/4H/session | H/L des sessions et TF HTF | EXPLOITABLE |
| 2. HTF sweep | 1H/4H/session | Prix traverse un level | EXPLOITABLE |
| 2B. Pre-market | 5m | Si sweep avant NY → attendre 5m sweep à NY open | EXPLOITABLE |
| 3. 5m confirmation | 5m | BOS / IFVG / 79% / SMT | EXPLOITABLE |
| 4. 5m continuation | 5m | FVG fill / equilibrium (SMT si 2B) | EXPLOITABLE |
| 5. 1m confirmation | 1m | BOS / IFVG / 79% / SMT | EXPLOITABLE |
| 6. Entry | 1m | Enter | EXPLOITABLE |
| SL | — | Au-dessus local high 1m | EXPLOITABLE |
| TP | — | Cascade: TP1 → BE, TP2 → TP3 aux draws 1H/4H/session | HEURISTIC |

**Spécificité V070 :** Règle 2B explicite (sweep pré-market → attendre 2e sweep NY). SMT formalisé. ES/NQ avec index selection. Exemples montrent 1:7 RR.

---

## Recommandation implémentation

**V070 est la meilleure base pour le code** — 6 steps explicites, la plupart EXPLOITABLE, protocol propre. C'est le "clean protocol" du même concept.

**V022 ajoute** le gate 1H alignment (5m vs 15m) — utile comme variante.

**V061 est trop agressif/discretionary** pour une première implémentation (skip 5m, "strong bias" subjectif).

### Gaps moteur requis pour S2

1. **EventChainTracker** (~200 lignes) — suivre la séquence d'événements par playbook
2. **HTF level tracker** — marquer automatiquement 1H/4H/session H/L
3. **SMT divergence** — comparer ES vs NQ (partiellement existant dans `ict.py`)
4. **79% Fibonacci** — pas encore implémenté
