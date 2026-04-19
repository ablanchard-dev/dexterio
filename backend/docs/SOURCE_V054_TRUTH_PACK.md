# Source Truth Pack — VIDEO 054 "The 3 Step A+ Scalping Strategy (That Actually Works)"

**Video file**: `videos/The 3 Step A+ Scalping Strategy (That Actually Works)-cVgq9op8hnw.mp4`
**Transcript**: `MASTER_FINAL.txt` L32570-32766
**Quality**: HAUTE (85% codable)
**Role in roadmap**: Variante Noyau FVG — CALIBRATION FIDÉLITÉ

---

## 1. Règles mécaniques extraites

### RÈGLE 1 — Range du jour (Step 1)
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L32583-32596
- **Verbatim**: "you're going to get to your desk right at 9.30 a.m. Eastern Time [...] you're going to be on trading view [...] we want to start out on our five-minute chart [...] we're going to mark our first set of levels by marking out the high and the low of this first five-minute candle that begins at 9.30 a.m. EST and ends at 9.35"
- **Formulation normalisée**: Sur le chart **5m**, marquer le high et le low du **1er candle 5m** (9:30-9:35 ET). Ce range définit les bornes de trading du jour.
- **Note importante**: V054 utilise un range **5m** (9:30-9:35). C'est différent de V065 qui utilise un range **15m** (9:30-9:45). Ce sont deux stratégies distinctes du même auteur.
- **Justification auteur**: "this candle [...] has the highest amount of volume of any candle over the entire trading day. This means the high is where selling pressure was the strongest, and then at the low, the buying pressure was the strongest."

---

### RÈGLE 2 — Direction confirmée par FVG sur 1m hors range (Step 2)
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L32604-32621
- **Verbatim**: "we're going to need to switch to our one minute chart [...] we need at least one of the three candles involved in the creation of the fair value gap to close either outside the high or outside the low"
- **Formulation normalisée**:
  1. Passer sur chart **1m**.
  2. Attendre qu'un FVG se forme dont **au moins 1 des 3 candles ferme au-delà du high ou du low** du range 5m.
  3. Direction = sens du break (close au-dessus du high → LONG ; close sous le low → SHORT).
- **Gate binaire**: La fermeture hors range d'au moins un candle du triplet FVG est OBLIGATOIRE. Un simple FVG à l'intérieur du range NE CONFIRME PAS la direction.
- **Verbatim clé**: "that is not what we're looking for [...] All this does is confirms the market direction."

---

### RÈGLE 3 — Entrée Model 1 : Confirmation Entry (Step 3a)
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L32622-32656
- **Verbatim**: "we're going to have a fair value gap pattern [...] at least one of the three candles in the fair value gap pattern has to close beyond either the high or the low. Once you have that happen, what you're going to wait for is a retest candle [...] we need to show that this fair value gap is going to hold [...] what we're looking for is an engulfing of the retest candle [...] this candle's body was fully engulfed by this up-close candle"
- **Séquence complète**:
  1. FVG se forme avec fermeture hors range → direction confirmée.
  2. Attendre un **retest candle** : le marché revient dans la zone du FVG.
  3. Attendre un **candle engulfant le retest candle** (body du retest entièrement absorbé).
  4. À la clôture du candle engulfant → entrer en **market order** (pas limit).
  5. **SL** = 1 tick sous le low du retest candle (LONG) / 1 tick au-dessus du high (SHORT).
  6. **TP** = RR **3:1 fixe**.
- **Verbatim SL**: "put our stop loss one tick below the low of this retest candle"
- **Verbatim TP**: "for the target, we're going to go for a fixed three to one risk to reward"
- **Verbatim entrée**: "as soon as that engulfing candle closes, then we're going to put our [entry]"

---

