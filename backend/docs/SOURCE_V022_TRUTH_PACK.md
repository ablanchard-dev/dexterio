# Source Truth Pack — VIDEO 022 "10h Course" (Checklist séquentielle)

**Video file**: `videos/The Trading Industry Will Hate Me for This FREE 10+ Hour Course-grw58BIzotU.mp4`
**Transcript**: `MASTER_FINAL.txt` L9648-16632 (core checklist: L13195-13305)
**Quality**: MOYENNE-HAUTE pour le passage core (70% codable), BASSE pour le reste
**Role in roadmap**: Noyau 2 — EDGE CANDIDAT

---

## 1. Règles mécaniques extraites (passage core L13195-13305)

### RÈGLE 1 — 4H trend = bias
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L13201-13203
- **Verbatim**: "Step one, we understand our bias. Whatever the four hour is telling us, that's what our bias is."
- **Formulation normalisée**: La tendance du 4H détermine le bias du jour. Si le 4H montre des BOS haussiers successifs → bias bullish. Si baissiers → bias bearish.
- **Confirmé en Part 2**: L13330-13335: "Right here, we got a breaking structure to the downside on the four hour [...] for the time being price is bearish on the four hour."
- **VIDÉO À VÉRIFIER**: [ ] Le trader utilise-t-il un critère mécanique précis pour le trend 4H (BOS? MA? Candle?) ou est-ce visuel?

### RÈGLE 2 — Si bullish: chercher lows à sweep sur 1H/4H
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L13206-13211
- **Verbatim**: "if we have a bullish bias, what are we looking for? We're looking for draws of liquidity underneath lows on the high timeframes, on the four hour and the one hour."
- **Et l'inverse**: L13229-13231: "if we're bullish on the four hour, but we're bearish on the hourly, we're still looking for lows"
- **Formulation normalisée**: Marquer les lows significatifs sur 1H et 4H. Attendre que le prix sweep l'un d'entre eux. Le bias détermine la direction (bullish → chercher lows, bearish → chercher highs), mais le sweep direction est toujours dans le sens opposé au bias (sweep DOWN pour un bias UP).

### RÈGLE 3 — "Hands in our ass" = no-trade state
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L13222-13223, L13232
- **Verbatim**: "we get our hands and we shove them into our ass and we don't do anything until those prices are hit" / "We put our hands on our ass until those prices get hit."
- **Formulation normalisée**: RIEN ne se passe tant que le sweep n'a pas eu lieu. Pas de setup, pas d'analyse de confluence, pas de trade. Le sweep est le déclencheur qui active la recherche.
- **Confirmé en examples**: L13353-13354: "We can pull our muddy hands out of our ass after these high timeframe draws of liquidity get hit."

### RÈGLE 4 — TF de scale-down basé sur alignement 4H/1H
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L13224-13227 et L13248-13255
- **Verbatim**:
  - 4H=1H: "if the four hour is bullish and the hourly is bullish [...] we scale that into the five minute timeframe" (L13225-13226)
  - 4H≠1H: "If the four hour is bullish and the hourly is bearish [...] 15 minute timeframe [...] 15 minute break of structure" (L13248-13252)
- **Formulation normalisée**:
  - Si 4H et 1H sont alignés → scale down to **5m**
  - Si 4H et 1H sont divergents → scale down to **15m**
- **Confirmé en Part 4**: L14024-14026: "if the one hour timeframe is in line with the four hours [...] scale into the five minute timeframe. If the four hours bullish and the hourly is bearish, we scale into the 15 minute timeframe."
- **C'est la règle la plus importante architecturalement** — elle détermine le TF d'exécution.

### RÈGLE 5 — BOS sur le LTF (après sweep)
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L13226-13227 et L13252-13253
- **Verbatim**: "the next thing we're looking for is a break of structure" (L13227) / "We're waiting for a [...] minute break of structure" (L13252-13253)
- **Formulation normalisée**: Après le sweep, sur le TF sélectionné (5m ou 15m), attendre un BOS dans le sens du bias.
- **Confirmé en examples**: L13354-13355: "we can start looking for a break of structure on the five minute timeframe. Okay. From there, boom, we see break of structure to the downside."

