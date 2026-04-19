# Source Truth Pack — VIDEO 064 & 068 — Strategy S10 (HTF AOI Engulfing)

**V064**: "This 1 Hour Day Trading Strategy Works Every Day ($1,000/day)"
**V068**: "This Trading Strategy Made Me $54,000 In Just 24 Hours"
**Transcript**: `MASTER_FINAL.txt` V064 L44421-44681, V068 L45846-46122
**Quality**: MOYENNE (65% codable) — checklist-driven mais beaucoup de scoring subjectif
**Role in roadmap**: Nouvelle stratégie S10 — HTF Trend + AOI + Rejection Engulfing
**Famille**: Set-and-forget engulfing at HTF supply/demand zones

---

## PARTIE A — VIDEO 064

---

## 1. Regles mecaniques extraites (V064)

### REGLE 1 — Trend 4H + 1H alignes (Confluence 1+2)
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L44480-44503
- **Verbatim**: "the first confluence is going to be the trend and we're going to be looking for the trend on the four hour and on the two hour [...] we have the trend on the four hour and we have the trend on the one hour"
- **Formulation normalisee**:
  1. Sur le chart **4H**, identifier la structure de prix : Lower Highs + Lower Lows = bearish, Higher Highs + Higher Lows = bullish.
  2. Sur le chart **1H**, confirmer la meme direction.
  3. Les deux TF doivent etre alignes. Si discordants, la confluence est reduite.
- **Scoring auteur**: 5% par TF (total 10% quand les deux sont alignes).
- **Note**: L44481 mentionne "four hour and on the two hour" puis corrige en "four hour and the one hour" (L44482). Le systeme utilise 4H + 1H.

---

### REGLE 2 — Area of Interest (AOI) avec minimum 3 touches (Confluence 3+4)
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L44505-44536
- **Verbatim**: "an area of interest we want to make sure that has a minimum of three touches above or below" (L44511)
- **Formulation normalisee**:
  1. Identifier une zone de support/resistance sur **4H** avec **minimum 3 touches**.
  2. Le prix doit etre **a** l'AOI (pas en route vers). Si le prix n'est pas encore a l'AOI → PAS DE TRADE.
  3. Confirmer la meme AOI sur **1H** (minimum 3 touches aussi).
- **Gate binaire**: Le prix DOIT etre a l'AOI. "if we are not at the area of interest we cannot take the trade" (L44536).
- **Scoring auteur**: 5% pour AOI 4H + 5% pour AOI 1H (total 10%).
- **Verbatim cle**: "we have one tap two taps three taps four taps so when I see this market break under and that is then going to retest this area that is a solid confirmation" (L44513-44515)

---

### REGLE 3 — Candlestick Rejection sur meme TF que AOI (Confluence 5+6)
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L44537-44577
- **Verbatim**: "the candlestick rejection is the confirmation that we are rejecting the area of interest [...] you want to make sure that the area of interest and the candlesticks be the exact same time frame" (L44538-44543)
- **Formulation normalisee**:
  1. Sur **4H** : observer un pattern de rejection a l'AOI 4H. Patterns valides : **double doji**, **bearish engulfing**, wick rejection.
  2. Sur **1H** : observer egalement une rejection (engulfing, doji) a l'AOI 1H.
  3. La rejection DOIT etre sur le MEME TF que l'AOI. Exemple invalide : AOI 4H + rejection 30m seulement (L44543-44544).
- **Gate binaire**: "without any confirmation of a rejection I am not interested in entering the trade" (L44549-44550)
- **Scoring auteur**: 10% par TF (total 20%).

---

### REGLE 4 — Entry Signal : Engulfing ou Doji sur 1H/30m (Confluence 7)
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L44582-44594
- **Verbatim**: "a bearish engulfing candlestick or a doji rejection [...] You have an entry signal on either the one hour time frame or the 30 minute time frame" (L44587-44589)
- **Formulation normalisee**:
  1. Apres les confluences trend + AOI + rejection validees, attendre un **signal d'entree** sur **1H ou 30m**.
  2. Patterns d'entree valides : **bearish/bullish engulfing** ou **doji rejection**.
  3. Entrer a la cloture du candle signal.
- **Note**: Le passage au 30m est optionnel pour obtenir un "sniper entry" avec meilleur RR (L44589-44590).
- **Scoring auteur**: 10% pour l'entry signal.