### RÈGLE 4 — Entrée Model 2 : Expanding Market Entry (Step 3b)
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L32678-32716
- **Verbatim**: "we still go to the one minute chart [...] we would still wait to see when the market comes back down [...] that retest candle getting engulfed, we're going to enter, but we're going to do things a little differently with our stop and our take profit"
- **Différences par rapport à Model 1**:
  - **Entrée**: Identique (engulfing du retest candle → market order à la clôture).
  - **SL**: Placé sous le **candle du FVG qui a créé le gap** (gap candle), PAS sous le retest candle.
    - Verbatim: "instead of placing the stop loss one tick under the retest candle, we're going to place it under the gap candle in the fair value gap. So whatever candle created the gap."
  - **TP**: Pas de TP fixe — trailing stop après dépassement du niveau 3:1.
    - Verbatim: "you're not just going to take profits [...] once the market passes this level [...] you're going to take your stop loss and you're going to trail it up just below each one minute candle"
    - Mécanique: Une fois le niveau 3:1 dépassé, SL se trail sous chaque nouveau candle 1m jusqu'au stop-out.
- **Résultat exemple**: Trade initialement 3:1 devenu ~7-8:1 par trailing.

---

### RÈGLE 5 — Condition "Expanding Market" : quand utiliser Model 2
- **Classification**: HEURISTIQUE À VALIDER
- **Source TXT**: L32717-32738
- **Deux méthodes exposées**:
  1. **Calendrier économique** (Forex Factory) : Présence de news **red folder** (impact maximal) le jour du trade.
     - Verbatim: "anytime we have red folder news, we know that the market is likely going to make a big impact"
  2. **ATR daily croissant sur 3+ jours** : Sur le chart journalier, si l'ATR augmente depuis plus de 3 jours → marché en expansion.
     - Verbatim: "what you want to see is an average true range being increasing for more than three days before you call an expanding market"
- **Classification**: HEURISTIQUE À VALIDER — le seuil ATR "3 jours croissants" est mécanique mais non validé quantitativement.

---

### RÈGLE 6 — Session / Time Window
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L32583-32585
- **Formulation normalisée**: Présence au bureau à **9:30 ET**. La fenêtre de setup commence dès 9:30. Pas de cutoff explicite mentionné dans V054.
- **Note**: V065 mentionne un cutoff 12:00 ET. V054 ne le mentionne pas explicitement. Appliquer 12:00 par prudence (règle commune aux deux vidéos du même auteur).

---

