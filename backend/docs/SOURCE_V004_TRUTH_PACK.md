# Source Truth Pack — VIDEO 004 "Copy My Simple Order Block Strategy You've Never Seen Before"

**Video file**: `videos/Copy My Simple Order Block Strategy You've Never Seen Before-ohgTRJLd1gQ.mp4`
**Transcript**: `MASTER_FINAL.txt` L1272-2172
**Quality**: HAUTE (80% codable)
**Role in roadmap**: Stratégie OB Retest pro-trend — S9 dans le triage MASTER

---

## 1. Regles mecaniques extraites

### REGLE 1 — Direction : Follow the Money (pro-trend obligatoire)
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L1391-L1468
- **Verbatim**: "follow the money is only trading from order blocks that are pro-trend" (L1395) / "Do not try to trade against the trend." (L1415) / "Always, always, always follow the money." (L1465-L1468)
- **Formulation normalisee**:
  1. Identifier la structure **swing** sur le HTF (Daily/4H/1H).
  2. Etablir le biais directionnel : higher highs + higher lows = BULLISH ; lower highs + lower lows = BEARISH.
  3. **Seuls les OB pro-trend sont valides.** Un OB bearish dans un marche bullish = IGNORE.
- **Gate binaire**: Si le biais HTF est bullish, seuls les OB bullish (demand zones) sont valides. Si bearish, seuls les OB bearish (supply zones).
- **Verbatim cle**: "Make sure you are using external structure." (L1431) — utiliser la structure swing externe, pas les micro-shifts internes.

---

### REGLE 2 — Types d'Order Blocks (3 variations)
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L1327-L1355
- **Verbatim**: "the three different types of order blocks that exist" (L1286)
- **Formulation normalisee**:
  1. **Type 1 — Final sell-to-buy** (bullish) / **final buy-to-sell** (bearish) : Le dernier candle oppose avant le mouvement agressif. (L1331-L1338)
  2. **Type 2 — Multi-candle formation** : Meme logique mais le candle oppose fait partie d'une sequence multi-candle. Seul le candle oppose est utilise comme OB. (L1343-L1347)
  3. **Type 3 — First candle of momentum** : Le premier candle qui lance le leg de momentum. (L1348-L1351)
- **Note**: "not one is better than the other. All are completely valid order blocks." (L1352-L1353)
- **Condition FVG associee**: "all good order blocks should leave an area of market inefficiency" (L1332) — un FVG doit etre present apres l'OB.

---

### REGLE 3 — FVG obligatoire comme validation de l'OB
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L1332-L1337
- **Verbatim**: "all good order blocks should leave an area of market inefficiency [...] the first candle high [...] and the third candle low [...] does not touch this high and it creates a gap in the market. That is what we obviously call a fair value gap"
- **Formulation normalisee**: Un OB valide **doit** laisser un FVG (gap entre high du candle 1 et low du candle 3 dans un triplet bullish, ou inverse pour bearish). Un OB sans FVG = OB faible.
- **Gate binaire**: OB sans FVG = NON VALIDE pour cette strategie.

---

### REGLE 4 — Avoid the Traps (filtre de liquidite)
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L1546-L1730
- **Verbatim**: "A trap for me is an area of liquidity that you're expecting price to trade into." (L1563-L1565) / "order blocks at these levels, they just don't work." (L1729-L1730)
- **Formulation normalisee**:
  1. Identifier les zones de liquidite **entre** le prix actuel et l'OB candidat :
     - Equal highs / equal lows (L1567, L1571)
     - Trendline liquidity (L1568)
     - Asia session high/low (L1573-L1574)
     - Previous day's high/low (L1577-L1579)
  2. Si une zone de liquidite se situe **entre** le prix et l'OB candidat, cet OB sera probablement traverse. Le **rejeter**.
  3. Utiliser l'OB qui se situe **au-dela** de la liquidite (apres le sweep).
- **Gate binaire**: OB avec liquidite visible entre le prix et l'OB = NE PAS TRADER cet OB.
- **Verbatim cle**: "I am a buyer as long as we trade below this level" (L1699-L1700) — attendre que la liquidite soit prise avant d'entrer.

---