---

### REGLE 5 — Stop Loss : 10-15 pips au-dela du high/low recent
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L44595-44620
- **Verbatim**: "our stop loss we want to make sure that we can give it anywhere from 10 to 15 pips from the previous high" (L44595-44596)
- **Formulation normalisee**:
  1. Identifier le high (SHORT) ou low (LONG) de la zone de retracement/AOI.
  2. Placer le SL a **10-15 pips au-dela** de ce niveau.
  3. Justification : eviter les liquidity grabs / faux breakouts (L44605-44608).
- **Exemple concret** : "20 pips right here. We want to make it roughly around 30 and that is a beautiful breathing room" (L44600). Cela implique : high de zone = 20 pips de distance + 10-15 pips de padding = ~30-35 pips SL total.
- **Note**: Le "10-15 pips" est un padding AU-DESSUS du high, pas la distance totale du SL.

---

### REGLE 6 — Take Profit : 1:1.5 min, 1:2 max
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L44621-44632
- **Verbatim**: "my take profit would be set at a minimum of a one to 1.5 max one to two" (L44621)
- **Formulation normalisee**:
  1. TP minimum = **1.5R** (risk-to-reward).
  2. TP maximum = **2R**.
  3. Pas de trailing, pas de TP3.
- **Justification auteur**: "you're trading the session. You don't anticipate for the movement [...] to continue going throughout the next session without having a retracement" (L44623-44625).

---

### REGLE 7 — Session Filter : Pre-London ou Pre-NY uniquement
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L44487-44492
- **Verbatim**: "the only times you're going to implement this trading checklist [...] pre-london session or pre-new york session [...] 9 a.m is the latest time" (L44487-44491)
- **Formulation normalisee**:
  1. Analyse et preparation : **avant** London ou **avant** NY.
  2. Execution : **pendant** London ou **pendant** NY.
  3. Cutoff : **9:00 AM** (non precise si ET ou UTC — probablement ET par contexte).
  4. Jamais apres NY session (pas de volume).
- **Note**: "9 a.m is the latest time" semble etre le dernier moment pour ENTRER, pas pour analyser. Ceci contraint l'entree a la premiere heure de la session.

---

### REGLE 8 — Exit: cloturer en fin de session
- **Classification**: HEURISTIQUE
- **Source TXT**: L44628-44634
- **Verbatim**: "it is very key that you aim to exit your trade at the end of New York session if you entered in London [...] I would not hold throughout the daily candlestick closure" (L44628-44631)
- **Formulation normalisee**:
  1. Si entre en London → sortir fin NY au plus tard.
  2. Si en profit avec continuation daily, option de passer a breakeven et tenir.
  3. Si pas assez en profit → cloturer manuellement, meme en leger drawdown.
- **Classification**: HEURISTIQUE — "pas assez en profit" n'est pas defini quantitativement.

---

### REGLE 9 — Grade minimum : seuil de checklist
- **Classification**: HEURISTIQUE
- **Source TXT**: L44636-44648
- **Verbatim**: "the type of trades that I like to take are anywhere from 80, 90 to 100% [...] this trade would give us a total of a 50%. Now that's not a great type of grade. I would give this anywhere from a D set up max" (L44637-44638)
- **Formulation normalisee**:
  - L'auteur utilise une checklist a pourcentage cumule.
  - Le trade montre (avec les TF basses seulement) = ~50% → grade D.
  - L'auteur prefere 80-100% (grade A+).
  - L'ajout de Weekly + Daily pourrait passer un trade de 30% a 80-90%.
- **Classification**: HEURISTIQUE — les seuils de grades ne sont pas definis numeriquement au-dela de l'exemple.

---

## 2. Elements HEURISTIQUES (V064)

### HEURISTIQUE 1 — Definition "trend" sur 4H/1H
- **Source TXT**: L44495-44499
- **Probleme**: La structure Lower High / Lower Low est visuelle. Combien de swings minimum ? 2 LH+LL suffisent-ils ? Quelle profondeur de lookback ?
- **A calibrer**: Definir un lookback (ex : 20 candles 4H = ~3.3 jours) et un compteur de swings minimum (ex : 2 LH+LL consecutifs).

