# Truth Pack — S7 Order Block Retest + S8 NQ Power of Three

Sources : V004 (L1272), V056 (L32982), V071 (L46915)
Date : 2026-04-19

---

## S7 — Order Block Retest

### V004 — Simple Order Block Strategy (codabilité 80-85%)

#### Flow d'exécution

```
1. HTF trend (swing HH/HL ou LH/LL)
    → 2. Identifier OB (dernière candle bearish avant impulse bullish + FVG)
        → 3. Vérifier pas de trap (pas d'equal highs/lows en-dessous)
            → 4. Attendre prix dans la zone OB
                → 5. 1m BOS confirmation (flip bearish → bullish sur 1m)
                    → 6. Entry sur le BOS 1m
```

#### Rules

| Règle | Détail | Lignes | Classification |
|-------|--------|--------|---------------|
| HTF trend | Swing structure HH/HL = bull, LH/LL = bear. Pro-trend only | L1391–1468 | EXPLOITABLE |
| OB Type 1 | Dernière candle bearish avant impulse bullish agressive | L1331–1333 | EXPLOITABLE |
| OB Type 2 | Candle bearish dans formation multi-candle avant impulse | L1343–1346 | EXPLOITABLE |
| OB Type 3 | Première candle du leg momentum bullish | L1349–1352 | EXPLOITABLE |
| FVG validation | OB doit laisser un FVG (candle 1 high vs candle 3 low ne touchent pas) | L1332–1338 | EXPLOITABLE |
| Trap avoidance | OB ne doit pas être sur equal highs/lows, session H/L, prev day H/L | L1563–1583 | HEURISTIC |
| 1m BOS confirmation | Attendre flip structure sur 1m dans la zone OB (break above swing high) | L1813–1820 | EXPLOITABLE |
| SL | Sous le swing low 1m le plus récent (avant le BOS) | L1828–1830 | EXPLOITABLE |
| TP | Cascade : 5R (half off) → 7R → HTF swing high (external range liq) | L2035–2083 | EXPLOITABLE |
| OB location | OB doit être au low du pullback leg, pas retracement interne | L1453–1465 | EXPLOITABLE |

#### Timeframes

| Rôle | TF |
|------|----|
| Trend/bias | 15m ou H1 (L1900) |
| OB identification | 15m (primary), 5m (alternative) |
| Entry confirmation | 1m |

#### Spécificités V004
- 3 types d'OB valides (pas un supérieur aux autres)
- **FVG non-négociable** : un OB sans FVG n'est pas un vrai OB
- Trap avoidance = le point le plus difficile à coder (quelle pool de liquidité sera sweep en premier ?)
- Le 1m BOS trigger est la partie la plus propre et le signal principal
- Cousin logique de NY_Open_Reversal (HTF bias → HTF OB → LTF BOS entry)

---

### V056 — 3-Step A+ ICT Strategy (3 Entry Models)

#### Framework commun (tous les 3 modèles)

| Step | Détail | Lignes | Classification |
|------|--------|--------|---------------|
| Step 1 — Target | External range liquidity only (swing extreme le plus récent) | L32990–33050 | EXPLOITABLE |
| Step 2 — Timing | Éviter NFP, FOMC, CPI. Trader APRÈS l'événement | L33086–33180 | EXPLOITABLE |
| Direction confidence | 70-80% confiance sur la direction avant entry | L33048 | HEURISTIC |

---

#### Model 1 — Engulfing Bar (codabilité ~85%)