### RÈGLE 6 — Confluence (3ème condition)
- **Classification**: HEURISTIQUE À VALIDER
- **Source TXT**: L13239-13255
- **Verbatim**: "we're looking for our third confluence [...] order block, fair value gap, breaker block, equilibrium. Those four." (L13239)
- **Formulation normalisée**: Après le BOS, attendre que le prix retrace vers l'une des 4 confluences: Order Block, FVG, Breaker Block, ou Equilibrium. Sur le même TF que le BOS (5m ou 15m).
- **Problème**: Laquelle choisir? Le trader dit "either an order block to get hit, a fair value gap to get hit, a breaker block to get hit, or equilibrium to get hit" (L13245-13246) — c'est un OU, n'importe laquelle suffit.
- **En pratique** (examples Part 2): L13356-13360: le trader marque TOUTES les confluences et prend celle qui est touchée en premier.
- **VIDÉO À VÉRIFIER**: [ ] Y a-t-il une priorité entre les confluences? Le trader en préfère-t-il une?

### RÈGLE 7 — Buying/selling pressure (trigger d'entrée)
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L13256-13266
- **Verbatim**: "We need to see buying pressure or selling pressure in order to execute out of these confluences [...] Literally just a green candle up and out of the order block, a green candle up and out of the fair value gap, a green candle up and out of the breaker block, a green candle closing above equilibrium."
- **Et l'inverse**: "a red candle closing underneath an order block, red candle closing underneath the fair value gap, red candle closing underneath the breaker block or red candle closing underneath equilibrium."
- **Formulation normalisée**: L'entrée n'est PAS au touch de la confluence. Il faut attendre une candle de confirmation: candle qui close au-delà de la confluence dans le sens du bias. C'est le trigger mécanique d'entrée.
- **Confirmé en examples**: L13370: "boom we finally see this candle close out of there perfect entry right here"

### RÈGLE 8 — Scale-down pour entry (LTF confirmation)
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L14035-14038
- **Verbatim**: "Once the third confluence gets pushed into, if we're on the five minute, we can scale into the one minute and try and find a break of structure within there [...] If we're on the 15 minute [...] we can scale into the five minute and find a break of structure right there."
- **Formulation normalisée**: Après la confluence touchée et la pressure confirmée, possibilité de scale-down d'un TF supplémentaire pour une entrée plus précise:
  - Si setup sur 5m → entry sur 1m (BOS 1m)
  - Si setup sur 15m → entry sur 5m (BOS 5m)
- **Note**: Ce point est ajouté en "Part 4", pas dans le core initial. C'est un raffinement, pas la base.

---

## 2. Séquence complète normalisée

```
ÉTAPE 0 — PRE-MARKET
  → Identifier 4H trend (bias)
  → Identifier 1H trend (alignement check)
  → Marquer highs/lows significatifs sur 1H et 4H (draws of liquidity)

ÉTAPE 1 — ATTENTE (no-trade state)
  → "Hands in our ass until those prices get hit"
  → Condition: sweep d'un high/low HTF

ÉTAPE 2 — SCALE DOWN
  → Si 4H=1H → 5m
  → Si 4H≠1H → 15m

ÉTAPE 3 — BOS (sur le TF sélectionné)
  → Attendre BOS dans le sens du bias

ÉTAPE 4 — CONFLUENCE (sur le même TF)
  → Attendre retrace vers OB / FVG / Breaker / Equilibrium

ÉTAPE 5 — TRIGGER (confirmation)
  → Candle close up and out (bullish) ou down and out (bearish) de la confluence

ÉTAPE 6 — ENTRY
  → Sur le candle de confirmation OU scale-down (5m→1m, 15m→5m) pour BOS LTF

SL/TP — NON SPÉCIFIÉ (voir section 3)
```

---

## 3. GAPs identifiés (non spécifié dans le transcript)

### GAP 1 — SL (CRITIQUE)
- **Source TXT**: L13320: "You guys don't know where to put your stop loss [...] We're going to get there in part three, probably."
- L13445: "we don't know where our stop losses [...] are yet"
- **En pratique** (examples): L14667-14668: "Could have put it literally underneath this candle right here, or fuck it, if you want to get super shicey, you could put it underneath these lows."
- **Heuristique observée**: SL sous le swing low du sweep (pour LONG) ou au-dessus du swing high (pour SHORT). Mais ce n'est JAMAIS formulé comme règle mécanique.
- **VIDÉO À VÉRIFIER**: [ ] **BLOQUANT** — Y a-t-il une partie du cours qui explicite le SL? Chercher dans les parties 3-7 du cours.
- **Provisoire pour prototype**: SL = low du sweep candle (pour LONG) ou high (pour SHORT).