### HEURISTIQUE 2 — Definition "3 touches" pour AOI
- **Source TXT**: L44511-44514
- **Probleme**: Qu'est-ce qu'un "touch" ? Wick qui touche la zone ? Close dans la zone ? Precision requise sur la tolerance (combien de pips de la zone = un touch).
- **A calibrer**: Touch = wick dans une bande de X pips autour du niveau. Seuil minimum = 3 touches sur le lookback.

### HEURISTIQUE 3 — "Picasso rejection"
- **Source TXT**: L44576
- **Probleme**: Terme non defini. Semble signifier "rejection parfaite visuellement evidente" — c'est subjectif.
- **Classification**: DISCRETIONNAIRE — ne pas coder, utiliser les patterns mecaniques (engulfing, doji) a la place.

---

## 3. Contexte discretionnaire (V064)

- **Frequence annoncee**: 1 trade/jour, 1h par jour, 5h par semaine.
- **Win rate annonce**: "65 to 70 percent" (L44444).
- **RR annonce**: "one-to-one, one-to-one to 1.5" (L44446-44447).
- **Instruments**: Forex principalement (pips = forex). Chart montre un marche forex.
- **Marches scanne**: "10 to 15 different markets every single sunday" (L44523).
- **Grade minimum suggere**: 80%+ pour "trades that I like to take" (L44638).
- **Checklist complete non revelee**: L'auteur dit avoir des confluences cachees pour sa strategie avancee (L44475-44477, L44664-44671).

---

## 4. Bruit / marketing (ignore)

- L44424-44468 : Intro storytelling (pecheur, fee du trading)
- L44556-44564 : Analogie "presenter a grand-pere"
- L44662-44681 : CTA confluence sheet, mentorship plug

---

---

## PARTIE B — VIDEO 068

---

## 5. Regles mecaniques extraites (V068)

### REGLE V068-1 — Engulfing Candlestick : definition stricte
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L45855-45878
- **Verbatim**: "an engulfing candlestick is a candlestick that eats the last two candlestick. It is one candlestick that engulfs the last previous two candlesticks" (L45856-45857)
- **Formulation normalisee**:
  1. **Bullish engulfing** : 2 candles baissiers suivis d'1 candle haussier qui engloble (body depasse) les 2 precedents.
  2. **Bearish engulfing** : 2 candles haussiers suivis d'1 candle baissier qui engloble les 2 precedents.
  3. **Morning star** = variante du bullish engulfing (L45871, L45934).
  4. **Invalide** : si 2 candles mangent 1 candle (L45937-45938). Doit etre **1 seul candle** qui mange **2 candles**.
  5. **Invalide** : si le candle n'englobe pas completement les 2 precedents (L45944-45946).
- **Gate binaire**: Le body du candle engulfing doit depasser le body des 2 candles precedents. Sinon → PAS VALIDE.

---

### REGLE V068-2 — Engulfing doit etre a un niveau S/R fort (4H)
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L45889-45916
- **Verbatim**: "This engulfing candlestick has to be used correctly at a strong area of interest or at a strong supply and demand zone or at a strong support and resistance" (L45889-45891)
- **Formulation normalisee**:
  1. L'engulfing doit se produire a un **niveau 4H de support/resistance** (L45957-45958).
  2. Le niveau doit avoir **plus de 3 touches** (L45968-45969).
  3. Un engulfing en milieu de chart sans contexte S/R = **INVALIDE** (L45883-45900, L46067-46075).
- **Gate binaire**: "If we are not at a strong support or resistance level, do not use the engulfing" (paraphrase L45905-45916).
- **Direction**: Bullish engulfing → doit etre AU-DESSUS d'un support (L46061-46062). Bearish engulfing → doit etre EN-DESSOUS d'une resistance (L46063-46064).

---

### REGLE V068-3 — Timeframes : 4H zone → 30m/15m entree
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L45972-45974
- **Verbatim**: "once you find this strong level of support and resistance, I go to the lower timeframe, such as a 30 minute, 15 minute, and I'm looking for this bullish engulfing candlestick" (L45972-45974)
- **Formulation normalisee**:
  1. Zone identifiee sur **4H** (daily aussi mentionne pour TP — L46002).
  2. Entree sur **30m ou 15m** via engulfing.
  3. Pas de mention de 1H trend check dans V068 (contrairement a V064).

---

