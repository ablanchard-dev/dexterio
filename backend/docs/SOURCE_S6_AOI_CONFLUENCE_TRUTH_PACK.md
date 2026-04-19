# Truth Pack — S6 Area of Interest Multi-Confluence

Sources : V064 (L44421), V068 (L45846), V055 (L32769), V024 (L17396), V062 (L35670)
Date : 2026-04-19

---

## Core partagé (5 vidéos)

Pipeline identique :
1. Identifier le trend sur HTF (weekly/daily/4H) via HH/HL ou LH/LL (body close)
2. Identifier un AoI (Area of Interest) : zone avec **3+ touches body** au même prix
3. Attendre que le prix atteigne l'AoI
4. Attendre un signal d'entrée (engulfing, morning star, doji) sur LTF (30m/15m/1H)
5. Entrer sur le close du signal
6. SL au-dessus/dessous de la zone (thesis invalidation)
7. TP au prochain structure level

---

## V064 — 1 Hour Day Trading Strategy (codabilité 6/9)

| Règle | Détail | Lignes | Classification |
|-------|--------|--------|---------------|
| 4H trend | LH/LL = bearish, HH/HL = bullish (body close) | L44496–44503 | EXPLOITABLE |
| 1H trend aligné | Même direction que 4H | L44499–44503 | EXPLOITABLE |
| AoI 4H | 3+ body touches au même prix | L44511–44513 | EXPLOITABLE |
| AoI 1H | Aussi valide dans la même zone | L44527–44535 | EXPLOITABLE |
| Rejection candlestick | Doji ou bearish engulfing sur 4H ET 1H | L44537–44580 | EXPLOITABLE |
| Entry | Engulfing sur 1H ou 30m au close | L44585–44594 | EXPLOITABLE |
| SL | 10–15 pips au-dessus du swing précédent | L44595–44616 | HEURISTIC |
| TP | 1:1 à 1:1.5, max 1:2 | L44620–44625 | EXPLOITABLE |
| Session | Pre-London, London, pre-NY, max 9AM NY | L44488–44493 | EXPLOITABLE |

---

## V068 — $54K in 24 Hours (codabilité 4/6)

| Règle | Détail | Lignes | Classification |
|-------|--------|--------|---------------|
| S/R zone 3+ touches | Zone forte avec plus de 3 touches | L45968–45969 | EXPLOITABLE |
| TF référence | 4H primaire | L45956–45959 | EXPLOITABLE |
| Engulfing 2 candles | 1 candle dont le body englobe les 2 précédentes | L45856–45858 | EXPLOITABLE |
| Entry sur close | Enter on close of engulfing | L45979 | EXPLOITABLE |
| SL | Sous les lows des 2 dernières candles + marge | L45980–45986 | HEURISTIC |
| TP | Prochain level structure (multiple TPs) | L46002–46020 | HEURISTIC |

---

## V055 — 3-Step A+ Supply & Demand (codabilité 8/11)

| Règle | Détail | Lignes | Classification |
|-------|--------|--------|---------------|
| Demand zone | 3+ impulsive candles = institution moved price | L32794–32802 | HEURISTIC |
| Zone drawing | Body de la candle avant le push | L32802–32807 | EXPLOITABLE |
| FVG confirmation | Imbalance entre candles voisines | L32809–32815 | EXPLOITABLE |
| Trend | HH/HL ou EMA (prix au-dessus = uptrend) | L32822–32839 | EXPLOITABLE |
| Slow momentum | Ralentissement en approchant la zone | L32846–32851 | HEURISTIC |
| Close inside zone | Close dans la zone (pas en-dessous = invalidé) | L32851–32854 | EXPLOITABLE |
| Entry | Prochaine candle positive (green) | L32853–32855 | EXPLOITABLE |
| SL | Sous la zone | L32854–32858 | EXPLOITABLE |
| Untested zone only | Zone fraîche > zone usée | L32881–32887 | EXPLOITABLE |
| Discounted (50% fib) | En-dessous de 50% du range | L32900–32904 | EXPLOITABLE |
| BOS requis | Break of structure avant entry | L32904–32910 | EXPLOITABLE |

---

## V024 — $346K in 1 Trade (codabilité 6/9)

| Règle | Détail | Lignes | Classification |
|-------|--------|--------|---------------|
| Daily trend | HH/HL ou shift vers LH/LL | L17447–17455 | EXPLOITABLE |
| Daily H&S | Head and shoulders aux highs | L17458–17464 | EXPLOITABLE |
| Neckline break | Body close sous la neckline | L17463–17468 | EXPLOITABLE |
| Break & retest | Retrace vers la neckline | L17467–17470 | EXPLOITABLE |
| 4H AoI | 3+ body touches | L17490–17511 | EXPLOITABLE |
| 4H EMA | Prix sous EMA = bearish confirmation | L17535–17542 | EXPLOITABLE |
| Double top | À l'AoI | L17558–17568 | HEURISTIC |
| Bearish engulfing | Trigger d'entrée | L17572–17578 | EXPLOITABLE |
| Min R:R 1:2.5 | Gate pré-entrée | L17648–17650 | EXPLOITABLE |