### GAP 2 — TP (CRITIQUE)
- **Source TXT**: L13320-13321: "You guys don't know where to put your take profit."
- L13371: "we're not going to talk about take profits"
- **En pratique** (examples): L14641: "one to three point two five [...] risk reward ratio"
- L14671-14672: "take profit one, take profit two, take profit three, take profit four" (Fibonacci extensions)
- **Heuristique observée**: TP = draws of liquidity opposés (previous session highs/lows) ou Fibonacci extensions (-0.27, -1.27). RR varie de 1:1 à 3.25:1.
- **VIDÉO À VÉRIFIER**: [ ] **BLOQUANT** — Chercher la section TP dans les parties 3-7 du cours.
- **Provisoire pour prototype**: TP = prochain high/low HTF dans le sens du bias (draw of liquidity).

### GAP 3 — Session window
- **Source TXT**: L13323-13324: "we're only trading New York session"
- **Mais** les examples Part 2 montrent des trades Asian et London session (L14604, L14618).
- **VIDÉO À VÉRIFIER**: [ ] La stratégie core est-elle NY-only ou multi-session?
- **Provisoire pour prototype**: NY session uniquement (9:30-16:00 ET) — fidèle à L13324.

### GAP 4 — Fréquence attendue
- **Source TXT**: L13290-13291: "I haven't taken, I haven't seen a single trade using this strategy the past two weeks."
- **Formulation**: La fréquence est TRÈS basse. Quelques trades par mois avec le core seul.

---

## 4. Éléments HEURISTIQUES (à valider par vidéo)

| Élément | Source | Problème |
|---------|--------|----------|
| Choix de la confluence (OB vs FVG vs Breaker vs EQ) | L13239-13246 | Le trader dit "either [...] those four" → n'importe laquelle. Mais en pratique, prend-il la première touchée? La plus proche? |
| "4H trend" — critère mécanique | L13201-13203 | Comment le trader identifie le trend? BOS? Dernière candle? Structure? |
| "Pre-market sweep" (Part 4 addition) | L14041-14049 | Ajout de sweep pre-market → confluence hourly. Change le flow. |
| Confluences sur le même TF que le BOS? | L13253-13255 | "order block on the 15 minute, fair value gap on the 15 minute" → oui, même TF. Confirmé. |

---

## 5. Bruit / marketing (ignoré)

- L13268-13270: "I know this is a lot to write down" — filler
- L13280-13300: "simplest fucking strategy [...] fucking base [...] fucking flashlight" — style, pas contenu
- L13455: "fucking solid" — filler
- 60%+ du cours total = mindset, psychology, risk management platitudes, anecdotes

---

## 6. Résumé des vérifications vidéo requises

| # | Point à vérifier | Bloquant? |
|---|-------------------|-----------|
| 1 | **SL — règle mécanique** (chercher parts 3-7 du cours) | **OUI** — sans SL, pas d'implémentation viable |
| 2 | **TP — règle mécanique** (chercher parts 3-7 du cours) | **OUI** — sans TP, pas de RR calculable |
| 3 | Session window (NY-only ou multi-session?) | Non — provisoire NY |
| 4 | Critère mécanique du 4H trend | Non — BOS heuristique raisonnable |
| 5 | Priorité entre confluences | Non — "première touchée" est viable |
| 6 | Scale-down entry (Part 4 refinement) | Non — optionnel, pas core |

**Verdict Gate S3**: Le passage core contient 7 RÈGLES EXPLOITABLES + 1 HEURISTIQUE + 2 GAPs CRITIQUES (SL/TP). La proportion est > 50% RÈGLE → Gate S3 PASSE avec réserve SL/TP.

---

## 7. Stratégie V022 résumée (implémentable avec SL/TP provisoires)

```
PRE-MARKET:
  bias = 4H_trend (bullish/bearish)
  alignment = (4H == 1H) ? "aligned" : "divergent"
  scale_tf = alignment == "aligned" ? "5m" : "15m"
  draws = mark_significant_highs_lows(1H, 4H, bias)

ÉTAPE 1 — NO-TRADE STATE
  wait_for: sweep of any draw on 1H or 4H
  condition: price touches/exceeds a marked HTF high (bearish) or low (bullish)

ÉTAPE 2 — BOS
  tf: scale_tf (5m or 15m)
  wait_for: break of structure in bias direction
  condition: candle closes beyond recent swing high/low

ÉTAPE 3 — CONFLUENCE
  tf: scale_tf (same as BOS)
  wait_for: price retraces to OB / FVG / Breaker / Equilibrium
  take: first confluence touched

ÉTAPE 4 — TRIGGER
  wait_for: candle closes beyond confluence in bias direction
  condition: green candle out (bullish) or red candle out (bearish)

ENTRY: on trigger candle close
SL (provisoire): beyond sweep candle extreme
TP (provisoire): next HTF draw of liquidity in bias direction
SESSION: NY (9:30-16:00 ET)
FREQUENCY: ~2-4 trades/month (core strategy only)
```