### RÈGLE 7 — Pas de trade si pas de FVG hors range
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L32607-32616
- **Verbatim**: "you just want to wait for the market to break outside the fair value gap. But that is not what we're looking for [...] the fair value gap does matter, but it's not enough to confirm our entry"
- **Formulation normalisée**: Le FVG seul (à l'intérieur du range) n'est PAS suffisant. La condition nécessaire est : FVG **avec au moins 1 candle fermant hors range**. Sinon → PAS DE TRADE.

---

### RÈGLE 8 — Timeframe d'exécution : 1m uniquement après setup 5m
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L32604-32606, L32685-32686
- **Formulation normalisée**:
  - Step 1 (range) : **5m**
  - Step 2 (confirmation direction) : **1m**
  - Step 3 (entrée) : **1m** (retest + engulfing)
- Le trader bascule explicitement de 5m vers 1m pour les étapes 2 et 3.

---

### RÈGLE 9 — Backtest annoncé dans la vidéo
- **Classification**: CONTEXTE DISCRÉTIONNAIRE
- **Source TXT**: L32753-32757
- **Verbatim**: "we had a P and L of $10,950 over a total of 17 trades with a win rate of 70.5%"
- Note: Max drawdown $1,300 sur 17 trades (~1 mois). C'est un backtest manuel présenté à l'écran, pas auditable.

---

## 2. Éléments HEURISTIQUES (à valider)

### HEURISTIQUE 1 — Seuil ATR pour "Expanding Market"
- **Classification**: HEURISTIQUE À VALIDER
- **Source TXT**: L32737-32738
- **Verbatim**: "what you want to see is an average true range being increasing for more than three days before you call an expanding market"
- **Problème**: "increasing" n'est pas défini quantitativement. Est-ce ATR[0] > ATR[1] > ATR[2] > ATR[3] ? Ou une croissance minimale en % ? Le seuil "3 jours" est mécanique mais la définition d'"augmentation" reste floue.
- **À calibrer** : ATR daily croissant sur 3 jours consécutifs (chaque jour > jour précédent) comme proxy.

### HEURISTIQUE 2 — "Small fair value gaps count"
- **Classification**: HEURISTIQUE À VALIDER
- **Source TXT**: L32667
- **Verbatim**: "small fair value gaps count as well"
- **Problème**: Aucun seuil minimum de taille de FVG n'est défini. Cela implique qu'un FVG d'1 tick est valide. Dans le code actuel `fvg_quality` est scoré — mais le seuil minimal n'est pas ancré à cette règle.
- **À calibrer** : Définir un seuil minimum (ex : FVG ≥ X% de l'ATR 1m) ou accepter tout FVG sans filtre de taille.

---

## 3. Contexte discrétionnaire (non codable mais informatif)

- **Fréquence annoncée**: "make consistent profits with less than 90 minutes of work per day". Backtest montre 17 trades/mois → ~4/semaine.
- **Instruments mentionnés**: "This works in futures, stocks, crypto, and forex." Le trader montre Nasdaq (NQ futures).
- **Prop firm angle**: Stratégie présentée comme adaptée aux prop firms (high win rate + fixed RR). "The high win rate, high risk to reward nature of this strategy makes it perfect for prop firms."
- **Patience requise**: L32693 — "you have to stay patient and understand that your edge is going to rely on you being disciplined."

---

## 4. Bruit / marketing (ignoré)

- L32573-32578 : Intro storytelling ("I've been trading for nine years")
- L32595-32602 : Appel à engagement ("comment and make a commitment")
- L32656-32663 : Prop firm plug (Apex, code Casper)
- L32739-32753 : Mentorship plug
- L32757-32766 : Outro/subscribe CTA

---

## 5. Comparaison V054 vs V065

| Dimension | V054 (cette vidéo) | V065 (vérité codée actuelle) |
|-----------|---------------------|-------------------------------|
| TF Range | **5m** (9:30-9:35) | **15m** (9:30-9:45) |
| TF Setup/Entry | **1m** pour tout | **5m** setup + 5m FVG |
| Confirmation | FVG **1m** avec 1 candle fermant hors range | FVG **5m** break hors range |
| Entrée | **Market order** à clôture candle engulfant | **Limit order** à 50% du FVG |
| SL (Model 1) | 1 tick sous **retest candle** | Sous **candle 1 du FVG** (fvg_extreme) |
| SL (Model 2) | Sous **gap candle** du FVG | N/A (pas de Model 2 implémenté) |
| TP | **3:1 fixe** (Model 1) / trailing après 3:1 (Model 2) | 1.5 + 2.0 (dual TP) + breakeven à 1R |
| Filtre "chop" | FVG hors range obligatoire (gate binaire) | `fvg_quality` score 0.45 (scoring) |
| Session cutoff | Non explicite (9:30+) | Encodé en code comme ANY (9:30-15:30) |
| Modèle confirmé | Engulfing retest **obligatoire** | Candle patterns (doji/pin_bar) — différent |

---

## 6. ÉCARTS (Gaps vidéo → code actuel FVG_Fill_Scalp)

### ÉCART E1 — Timeframe Range : 5m vs 15m
- **V054**: Range = 1er candle 5m (9:30-9:35)
- **Code actuel**: setup_tf 5m mais aucun range 5m "premier candle" défini. Le range vient du HTF bias, pas d'un candle d'ouverture.
- **Criticité**: HAUTE — c'est la fondation du setup.

### ÉCART E2 — Timeframe exécution : 1m vs 5m
- **V054**: Tout se passe sur 1m après le range 5m.
- **Code actuel**: `setup_tf: "5m"`, `confirmation_tf: "1m"` — partiellement aligné mais le FVG lui-même est cherché sur 5m, pas 1m.
- **Criticité**: MOYENNE — la logique de détection FVG doit explicitement opérer sur 1m.

### ÉCART E3 — Condition de confirmation : fermeture hors range
- **V054**: Le FVG est validé seulement si **au moins 1 des 3 candles ferme hors range** (au-delà du high ou low du 1er candle 5m).
- **Code actuel**: Pas de vérification "fermeture hors range" dans la logique FVG. Le FVG est détecté par gap géométrique sans condition de position relative au range.
- **Criticité**: HAUTE — c'est le gate principal de filtrage direction.

### ÉCART E4 — Type d'entrée : market vs limit
- **V054**: Entrée **market** à la clôture du candle engulfant le retest.
- **Code actuel**: `type: "LIMIT"`, `zone: "fvg_50"` — entrée passive au milieu du FVG.
- **Criticité**: HAUTE — logique d'entrée fondamentalement différente.

### ÉCART E5 — SL placement : retest candle vs candle 1 FVG
- **V054 Model 1**: SL = 1 tick sous **low du retest candle** (le candle qui revient dans le FVG).
- **Code actuel**: `distance: "fvg_extreme"` = sous le candle 1 du FVG — ce qui correspond au Model 2 de V054, pas au Model 1.
- **Criticité**: MOYENNE — le code implémente accidentellement le SL du Model 2 sans implémenter le Model 2.

### ÉCART E6 — TP : 3:1 fixe vs 1.5+2.0 dual TP
- **V054**: TP unique à **3:1 fixe** (Model 1) ou trailing après 3:1 (Model 2).
- **Code actuel**: `tp1_rr: 1.5`, `tp2_rr: 2.0`, `breakeven_at_rr: 1.0` — ni 3:1, ni trailing.
- **Criticité**: HAUTE — le RR cible est différent, et le breakeven trigger n'existe pas dans V054.

### ÉCART E7 — Filtre de direction : gate binaire vs scoring
- **V054**: Binaire — FVG hors range = TRADE / pas de FVG hors range = PAS DE TRADE.
- **Code actuel**: `fvg_quality: 0.45` dans un score — approche continue, pas gate binaire.
- **Criticité**: MOYENNE — l'effet filtre existe mais la mécanique est différente.

### ÉCART E8 — Modèle engulfing retest : absent du code
- **V054**: Étape critique = attendre un retest candle PUIS un candle engulfant ce retest candle. Deux candles distincts.
- **Code actuel**: `candlestick_patterns: required_families: [doji, spinning_top, pin_bar]` — patterns de reversal sur le setup candle, pas de logique retest+engulfing séquentielle.
- **Criticité**: HAUTE — la confirmation d'entrée est fondamentalement différente.

### ÉCART E9 — Model 2 (Expanding Market) : non implémenté
- **V054**: Expose un second modèle avec SL élargi + trailing après 3:1 pour marchés en expansion (news rouge + ATR croissant 3j).
- **Code actuel**: Pas de Model 2, pas de trailing stop, pas de détection "expanding market" (news ou ATR).
- **Criticité**: FAIBLE pour une implémentation initiale. Engine gap.

---

## 7. ENGINE GAPS (ce que le moteur actuel ne peut pas faire)

### ENGINE GAP G1 — Pas de "1er candle 5m range" comme zone nommée
- Le moteur ne définit pas de zone "opening range" basée sur le premier candle d'ouverture. Il n'y a pas de concept `opening_range_high` / `opening_range_low` dans les engines.
- **Fichiers concernés**: `backend/engines/setup_engine.py`, `backend/engines/signal_detector.py`

### ENGINE GAP G2 — Pas de détection FVG sur 1m avec condition "fermeture hors range"
- La détection FVG actuelle est géométrique (gap entre candles) sans vérification de position relative à une zone de référence externe.
- **Fichiers concernés**: `backend/engines/signal_detector.py` (section FVG)

### ENGINE GAP G3 — Pas de logique retest + engulfing séquentielle
- Le moteur détecte des patterns candlestick sur une bougie isolée. Il ne détecte pas la séquence : (1) candle revient dans zone → (2) candle suivant engulf le corps du précédent.
- **Fichiers concernés**: `backend/engines/signal_detector.py`, `backend/engines/setup_engine.py`

### ENGINE GAP G4 — Pas de market order à la clôture
- Le moteur utilise des limit orders. Un mode d'entrée market-at-close (entrer au open du candle suivant) n'est pas implémenté.
- **Fichiers concernés**: `backend/engines/execution_engine.py`

### ENGINE GAP G5 — Pas de trailing stop 1m-candle-by-candle
- Aucun mécanisme de trailing stop où le SL suit le low (ou high) de chaque nouveau candle 1m une fois un niveau cible atteint.
- **Fichiers concernés**: `backend/engines/risk_engine.py`

### ENGINE GAP G6 — Pas de détection "expanding market" (ATR daily trend + news)
- Pas de lecture de l'ATR daily sur N jours consécutifs. Pas d'intégration de calendrier économique (Forex Factory / news rouge).
- **Fichiers concernés**: `backend/engines/context_engine.py` (si existant), sinon nouveau composant requis.

---

## 8. Résumé implémentable (V054 fidèle)

```
TIMEFRAME: 5m (range) → 1m (setup + entrée)
SESSION: 9:30 ET (présence bureau) — cutoff 12:00 ET (par analogie V065)

STEP 1: Marquer high/low du 1er candle 5m (9:30-9:35)
         opening_range_high = candle[9:30-9:35].high
         opening_range_low  = candle[9:30-9:35].low

STEP 2: Sur 1m, détecter FVG tel que :
         - Au moins 1 des 3 candles du triplet ferme AU-DELÀ de opening_range_high (LONG)
           ou EN-DESSOUS de opening_range_low (SHORT)
         - Si aucun FVG valide → NO TRADE (gate binaire)
         - Direction = sens du break

STEP 3 — MODEL 1 (défaut) :
         - Attendre retest candle (marché revient dans le FVG)
         - Attendre candle engulfant le body du retest candle
         - À la clôture du candle engulfant → MARKET ORDER
         - SL = 1 tick sous low du retest candle (LONG) / 1 tick au-dessus high (SHORT)
         - TP = 3:1 RR fixe
         - Set and forget

STEP 3 — MODEL 2 (expanding market uniquement) :
         - Même entrée que Model 1
         - SL = sous le gap candle du FVG (SL plus large)
         - Pas de TP fixe → trailer le SL sous chaque candle 1m dès que 3:1 est dépassé

EXPANDING MARKET FILTER :
         - Red folder news ce jour (Forex Factory) OU
         - ATR daily croissant sur 3+ jours consécutifs

FILTRES :
         - FVG hors range obligatoire (gate binaire)
         - Fenêtre 9:30-12:00 ET
         - 1 trade max par jour (implicite : 1 range, 1 direction)
```

---

## 9. Vérifications requises avant implémentation

| # | Point | Ligne TXT | Bloquant? |
|---|-------|-----------|-----------|
| 1 | Confirmer que le cutoff 12:00 s'applique à V054 | Non mentionné | Non (appliquer par analogie V065) |
| 2 | Définition exacte "engulfing" : body only ou body+wick? | L32635-32637 | Non — TXT dit "body was fully engulfed" → body only |
| 3 | Seuil ATR "increasing" : strict ou rolling? | L32737-32738 | Oui — nécessite calibration |
| 4 | Taille minimum FVG? | L32667 "small FVGs count" | Non — pas de seuil = accepter tout |
| 5 | Model 2 SL : sous gap candle = sous low du candle du milieu du triplet? | L32698-32699 | Non — TXT suffit |
| 6 | Confirmer 1 trade/jour max ou multiple setups possibles | Non explicite | Non — 1 range = 1 direction = 1 trade |

**Verdict**: V054 est hautement codable. Les 8 règles principales sont claires dans le transcript. Les deux points vraiment flous (seuil ATR, taille FVG) ne bloquent pas l'implémentation du noyau (Model 1 sans Model 2).
