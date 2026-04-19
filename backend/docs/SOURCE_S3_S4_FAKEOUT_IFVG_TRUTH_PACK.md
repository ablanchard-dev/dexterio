# Truth Pack — S3 London/Session Fakeout + S4 iFVG

Sources : V066 (L44844), V051 (L26511), V010 (L5443)
Date : 2026-04-19

---

## S3 — London/Session Fakeout

### Core partagé (V066 + V051)

1. Marquer les H/L de la session précédente (Asian + NY)
2. Attendre que London ouvre et sweep un level de session
3. Attendre BOS dans la direction opposée sur LTF
4. Entry sur le BOS
5. SL au-dessus/dessous du sweep extreme
6. TP au level de session opposé

---

### V066 — London Fakeout (haute codabilité, 5/6 EXPLOITABLE)

| Règle | Détail | Classification |
|-------|--------|---------------|
| Session marking | Asian 18:00-03:00 NY, London 03:00-08:00, NY 08:00-16:00 | EXPLOITABLE |
| Sweep identification | Price pushes above/below session H/L during London | HEURISTIC (no distance threshold) |
| BOS trigger | 5m candle CLOSE below valid low (not wick) | EXPLOITABLE |
| Entry | On BOS candle close | EXPLOITABLE |
| SL | Above high of London fakeout sweep | EXPLOITABLE |
| TP | Prior session lows/highs (opposite extreme) | EXPLOITABLE |
| Session window | London 03:00-08:00 NY. Also works at NY open | EXPLOITABLE |

**V066 ne requiert PAS de daily bias ni de 15m structure.** C'est le pattern brut : sweep + BOS = trade. Simple et direct.

---

### V051 — 3 Step A+ Asia Sweep (la plus codable, 6/7 EXPLOITABLE)

| Règle | Détail | Classification |
|-------|--------|---------------|
| Daily bias | Candle pattern: wick-above-close-inside = bearish, close-above-prior-high = bullish | EXPLOITABLE |
| 15m intraday bias | External structure HH/HL ou LH/LL alignée avec daily | EXPLOITABLE |
| Asia sweep | Prix doit trader au-dessous de Asia low (ou au-dessus de Asia high) | EXPLOITABLE |
| Entry trigger | 1m BOS: close above swing high (long) ou close below swing low (short) | EXPLOITABLE |
| SL | Sous le swing low du 1m leg | EXPLOITABLE |
| TP | Daily bias target. RR minimum 1:5 | HEURISTIC (scale point) |
| Session window | London 02:00-05:00 EST | EXPLOITABLE |

**V051 ajoute daily bias + 15m structure** comme filtres. Plus restrictif que V066, mais RR minimum 5:1 = sélectivité maximale.

---

### Différences clés S3

| Dimension | V066 | V051 |
|-----------|------|------|
| HTF daily bias | Non requis | MANDATORY |
| 15m intraday structure | Non requis | MANDATORY (alignement) |
| Entry TF | 5m BOS | 1m BOS |
| Min RR | 1:3 implicite | 1:5 explicite |
| Session | London 03:00-08:00 + NY valide | London 02:00-05:00 seulement |
| Complexité | 2 conditions (sweep + BOS) | 4 conditions (daily + 15m + sweep + 1m BOS) |

**Recommandation :** Implémenter V066 d'abord (plus simple, moins de filtres). V051 comme variante "strict" avec daily bias + 15m filter.

---

## S4 — iFVG Setups (V010, standalone)

### Pourquoi S4 est distinct

- **Aucune dépendance session** — pas d'Asian/London/NY. Purement price-structure.
- **Mécanisme d'inversion** — le prix doit d'abord FILL un FVG puis l'INVERSER (close through). Pas d'analog en S3.
- **Discount/premium zone** — filtre 50% du range obligatoire. Pas en S3.
- **Fractal** — même setup sur tous les TF (1m, 5m, 15m, 1H).

### Rules V010

| Règle | Détail | Classification |
|-------|--------|---------------|
| HTF FVG to the left | FVG sur TF supérieur doit exister dans la zone | EXPLOITABLE |
| Discount zone | Long = en dessous de 50% du range. Short = au-dessus | EXPLOITABLE |
| Liquidity sweep into FVG | Sweep de structural lows/highs DANS le HTF FVG | HEURISTIC (no distance) |
| iFVG close | Candle close au-dessus (long) ou au-dessous (short) d'un FVG inversé | EXPLOITABLE |
| Entry | Sur la candle qui close through l'iFVG | EXPLOITABLE |
| SL | Close below the iFVG zone | EXPLOITABLE |
| TP | Next structural target (subjective) | DISCRETIONARY |
| Session | Aucune restriction | N/A |

### Codabilité : MODERATE

4/7 rules EXPLOITABLE, 2 HEURISTIC, 1 DISCRETIONARY. Le TP est le point faible. Le détecteur iFVG existe déjà dans le repo (`engines/patterns/ifvg.py`). Le problème précédent : iFVG 5m WF = négatif (E[R] -0.049, 219 trades). Mais l'implémentation actuelle n'est PAS fidèle à V010 (pas de discount zone filter, pas de HTF FVG anchor requirement).

### Gaps vs implémentation actuelle IFVG_5m_Sweep

| Règle V010 | Implémenté ? | Note |
|-------------|-------------|------|
| HTF FVG to the left | NON | Le playbook actuel ne vérifie pas la présence d'un HTF FVG |
| Discount zone (50%) | NON | Pas de filtre equilibrium/discount |
| Liquidity sweep into FVG | Partiellement | `liquidity_sweep` existe mais pas lié au FVG zone |
| iFVG close | OUI | Détecteur `ifvg.py` fonctionne |
| SL = close below iFVG | NON | SL fixe % au lieu de structure-based |
| TP = structural | NON | TP fixe RR |

**L'implémentation actuelle est un squelette, pas une stratégie fidèle V010.**

---

## Ranking codabilité global

| Stratégie | EXPLOITABLE | HEURISTIC | DISCRETIONARY | Recommandation |
|-----------|-------------|-----------|---------------|----------------|
| V051 (S3 strict) | 6/7 | 0 | 1 | **Priorité haute** |
| V066 (S3 simple) | 5/6 | 1 | 0 | **Priorité haute** |
| V010 (S4 iFVG) | 4/7 | 2 | 1 | **Priorité moyenne** (TP à définir) |