### REGLE 5 — Confirmation : Order Flow Shift sur 1m (steroids)
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L1806-L1900
- **Verbatim**: "I'm waiting for a pullback into here and a shift above this high. [...] That's my confirmation that this is the order block that I'm going to use." (L1813-L1821)
- **Formulation normalisee**:
  1. Le prix arrive dans la zone de l'OB (HTF).
  2. Sur le **1m**, la structure est **bearish** (pullback en cours).
  3. Attendre un **shift de structure 1m** : break du dernier swing high 1m (pour un long) ou swing low 1m (pour un short).
  4. Ce shift = confirmation que l'OB tient. **Sans ce shift, pas d'entree.**
- **Verbatim cle**: "bearish structure on the one minute timeframe, flipped to bullish structure on the one minute timeframe. And then I just trade the one minute timeframe." (L1895-L1899)
- **TF fractale**: "I use the 15 minute and the one minute as fractals together." (L1900-L1901) — le setup est vu sur 15m, la confirmation sur 1m.

---

### REGLE 6 — Entree : OB 1m post-shift (refined entry)
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L1822-L1845, L2028-L2034
- **Verbatim**: "I can wait for this [...] I can just use the order block from this level. And so I can just be a buyer from here" (L1835-L1839) / "This sell to buy, you can encompass them both. Long position. Entry there." (L2029-L2032)
- **Formulation normalisee**:
  1. Apres le shift 1m, identifier l'OB **1m** qui a cree le shift (le sell-to-buy ou buy-to-sell sur 1m).
  2. Entrer sur cet OB 1m (pas l'OB HTF).
  3. Ceci donne un SL beaucoup plus serre et un RR beaucoup plus eleve.
- **Avantage RR**: "your one to two risk to reward for me is a one to nine risk to reward" (L1843-L1844)

---

### REGLE 7 — Stop Loss : sous le low du shift 1m
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L1840-L1841, L2033
- **Verbatim**: "I can put my stop loss at this low." (L1841) / "Stop loss goes below this low" (L2033)
- **Formulation normalisee**: SL = sous le low du swing qui a precede le shift 1m (pour un long). Ce low est le dernier swing low 1m avant le BOS bullish.

---

### REGLE 8 — Take Profit : partiel echelonne (5R, 7R, full)
- **Classification**: HEURISTIQUE A VALIDER
- **Source TXT**: L2039-L2044, L2059-L2083
- **Verbatim**: "I cut some off at 5R, some off at 7R, and then some off at the full take profit." (L2040-L2041)
- **Formulation normalisee**:
  1. **TP1** = 5R — fermer ~50% de la position.
  2. **TP2** = 7R — fermer ~25%.
  3. **TP3** = swing high/low HTF (target structure) — fermer les 25% restants.
- **Note**: "I have a final 25% to run to this high." (L2082) — le dernier morceau vise le swing HTF.
- **Classification HEURISTIQUE** car les pourcentages exacts (50/25/25) sont inferres du contexte, pas explicitement chiffres.

---

### REGLE 9 — Timeframes : HTF bias + 15m setup + 1m execution
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L1399-L1401 (HTF structure), L1900-L1901 (fractal 15m/1m), L1811 (1m order flow), L2021 (5m/3m alternative)
- **Verbatim**: "I use the 15 minute and the one minute as fractals together." (L1900-L1901)
- **Formulation normalisee**:
  - **HTF bias** : Daily / 4H / 1H — structure swing (higher highs/lows ou lower highs/lows).
  - **Setup TF** : 15m — identifier l'OB pro-trend avec FVG.
  - **Confirmation TF** : 1m — attendre le shift de structure.
  - **Entry TF** : 1m (ou 5m/3m comme alternative — L2021-L2025).
- **Note**: "I usually use the five minute timeframe. But on this instance, there's not really an order block in here. It actually looks quite messy. So you can use a three minute timeframe or whatever minute timeframe." (L2021-L2026) — la TF d'entree est flexible.

---

### REGLE 10 — Session : London sweep + NY entry
- **Classification**: HEURISTIQUE A VALIDER
- **Source TXT**: L1685-L1716
- **Verbatim**: "Coming into London session." (L1685) / "And then New York comes, we go for one more sweep of that low." (L1713-L1714)
- **Formulation normalisee**: Le modele typique montre un sweep de liquidite en **London** (Asia lows) puis une entree en **NY** apres le shift 1m. Pas de cutoff explicite mentionne.
- **Classification HEURISTIQUE** car la session n'est pas imposee comme gate rigide.

---

## 2. Elements HEURISTIQUES (a valider)

### HEURISTIQUE 1 — Taille minimum de l'OB
- **Classification**: HEURISTIQUE A VALIDER
- **Source TXT**: Non mentionnee
- **Probleme**: Aucun seuil minimum de taille d'OB n'est defini. Le trader parle d'"area" sans quantifier.
- **A calibrer**: OB >= X% de l'ATR du TF de reference.

### HEURISTIQUE 2 — Nombre d'OB candidats
- **Classification**: HEURISTIQUE A VALIDER
- **Source TXT**: L1769-L1804
- **Verbatim**: "maybe you have two order blocks [...] Do you just choose one and forget the other?" (L1771-L1775)
- **Probleme**: Le trader utilise la confirmation 1m pour discriminer entre OB candidats multiples. Mais si deux OB donnent un shift, lequel choisir ?
- **Reponse implicite**: L'OB le plus bas (pro-trend bullish) ou le plus haut (pro-trend bearish) = meilleur RR. Mais ceci est infere, pas explicite.

### HEURISTIQUE 3 — Definition precise du BOS 1m
- **Classification**: HEURISTIQUE A VALIDER
- **Source TXT**: L1895-L1899
- **Probleme**: "shift above this high" — un close au-dessus ou un wick suffit ? Le trader dit "wick of this high which doesn't count as a break" (L1489) ce qui suggere que seul un **close** au-dela du swing high/low compte comme BOS.
- **A calibrer**: BOS 1m = close au-dela du dernier swing high/low 1m (pas juste wick).

---

## 3. Contexte discretionnaire (non codable mais informatif)

- **Philosophie**: "Trading actually isn't that hard." (L1991) — le trader insiste sur la simplicite : 3 regles + confirmation = systeme.
- **Frequence**: Le trade exemple (L1910-L2170) montre un trade par jour, tenu de quelques minutes (5R en 10 minutes) a overnight pour le TP final.
- **Instruments mentionnes**: Forex (EURUSD mentionne L1302), mais le trade en live est sur un instrument non specifie (probablement indices ou forex).
- **Inner Circle / mentorship**: Le trade est execute en live avec des etudiants. Non auditable.
- **Taille de compte**: "On half a million dollar account, risking 1%" (L2111-L2112) — contexte prop firm / funding.

---

## 4. Bruit / marketing (ignore)

- L1275-L1293 : Intro storytelling / hook ("99% of traders")
- L1288-L1292 : Credibilite personnelle ("years and years of data", "hundreds of trades")
- L1656-L1672 : Plug Prosperity School / Inner Circle
- L2087-L2095 : Plug etudiants / live trading
- L2108-L2122 : Flex capital ($500K, $12,500 en 10 min)
- L2166-L2172 : Outro / CTA

---

## 5. Pseudo-code du flux d'execution

```
FUNCTION ob_retest_strategy(market_data):

    # === STEP 1: HTF BIAS (Daily / 4H / 1H) ===
    htf_structure = identify_swing_structure(tf="1H")  # or D/4H
    IF htf_structure == UPTREND:
        bias = LONG
    ELIF htf_structure == DOWNTREND:
        bias = SHORT
    ELSE:
        RETURN NO_TRADE  # no clear trend

    # === STEP 2: IDENTIFY OB CANDIDATES (15m) ===
    ob_candidates = find_order_blocks(tf="15m", direction=bias)
    # Types: final_sell_to_buy, multi_candle, first_momentum_candle
    # Filter: must have associated FVG
    ob_candidates = [ob FOR ob IN ob_candidates IF has_fvg(ob)]

    IF len(ob_candidates) == 0:
        RETURN NO_TRADE

    # === STEP 3: AVOID TRAPS — LIQUIDITY FILTER ===
    FOR each ob IN ob_candidates:
        liquidity_zones = find_liquidity_between(current_price, ob.zone)
        # equal highs/lows, Asia hi/lo, prev day hi/lo, trendline liq
        IF len(liquidity_zones) > 0:
            MARK ob AS TRAPPED
    
    valid_obs = [ob FOR ob IN ob_candidates IF NOT ob.TRAPPED]
    IF len(valid_obs) == 0:
        RETURN NO_TRADE

    # === STEP 4: WAIT FOR PRICE TO REACH OB ===
    WAIT UNTIL price enters valid_obs[0].zone  # deepest OB preferred

    # === STEP 5: 1m ORDER FLOW SHIFT (confirmation) ===
    MONITOR 1m_structure:
        # Price arriving at OB => 1m is bearish (for longs) or bullish (for shorts)
        IF bias == LONG:
            WAIT UNTIL 1m_BOS_bullish  # close above last 1m swing high
        ELIF bias == SHORT:
            WAIT UNTIL 1m_BOS_bearish  # close below last 1m swing low

    IF no_shift_detected:
        RETURN NO_TRADE  # OB failed, price traded through

    # === STEP 6: ENTRY on 1m OB post-shift ===
    entry_ob = find_1m_order_block_at_shift_origin()
    entry_price = entry_ob.zone  # buy at the 1m OB that caused the shift

    # === STEP 7: SL & TP ===
    IF bias == LONG:
        stop_loss = shift_swing_low - 1_tick  # low before the 1m BOS
    ELIF bias == SHORT:
        stop_loss = shift_swing_high + 1_tick

    risk = abs(entry_price - stop_loss)
    tp1 = entry_price + 5 * risk   # 50% position
    tp2 = entry_price + 7 * risk   # 25% position
    tp3 = htf_swing_target          # 25% position (structure target)

    EXECUTE trade(entry_price, stop_loss, [tp1, tp2, tp3])
```

---

## 6. Comparaison V004 vs playbooks existants

### V004 vs `Trend_Continuation_FVG_Retest` (le plus proche)

| Dimension | V004 (OB Retest) | Trend_Continuation_FVG_Retest |
|-----------|-------------------|-------------------------------|
| Concept | OB pro-trend + FVG + 1m shift confirmation | FVG retest pro-trend |
| TF Bias | D/4H/1H (swing structure) | HTF bias (htf_bias_allowed) |
| TF Setup | **15m** (OB + FVG) | **5m** (confirmation_tf: 5m) |
| TF Entry | **1m** (shift + refined OB) | **5m** (limit a fvg_50) |
| Confirmation | **1m BOS** (structure shift) | Candlestick patterns (pin_bar, doji, engulfing) |
| Filtre liquidite | **Trap avoidance** (liq zones) | Aucun filtre liquidite |
| Entree | OB 1m post-shift (refined) | LIMIT a 50% du FVG |
| SL | Sous swing low 1m pre-shift | fvg_low_high + 2 ticks |
| TP | **5R / 7R / structure** (partiel) | 3R / 5R + BE a 1.5R |
| FVG role | Validation de l'OB (gate) | Zone d'entree (le FVG est le trade) |

### V004 vs `HTF_Bias_15m_BOS` (overlap structural)

| Dimension | V004 (OB Retest) | HTF_Bias_15m_BOS |
|-----------|-------------------|-------------------|
| Concept | OB pro-trend + FVG + 1m shift | HTF bias + 15m BOS after sweep |
| TF Setup | **15m** | **15m** |
| TF Entry | **1m** | **1m** |
| Sweep required | Non obligatoire (trap avoidance) | **Oui** (require_sweep: true) |
| BOS required | **Oui** (1m shift = BOS 1m) | **Oui** (require_bos: true, mais sur 15m) |
| OB role | **Central** — l'OB est la zone de trade | Absent — zone = fvg_retest |
| Filtre liquidite | **Trap avoidance** (explicite) | Aucun |
| Entree | OB 1m post-shift (market) | LIMIT a fvg_retest |
| SL | Sous swing low 1m | Sous recent_swing + 3 ticks |
| TP | 5R / 7R / structure | 3R / 5R + BE a 1.5R |

**Synthese** : V004 partage la hierarchie TF avec `HTF_Bias_15m_BOS` (15m setup / 1m entry) mais la logique d'entree est fondamentalement differente. V004 est centre sur l'OB (zone), `HTF_Bias_15m_BOS` est centre sur le BOS 15m + FVG. Le filtre "trap avoidance" de V004 n'existe dans aucun playbook actuel.

---

## 7. ECARTS (Gaps video -> code actuel)

### ECART E1 — Concept OB absent du moteur
- **V004**: L'Order Block est le concept central — zone definie par le dernier candle oppose avant un mouvement agressif + FVG.
- **Code actuel**: Aucun playbook n'a de concept `order_block` explicite. Les OB ne sont ni detectes ni representes comme entites dans `signal_detector.py` ou `setup_engine.py`. Le plus proche est `fvg_50` (zone FVG) qui n'est pas un OB.
- **Criticite**: HAUTE — concept fondamental absent.

### ECART E2 — Filtre "Trap Avoidance" (liquidity filter) absent
- **V004**: Gate binaire — si une zone de liquidite (equal highs/lows, Asia hi/lo, prev day hi/lo) se situe entre le prix et l'OB, rejeter l'OB.
- **Code actuel**: Aucun playbook ne filtre les zones de liquidite comme "traps". `require_sweep: true` verifie qu'un sweep a eu lieu, mais ne filtre pas les OB par position relative a la liquidite.
- **Criticite**: HAUTE — le trader insiste que c'est la regle #2 la plus critique.

### ECART E3 — Confirmation 1m BOS (order flow shift)
- **V004**: La confirmation est un **break of structure 1m** = close au-dela du dernier swing high/low 1m dans la direction du biais.
- **Code actuel**: Les confirmations sont des candlestick patterns (doji, pin_bar, engulfing) ou des scoring continus. Aucun playbook n'utilise un BOS 1m comme gate de confirmation.
- **Criticite**: HAUTE — logique de confirmation fondamentalement differente.

### ECART E4 — Entree refined (OB 1m post-shift vs OB HTF)
- **V004**: Apres le shift 1m, l'entree se fait sur l'OB **1m** qui a genere le shift, pas sur l'OB HTF. Cela donne un SL tres serre et un RR tres eleve (9:1 au lieu de 2:1).
- **Code actuel**: Toutes les entrees sont sur la zone du setup TF (fvg_50, pattern_close, etc.), pas sur une zone "refined" derivee de la confirmation.
- **Criticite**: HAUTE — c'est le "secret weapon" du trader, la source du RR superieur.

### ECART E5 — TP echelonne 5R/7R/structure
- **V004**: 3 niveaux de TP : 5R (50%), 7R (25%), swing HTF (25%).
- **Code actuel**: Maximum 2 niveaux de TP (tp1_rr, tp2_rr) + breakeven. Aucun playbook n'a de 3eme TP visant une structure HTF.
- **Criticite**: MOYENNE — le moteur supporte 2 TP, pas 3.

### ECART E6 — BOS definition : close only, wick excluded
- **V004**: "A wick of this high which doesn't count as a break." (L1489)
- **Code actuel**: La definition de BOS dans le moteur n'est pas explicitement close-only vs wick. A verifier dans `signal_detector.py`.
- **Criticite**: FAIBLE — probablement deja le cas mais a confirmer.

---

## 8. ENGINE GAPS (ce que le moteur actuel ne peut pas faire)

### ENGINE GAP G1 — Pas de detection d'Order Block
- Le moteur ne detecte pas les OB (final sell-to-buy, first momentum candle, multi-candle). Il n'y a pas d'entite `order_block` avec les attributs `zone_high`, `zone_low`, `type`, `associated_fvg`.
- **Fichiers concernes**: `backend/engines/signal_detector.py`, `backend/engines/setup_engine.py`

### ENGINE GAP G2 — Pas de filtre "trap avoidance" (liquidite relative)
- Le moteur ne peut pas evaluer si une zone de liquidite (equal highs/lows, session hi/lo, prev day hi/lo) se situe entre le prix courant et une zone de setup candidate, pour rejeter cette zone.
- **Fichiers concernes**: `backend/engines/context_engine.py`, `backend/engines/setup_engine.py`

### ENGINE GAP G3 — Pas de BOS 1m comme gate de confirmation
- Le moteur detecte des BOS (`require_bos: true`) mais pas specifiquement un BOS 1m **apres** que le prix ait atteint une zone HTF. La logique est : detecter BOS sur le setup TF, pas "attendre BOS 1m dans une zone HTF predeterminee".
- **Fichiers concernes**: `backend/engines/signal_detector.py`, `backend/engines/setup_engine.py`

### ENGINE GAP G4 — Pas d'entree "refined" (OB 1m post-shift)
- Le moteur n'a pas de concept d'entree derivee d'une confirmation LTF. L'entree est toujours sur la zone du setup (fvg_50, pattern_close, etc.), jamais sur un OB 1m identifie pendant la confirmation.
- **Fichiers concernes**: `backend/engines/execution_engine.py`

### ENGINE GAP G5 — Pas de TP a 3 niveaux
- Le moteur supporte `tp1_rr` et `tp2_rr`. Il n'y a pas de `tp3` ni de concept "structure target" (viser un swing high/low HTF comme TP final).
- **Fichiers concernes**: `backend/engines/risk_engine.py`

### ENGINE GAP G6 — Pas de detection de zones de liquidite (equal highs/lows, session extremes)
- Le moteur ne calcule pas les equal highs/equal lows comme zones de liquidite. Les session highs/lows (Asia, London, prev day) ne sont pas representes comme entites nommees consultables par les playbooks.
- **Fichiers concernes**: `backend/engines/context_engine.py`, `backend/engines/signal_detector.py`

---

## 9. Resume implementable (V004 fidele)

```
TIMEFRAMES: D/4H/1H (bias) -> 15m (setup OB) -> 1m (confirmation + entry)
SESSION: Typiquement NY open apres sweep London. Pas de cutoff explicite.

STEP 1 — HTF BIAS:
    Identifier structure swing sur D/4H/1H
    higher highs + higher lows => LONG
    lower highs + lower lows  => SHORT
    pas de trend clair        => NO TRADE

STEP 2 — IDENTIFIER OB 15m:
    Trouver OB pro-trend sur 15m:
      - Type 1: final sell-to-buy (bullish) ou buy-to-sell (bearish)
      - Type 2: multi-candle, utiliser le candle oppose
      - Type 3: first candle of momentum
    Gate: OB doit avoir un FVG associe (gap entre C1.high et C3.low)
    Si aucun OB valide avec FVG => NO TRADE

STEP 3 — TRAP AVOIDANCE:
    Lister les zones de liquidite entre prix et OB:
      - Equal highs / equal lows
      - Asia session high/low
      - Previous day high/low
      - Trendline liquidity
    Si liquidite visible entre prix et OB => REJETER cet OB
    Utiliser l'OB au-dela de la liquidite

STEP 4 — ATTENDRE PRIX DANS L'OB:
    Le prix doit atteindre la zone de l'OB 15m

STEP 5 — CONFIRMATION 1m (order flow shift):
    Sur 1m, le prix est en structure opposee au bias (pullback)
    Attendre BOS 1m dans la direction du bias:
      LONG: close au-dessus du dernier swing high 1m
      SHORT: close en-dessous du dernier swing low 1m
    Si pas de shift => OB echoue => NO TRADE

STEP 6 — ENTRY REFINED:
    Identifier l'OB 1m qui a cree le shift (sell-to-buy ou buy-to-sell sur 1m)
    Entrer sur cet OB 1m (refined entry)

STEP 7 — SL & TP:
    SL = sous le swing low 1m qui a precede le BOS (LONG) + 1 tick
         au-dessus du swing high 1m (SHORT) + 1 tick
    TP1 = 5R  (fermer ~50%)
    TP2 = 7R  (fermer ~25%)
    TP3 = swing HTF target (fermer ~25%)

FILTRES:
    - Pro-trend obligatoire (gate binaire)
    - FVG associe a l'OB (gate binaire)
    - Trap avoidance (gate binaire)
    - 1m BOS confirmation (gate binaire)
    - 1 trade par OB (implicite)
```

---

## 10. Verifications requises avant implementation

| # | Point | Ligne TXT | Bloquant? |
|---|-------|-----------|-----------|
| 1 | Definition exacte BOS 1m : close only? | L1489 "wick doesn't count as break" | Non — close only confirme |
| 2 | Session cutoff ? | Non mentionne | Non — appliquer NY (9:30-16:00) par defaut |
| 3 | Quelle TF exacte pour le bias HTF ? D, 4H, 1H ? | L1399-L1401 (swing structure) | Oui — a calibrer |
| 4 | Taille minimum OB ? | Non mentionnee | Non — pas de seuil = accepter tout avec FVG |
| 5 | Proportions exactes TP echelonne (50/25/25) ? | L2040-L2082 (infere) | Non — proxy raisonnable |
| 6 | OB 1m refined : limit ou market entry ? | L2028-L2032 | Oui — le texte montre limit sur l'OB mais pas explicite |
| 7 | Multi-OB : comment choisir entre OB1 et OB2 ? | L1769-L1804 | Non — le shift 1m tranche |

**Verdict**: V004 est hautement codable pour le noyau (Steps 1-5-6-7). Les 4 gates binaires (pro-trend, FVG, trap avoidance, 1m BOS) sont clairs. Le principal obstacle est l'absence totale de detection d'Order Block et de filtre trap avoidance dans le moteur actuel (ENGINE GAPS G1, G2, G4).