| Règle | Détail | Lignes | Classification |
|-------|--------|--------|---------------|
| Engulfing detection | 1 candle prend le high ET le low de la précédente, close opposé | L33200–33210 | EXPLOITABLE |
| Entry | Sur la 3ème candle (retracement après l'engulfing) | L33201–33203 | HEURISTIC |
| SL | Sous le low de l'engulfing candle (bull) / au-dessus du high (bear) | L33210–33225 | EXPLOITABLE |
| TP | External range liquidity (old swing high/low) | L33212–33217 | EXPLOITABLE |
| Min R:R | 1:2 minimum sinon skip | L33212–33217 | EXPLOITABLE |
| Calendar | Pas de trade NFP/FOMC/CPI day | L33086–33180 | EXPLOITABLE |

**TF non spécifié** — le pattern est TF-agnostic dans le texte.

---

#### Model 2 — Liquidity Raid (codabilité ~90%) ⭐ DISCOVERY

| Règle | Détail | Lignes | Classification |
|-------|--------|--------|---------------|
| Equal highs/lows | Identifier pool de liquidité (equal H/L) | L33258 | EXPLOITABLE |
| Sweep | Prix trade en-dessous des equal lows (bull) | L33258–33261 | EXPLOITABLE |
| Closure confirmation | Candle CLOSE au-dessus du swing low swept | L33260, L33291 | EXPLOITABLE |
| Entry | Sur le close de la candle de confirmation | L33260 | EXPLOITABLE |
| SL | Au sweep extreme (le wick le plus bas qui a swept) | L33264–33266 | EXPLOITABLE |
| TP | External range liquidity (old swing high/low) | L33272–33275 | EXPLOITABLE |

**C'est le modèle le plus propre de V056.** Toute la logique est close-based : détecter equal H/L, détecter sweep, détecter close back above. Zéro discrétion. Le TF n'est pas fixé mais chaque tier est déterministe une fois choisi.

**Citation clé :** "it's all dependent on the closure if we don't get a closure then it's not valid" (L33291)

---

#### Model 3 — FVG Fill (codabilité ~75%)

| Règle | Détail | Lignes | Classification |
|-------|--------|--------|---------------|
| FVG detection | 3-candle imbalance (candle 1 high vs candle 3 low = gap) | L33295–33298 | EXPLOITABLE |
| Entry | Limit order dans le FVG (prix retrace dans le gap) | L33297–33301 | EXPLOITABLE |
| SL Aggressive | Au near edge du FVG (candle 1 low/high) | L33298–33306 | EXPLOITABLE |
| SL Moderate | À candle 2 high/low | L33298–33306 | EXPLOITABLE |
| SL Conservative | À candle 3 high/low | L33298–33306 | EXPLOITABLE |
| TP | External range liquidity | L33304–33308 | EXPLOITABLE |

**SL tier = 1 free parameter** (aggressive/moderate/conservative). Chaque tier est déterministe une fois choisi. Pas de signal de confirmation → WR potentiellement plus bas.

---

## S8 — NQ Power of Three (V071, auteur différent : Kane/TJR)

### Codabilité : 55-65%

#### Flow d'exécution

```
1. Daily PO3 : identifier range D-1 (high/low)
    → 2. H4 PO3 : manipulation wick dans la zone daily
        → 3. H1 PO3 : candle 10am EST wick above 9am high
            → 4. SMT divergence : NQ fait new high, ES ne confirme pas (ou inverse)
                → 5. Entry : limit à l'IFVG (gap inversé) dans le wick 10am
                    → 6. TP : 50% du dealing range
```

#### Rules

| Règle | Détail | Lignes | Classification |
|-------|--------|--------|---------------|
| Daily PO3 range | High/low du jour précédent | L46940–46952 | EXPLOITABLE |
| H4 PO3 alignment | H4 manipulation wick coïncide avec daily wick zone | L46994–47002 | EXPLOITABLE |
| H1 10am manipulation | Candle 10am EST wick above 9am hourly high | L47023–47037 | EXPLOITABLE |
| SMT divergence | NQ fait new high, ES ne confirme pas (ou inverse) | L47257–47315 | EXPLOITABLE |
| IFVG entry | Limit à la re-tap de l'inversion FVG dans le wick | L47338–47363 | EXPLOITABLE |
| TP | 50% du dealing range — "the base hit" | L47362–47364 | EXPLOITABLE |
| SL | Au sweep high (extreme du wick 10am) + buffer | L47314–47316 | EXPLOITABLE |
| Breakeven | Si candle hourly reclaim au-dessus du sweep high → exit | L47045–47048 | EXPLOITABLE |
| Session window | 9:15–11:30 EST strictement | L47031 | EXPLOITABLE |
| Asset | NQ only (ES pour divergence reference seulement) | L46960–46962 | EXPLOITABLE |
| Multi-TF PO3 alignment | Daily + H4 + H1 doivent tous montrer manipulation | L46997, L47464–47467 | HEURISTIC |
| Aggressive BE management | "right or right out" — intuition-based | L47078 | DISCRETIONARY |

#### Ce qui rend V071 unique dans le MASTER

1. **NQ-specific** — aucun autre modèle ne cible exclusivement NQ
2. **10am EST time event** — seul modèle avec un trigger temporel fixe
3. **H1 only** — pas de descente vers 5m/1m pour l'entry
4. **Cross-index divergence** (NQ vs ES) — filtre requis, pas optionnel
5. **TP = 50% du range** — pas un swing extreme ni un R:R fixe

**Citation clé de Kane :** "I think a robot could pick up the model...but the discretion is my edge" (L47207–47210) — l'edge en live vient d'une couche intuitive non codable.

---

## Ranking codabilité global S7+S8

| Modèle | Codabilité | Strongest Rule | Weakest Rule |
|--------|------------|----------------|--------------|
| V056 Model 2 (Liquidity Raid) | **90%** | Closure confirmation (tout close-based) | TF non fixé |
| V056 Model 1 (Engulfing Bar) | **85%** | Pattern definition strict | TF non fixé |
| V004 (OB Retest + 1m BOS) | **80-85%** | 1m BOS trigger | Trap avoidance ordering |
| V056 Model 3 (FVG Fill) | **75%** | FVG geometry | SL tier choice + pas de confirmation |
| V071 (NQ Power of Three) | **55-65%** | 10am time filter + SMT | IFVG entry selection + multi-TF alignment |