**Note :** V024 est un swing trade (multi-jours). Pas un scalp intraday.

---

## V062 — 10+ Hour Course (codabilité 7/10)

| Règle | Détail | Lignes | Classification |
|-------|--------|--------|---------------|
| Weekly trend | HH/HL ou LH/LL (body close) | L38500–38520 | EXPLOITABLE |
| Daily trend aligné | Même direction que weekly | L40120–40126 | EXPLOITABLE |
| AoI weekly/daily only | 3+ body touches, **pas** en-dessous de 4H | L40290–40297 | EXPLOITABLE |
| Zone size | 20–35 pips sweet spot | L40068 | HEURISTIC |
| Weekly+daily overlap | Combiner si les zones se chevauchent | L40061–40083 | HEURISTIC |
| H&S neckline break | Body close requis | L40697–40737 | EXPLOITABLE |
| Break & retest | Body close au-dessus + retest | L40170–40220 | EXPLOITABLE |
| Entry signal | Morning star ou engulfing sur 30m/15m | L43241–43264 | EXPLOITABLE |
| Enter on close | Pas mid-candle | L43242 | EXPLOITABLE |
| TP min 1:2 | Pre-trade gate | L40511–40513 | EXPLOITABLE |

---

## Éléments partagés

| Élément | V064 | V068 | V055 | V024 | V062 |
|---------|------|------|------|------|------|
| AoI = 3+ touches | ✓ | ✓ | ✓ | ✓ | ✓ |
| Body-based (pas wicks) | ✓ | implicite | body avant push | **explicite** | **explicite** |
| Engulfing = trigger | ✓ | ✓ (2 candles) | non (green candle) | ✓ | ✓ |
| Enter on close | ✓ | ✓ | ✓ | implicite | ✓ |
| HTF context ≥ 4H | 4H+1H | 4H | H1+daily BOS | daily+4H | weekly+daily |
| Session filter | London/NY | NY | London/NY | swing | London/NY |

---

## Différences clés

| Dimension | V064 | V068 | V055 | V024 | V062 |
|-----------|------|------|------|------|------|
| TF AoI | 4H+1H | 4H | H1 | 4H | Weekly+daily only |
| TF entry signal | 1H ou 30m | 30m ou 15m | 5m | 4H | 30m ou 15m |
| Pattern requis | Non | Non | FVG+BOS | H&S+double top | H&S ou break-retest |
| TP | 1:1 à 1:2 | Structure | 1:1 à trailing | Min 1:2.5 | Min 1:2 |
| EMA | Non | Non | Oui | Oui (4H) | Non |

---

## Verdict codabilité

**Partiellement codable — les parties dures sont discretionary.**

### Ce qui est mécanique (codable)
- Market structure HH/HL/LH/LL via body close → **fait** dans le moteur
- AoI = 3+ body touches au même prix → **comptable, objectif**
- Engulfing = 1 candle body englobe 2 précédentes → **test binary**
- Enter on close → **binary**
- TF alignment check → **binary**
- Pre-trade R:R gate → **calculable**

### Ce qui est HEURISTIC (difficile)
- **Construction de la zone AoI** : quels touches comptent, où tracer les bords, zone size
- "Slow momentum" vers la zone (V055) — pas de seuil quantitatif
- Zone fraîcheur vs usée — pas de définition quantitative de l'épuisement
- Double top ou H&S sur 4H — pattern recognition à calibrer

### Ce qui est DISCRETIONARY (non codable)
- **Confluence scoring** : combien de raisons suffisent ? 8-9 en V024, 5 pour un "D setup" en V064
- **"Picasso" trades** — l'intuition de l'auteur sur la qualité des patterns
- Décision d'extension TP basée sur le momentum — pure discrétion
- Choix de marché (10-15 marchés par semaine)

### Codabilité estimée : 40-55%

Le squelette (TF alignment → AoI → engulfing → enter) est codable. Le problème central non résolu : **la construction de l'AoI** (quels body touches comptent, comment gérer les candles qui se chevauchent, la taille de zone) et la couche discretionary de "qualité Picasso" qui filtre les faux signaux.

**Priorité : P2 (swing).** Nécessite un détecteur AoI 3+ touches non trivial (~150 lignes) qui n'existe pas dans le moteur.