### REGLE V068-4 — Entree : a la cloture du candle engulfing
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L45977-45979
- **Verbatim**: "placed my entry as soon as that candlestick closed" (L45979)
- **Formulation normalisee**: Market order a la cloture du candle engulfing sur 30m/15m.

---

### REGLE V068-5 — Stop Loss : sous le low des 2 derniers candles + breathing room
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L45980-45986
- **Verbatim**: "I put my stop loss right under the low of the last two candlesticks. And I give it some breathing room, just in case if it needs to come back and then create some type of wake" (L45980-45983)
- **Formulation normalisee**:
  1. SL = sous le **low des 2 candles precedant l'engulfing** (les candles "manges").
  2. + breathing room (non quantifie — equivalent au "10-15 pips" de V064).

---

### REGLE V068-6 — Take Profit : structure level sur Daily/HTF
- **Classification**: HEURISTIQUE
- **Source TXT**: L46001-46021
- **Verbatim**: "my first take profit was this structure level right here on the daily timeframe, which was the high of this wick" (L46001-46003)
- **Formulation normalisee**:
  1. TP1 = prochain niveau de structure sur le meme TF que l'entree (30m) ou le daily.
  2. TP2 (optionnel) = prochain niveau HTF de S/R.
  3. Possibilite de hold en swing si le chemin est libre (L46012-46021).
- **Classification**: HEURISTIQUE — le TP depend de l'identification visuelle de "structure levels" et de la decision de hold vs close.

---

### REGLE V068-7 — Invalidation : engulfing contre la zone
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L46046-46064
- **Verbatim**: "You literally just bought right at a resistance level [...] That is why it's so key to enter the trade at a very key support or resistance level" (L46047-46051)
- **Formulation normalisee**:
  1. **NE PAS** acheter un bullish engulfing si le prix est a une resistance (= engulfing VERS la resistance).
  2. **NE PAS** vendre un bearish engulfing si le prix est a un support.
  3. Bullish engulfing = valide seulement **au-dessus d'un support** (rebond).
  4. Bearish engulfing = valide seulement **en-dessous d'une resistance** (rejection).

---

### REGLE V068-8 — Filtre taille engulfing : doit manger 2 candles minimum
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L46070-46072
- **Verbatim**: "It obviously didn't eat completely the last two candles, so that should be your first red flag" (L46070-46071)
- **Formulation normalisee**: Si l'engulfing ne depasse pas completement les 2 candles precedents → red flag → pas d'entree.

---

## 6. Elements HEURISTIQUES (V068)

### HEURISTIQUE V068-1 — "Strong" level de S/R
- Meme probleme que V064 HEURISTIQUE 2. Combien de touches = "strong" ? V068 dit ">3 touches" (L45968) ce qui est exploitable, mais la tolerance de zone reste floue.

### HEURISTIQUE V068-2 — TP swing vs intraday
- L45990-45997 : L'auteur decide au cas par cas s'il hold en swing ou sort intraday. Pas de regle mecanique.

### HEURISTIQUE V068-3 — Engulfing de "10 candles"
- L46040-46044 : Un engulfing qui mange 10 candles est "very strong indication" mais reste invalide si contre la zone. Le nombre de candles manges n'est pas un filtre codable precis.

---

## 7. Contexte discretionnaire (V068)

- **Instrument montre**: AUD/CAD (forex) sur 30m (L45923-45924).
- **Resultat annonce**: $54,000 en 24h (L45849-45851). Non auditable.
- **Mode**: Day trading / intraday, convertible en swing (L45990-46000).
- **30m AOI non valide seul**: "on a 30-minute, a set-and-forget strategy, we don't use 30-minute areas of interest because they're nowhere near as effective" (L46077-46079). Confirme que l'AOI DOIT etre HTF (4H+).

---

## 8. Bruit / marketing (ignore)

- L45849-45867 : Intro gain + phone refresh
- L46085-46122 : CTA set-and-forget, mentorship plug

---

---

## PARTIE C — CONVERGENCES ET DIFFERENCES V064 vs V068

| Dimension | V064 | V068 |
|-----------|------|------|
| **TF Trend** | 4H + 1H (structure LH/LL ou HH/HL) | Pas mentionne explicitement |
| **TF Zone (AOI)** | 4H + 1H (min 3 touches chaque) | 4H (min 3 touches) + daily pour TP |
| **TF Rejection** | 4H (doji/engulfing) + 1H (engulfing) | Non separe — la rejection EST l'entry |
| **TF Entree** | 1H ou 30m (engulfing/doji) | 30m ou 15m (engulfing strict) |
| **Definition engulfing** | Engulfing OU doji (plus souple) | Engulfing strict : 1 candle mange 2 candles (plus precis) |
| **SL** | 10-15 pips au-dela du high/low recent | Sous low des 2 candles precedents + breathing room |
| **TP** | 1.5R min, 2R max (fixe, session-bound) | Structure level sur daily/HTF (discretionnaire) |
| **Session** | Pre-London/NY, cutoff 9am | Pas de filtre session explicite (9:30 mentionne pour l'exemple) |
| **Gate AOI** | Binaire : doit etre A l'AOI | Binaire : doit etre a un S/R fort |
| **Gate direction** | Engulfing dans le sens du trend 4H+1H | Engulfing dans le bon sens vs zone (above support = buy, below resistance = sell) |
| **Instruments** | Forex (multi, 10-15 marches) | Forex (AUD/CAD montre) |

### Convergences cles
1. **AOI 4H avec min 3 touches** est le fondement des deux videos.
2. **Engulfing comme signal d'entree** est central dans les deux.
3. **Gate binaire** : pas d'entree sans etre a la zone.
4. **Breathing room SL** : les deux insistent sur un padding au-dela du swing extreme.
5. **Pas de trade en milieu de chart** : l'engulfing seul sans zone = invalide.

### Differences cles
1. **V064 ajoute un filtre trend 4H+1H** que V068 ne mentionne pas (V068 se fie uniquement a la zone).
2. **V064 separe rejection (4H/1H) et entry signal (1H/30m)** en etapes distinctes ; V068 fusionne rejection et entry en un seul engulfing.
3. **V068 definit l'engulfing plus strictement** : 1 candle mange 2 candles (3-candle pattern). V064 accepte aussi les doji.
4. **TP** : V064 est mecanique (1.5R-2R fixe) ; V068 est discretionnaire (structure levels).

---

## 9. ECARTS (Gaps V064/V068 vs playbooks existants)

### ECART E1 — Aucun playbook existant n'utilise 4H/1H AOI + engulfing
- **Playbooks actuels** : Tous operent sur 5m setup / 1m entry. Aucun ne definit une zone AOI sur 4H avec comptage de touches.
- **Criticite**: HAUTE — c'est une strategie fondamentalement differente de tout ce qui existe dans le repo.

### ECART E2 — Timeframes trop eleves pour le moteur actuel
- **V064/V068** : 4H zone, 1H trend, 30m/15m entry.
- **Moteur actuel** : Opere sur 5m max pour setup, 1m pour entry. Pas de support 4H/1H natif.
- **Criticite**: HAUTE — necessite un pipeline HTF complet.

### ECART E3 — Comptage de touches AOI : absent du moteur
- **V064/V068** : "minimum 3 touches" comme gate binaire.
- **Moteur actuel** : Pas de logique de comptage de touches sur un niveau de S/R.
- **Criticite**: HAUTE — engine gap fondamental.

### ECART E4 — RR cible : 1.5R-2R vs 3R+ des playbooks actuels
- **V064** : 1.5R min, 2R max.
- **Playbooks actuels** : Minimum 2.5R-3R pour tous les playbooks DAYTRADE.
- **Criticite**: MOYENNE — le playbook S10 aurait un profil RR tres different, necessitant un win rate >60% pour etre profitable.

### ECART E5 — Engulfing "mange 2 candles" : pas dans le moteur
- **V068** : Definition stricte = 1 candle qui engloble les 2 precedents (body complet).
- **Moteur actuel** : `candlestick_patterns` detecte des engulfing standards (1 vs 1) sans la condition "mange 2".
- **Criticite**: MOYENNE — necessite une extension de la detection candlestick.

### ECART E6 — Session filter pre-session
- **V064** : "pre-London or pre-New York" — analyse AVANT la session, entree au debut.
- **Playbooks actuels** : Time ranges fixes (ex : 09:30-11:00) sans concept de "pre-session analysis".
- **Criticite**: FAIBLE — conceptuellement different mais operationnellement similaire a un filtre time_range.

---

## 10. ENGINE GAPS (ce que le moteur actuel ne peut pas faire)

### ENGINE GAP G1 — Pas de pipeline 4H/1H
- Le moteur ne charge pas de donnees 4H ou 1H. Les TF disponibles sont typiquement 5m et 1m.
- **Fichiers concernes**: `backend/engines/setup_engine.py`, data pipeline

### ENGINE GAP G2 — Pas de detection de zones S/R avec comptage de touches
- Le moteur ne detecte pas de niveaux horizontaux de support/resistance et ne compte pas le nombre de touches.
- **Fichiers concernes**: `backend/engines/signal_detector.py`, `backend/engines/setup_engine.py`
- **Complexite**: HAUTE — necessite un algorithme de detection de niveaux (clustering de highs/lows) + compteur de touches avec tolerance.

### ENGINE GAP G3 — Pas de detection engulfing "2-candle" (3-candle pattern)
- Le moteur detecte des patterns 1-vs-1 (engulfing standard). La definition V068 exige 1 candle qui mange 2 candles precedents.
- **Fichiers concernes**: `backend/engines/signal_detector.py`

### ENGINE GAP G4 — Pas de confirmation de rejection sur meme TF que zone
- Le moteur ne verifie pas que la rejection (candlestick pattern) se produit sur le meme TF que la zone qui l'a generee.
- **Fichiers concernes**: `backend/engines/setup_engine.py`

### ENGINE GAP G5 — Pas de SL "padding pips au-dela du swing"
- Le SL actuel est base sur `fvg_extreme`, `recent_swing`, etc. Le concept "10-15 pips AU-DELA du high" n'est pas parametrable comme padding fixe en pips.
- **Fichiers concernes**: `backend/engines/risk_engine.py`

### ENGINE GAP G6 — Pas de TP structure-level (V068)
- Le TP actuel est base sur un ratio RR fixe. V068 utilise des niveaux de structure sur le daily comme TP.
- **Fichiers concernes**: `backend/engines/risk_engine.py`

---

## 11. Execution Flow (pseudo-code combine V064+V068)

```
# ============================================================
# S10 — HTF AOI Engulfing Strategy
# ============================================================

# --- PHASE 1 : HTF CONTEXT (weekly/daily scan — V064 only) ---
# Optionnel : ajoute du grade mais pas obligatoire pour le setup
FOR each market IN watchlist:
    weekly_bias  = classify_trend(weekly)    # bonus grade
    daily_bias   = classify_trend(daily)     # bonus grade

# --- PHASE 2 : TREND CHECK 4H + 1H (V064) ---
    trend_4h = classify_structure(4H, lookback=20)  # HH/HL or LH/LL
    trend_1h = classify_structure(1H, lookback=20)

    IF trend_4h != trend_1h:
        grade -= 10%    # non-aligned, reduce confidence
        # V064 allows trade but with lower grade
    ELSE:
        grade += 10%    # aligned = 5% + 5%

# --- PHASE 3 : AOI DETECTION (V064 + V068 convergent) ---
    aoi_4h = find_sr_level(4H, min_touches=3)
    aoi_1h = find_sr_level(1H, min_touches=3)    # V064 only

    IF aoi_4h IS NULL:
        SKIP — no trade possible                   # GATE BINAIRE

    IF NOT price_at_zone(current_price, aoi_4h):
        SKIP — "price must BE at the AOI"          # GATE BINAIRE

    grade += 5%  (4H AOI present)
    IF aoi_1h IS NOT NULL AND price_at_zone(current_price, aoi_1h):
        grade += 5%  (1H AOI confirmed)

# --- PHASE 4 : REJECTION CHECK same TF as AOI (V064) ---
    rejection_4h = detect_rejection(4H, at=aoi_4h)
        # Valid patterns: double_doji, engulfing, wick_rejection
    rejection_1h = detect_rejection(1H, at=aoi_1h)

    IF rejection_4h:
        grade += 10%
    IF rejection_1h:
        grade += 10%

    IF NOT rejection_4h AND NOT rejection_1h:
        SKIP — "no rejection = no trade"           # GATE BINAIRE

# --- PHASE 5 : ENTRY SIGNAL on 1H/30m/15m ---
    # V064: 1H or 30m engulfing/doji
    # V068: 30m or 15m engulfing strict (1 candle eats 2)
    entry_tf = select_entry_tf([30m, 15m])         # prefer 30m

    signal = detect_engulfing_2candle(entry_tf, at=aoi_4h)
        # V068 strict: body of candle N > body of candle N-1 AND N-2
        # V064 relaxed: also accepts doji rejection

    IF signal IS NULL:
        WAIT — check next candle

    IF session NOT IN [pre_london, london, pre_ny, ny]:
        SKIP — wrong session (V064 L44487-44492)

# --- PHASE 6 : ENTRY ---
    entry_price = signal.close                     # market order at close

# --- PHASE 7 : SL ---
    # V064: 10-15 pips beyond the high/low of the zone
    # V068: below low of the 2 eaten candles + breathing room
    IF direction == SHORT:
        sl_base = max(signal.candle_n_minus_1.high, signal.candle_n_minus_2.high)
        sl_price = sl_base + padding_pips(10, 15)
    ELIF direction == LONG:
        sl_base = min(signal.candle_n_minus_1.low, signal.candle_n_minus_2.low)
        sl_price = sl_base - padding_pips(10, 15)

# --- PHASE 8 : TP ---
    risk = abs(entry_price - sl_price)
    # V064 mode (intraday):
    tp1 = entry_price + direction * risk * 1.5
    tp2 = entry_price + direction * risk * 2.0     # max
    # V068 mode (structure-based, optional swing):
    # tp_structure = next_structure_level(daily, direction)

# --- PHASE 9 : TRADE MANAGEMENT ---
    # V064: close at end of session if not at TP
    # V064: if in decent profit at session end → move to breakeven
    # V064: if in small loss or small profit → close manually
    IF session_ending AND NOT tp_hit:
        IF unrealized_pnl > 0.5R:
            move_sl_to_breakeven()
        ELSE:
            close_trade()

# --- GRADE THRESHOLDS (from V064 checklist) ---
    # < 50% → D setup → skip (or reduce size)
    # 50-70% → C/B → acceptable
    # 80%+ → A/A+ → ideal
    IF grade < 50%:
        SKIP or reduce_size()
```

---

## 12. Verifications requises avant implementation

| # | Point | Source | Bloquant? |
|---|-------|--------|-----------|
| 1 | "9 AM latest" = 9:00 ET ou 9:00 local du marche? | V064 L44491 | Oui — forex = GMT sessions, pas ET |
| 2 | "10-15 pips" = applicable a SPY/QQQ ou seulement forex? | V064 L44595 | Oui — pips forex ≠ ticks equity. Necessite conversion |
| 3 | Min touches AOI : strictement > 3 ou >= 3? | V064 L44511, V068 L45968 | Non — "minimum of three" = >= 3 |
| 4 | Definition "touch" : wick ou close dans la zone? | Non explicite | Oui — impacte fortement le comptage |
| 5 | Engulfing strict (V068) vs relaxe (V064) : lequel coder? | Convergence | Non — coder V068 strict, accepter doji en option |
| 6 | TP structure (V068) : comment identifier les niveaux? | V068 L46001-46006 | Oui — engine gap, pas de detecteur structure levels |
| 7 | Applicabilite aux equities (SPY/QQQ) : la strategie est presentee sur forex | Contexte | Oui — les TF et le comportement des niveaux different |

---

## 13. Verdict

**V064 + V068 decrivent une strategie HTF "set-and-forget" fondamentalement differente de tous les playbooks actuels.** Les TF (4H/1H/30m) sont 10-100x plus lents que le pipeline actuel (5m/1m). Le concept central (AOI avec 3+ touches + engulfing rejection) est partiellement codable mais necessite 6 engine gaps majeurs.

**Codabilite** : ~65%. Les regles de trend, AOI gate, engulfing pattern et SL/TP sont mecaniques. Les elements discretionnaires (grade seuil, TP structure, session exit management) necessitent des proxies.

**Priorite** : BASSE dans le contexte actuel. Tous les playbooks existants sont negatifs sur 6 mois de WF. Ajouter un playbook HTF ne resout pas le probleme fondamental. Cependant, cette strategie opere sur des TF completement differents et pourrait avoir un profil d'edge distinct — a evaluer uniquement si les donnees Polygon 18+ mois (P2) deviennent disponibles.
