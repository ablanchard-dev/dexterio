# Source Truth Pack — VIDEO 055 "The 3 Step A+ Supply & Demand Strategy (That Actually Works)"

**Video file**: `videos/The 3 Step A+ Supply & Demand Strategy (That Actually Works)-nkMzaQqpFbw.mp4`
**Transcript**: `MASTER_FINAL.txt` L32769-32978
**Quality**: MOYENNE (65% codable) — Beaucoup de narration live, peu de seuils quantitatifs
**Role in roadmap**: Strategy S7 — Supply & Demand Zone. HTF swing trading / day trade hybrid.

---

## 1. Regles mecaniques extraites

### REGLE 1 — Identifier une zone de demande institutionnelle (Step 1)
- **Classification**: HEURISTIQUE
- **Source TXT**: L32788-32807
- **Verbatim**: "We get 1, 2, 3, 4 big green candles in a row. [...] This would take about a billion dollars, which means we have institutional demand. [...] what we do is draw a demand zone and we draw that on the candle body before the big push up."
- **Formulation normalisee**:
  1. Sur le chart **H1**, reperer un mouvement impulsif (3+ candles consecutives de meme couleur).
  2. Dessiner la zone de demande sur le **corps (body)** de la derniere bougie AVANT le mouvement impulsif.
  3. Si la bougie est grosse : utiliser body-to-body (corps seulement).
  4. Si la bougie est petite : utiliser wick-to-wick (meche a meche).
  5. Si plusieurs petites bougies : les regrouper en une seule zone.
- **Verbatim body vs wick**: "the reason I draw the demand zone just on the body right here is because this is where the majority of the trading volume occurred [...] if I had a smaller candle [...] I will use wick to wick."
- **Probleme**: "Big candle" et "3+ candles" ne sont pas quantifies. Combien de pips/ATR = "impulsif" ? Non defini.

---

### REGLE 2 — Fair Value Gap comme confirmation de momentum (Step 1 complement)
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L32808-32815
- **Verbatim**: "The next thing we're looking for is a fair value gap [...] We're using this for trend confirmation and momentum. You can see this candle right here and this candle right here do not cover this candle, creating a level of imbalance."
- **Formulation normalisee**: Apres identification de la zone de demande, verifier qu'un **FVG** (gap entre candle 1 et candle 3 du triplet, non couvert par le candle 2) existe dans le mouvement impulsif. Le FVG confirme le momentum et l'interet institutionnel.
- **Gate**: Le FVG est mentionne comme complementaire, pas comme gate binaire obligatoire.

---

### REGLE 3 — Confluence stack : zone testee historiquement (Step 1 complement)
- **Classification**: HEURISTIQUE
- **Source TXT**: L32816-32821
- **Verbatim**: "if we scroll out a little bit [...] we can look to see if this was a level used in the past. You can see right here and right here. our level was recently used as a resistance. So we can expect this level may be used as a support"
- **Formulation normalisee**: Verifier que la zone de demande correspond a un ancien niveau de resistance (S/R flip). Ce chevauchement ("stack") renforce la zone.
- **Probleme**: "Scroll out" = combien de barres ? Aucun seuil de lookback defini.

---

### REGLE 4 — Confirmation de tendance via BOS sur meme TF et HTF (Step 2)
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L32823-32839
- **Verbatim**: "we're just going to scroll out a little bit on the time frame we're actually on. And let's just mark out our swing low, our swing high [...] We have a break of structure here, and we have a break of structure here."
- **Formulation normalisee**:
  1. Sur le **meme TF** (H1) : identifier les swing highs/lows. Verifier que les swing highs sont croissants (uptrend) ou swing lows decroissants (downtrend). Au moins 2 BOS dans la meme direction.
  2. Sur le **H4** : meme verification (swing highs/lows alignes avec la direction).
  3. Alternative debutant : prix au-dessus d'une **EMA** avec separation visible.
- **Verbatim HTF**: "come to a higher time frame. Like let's go to the four hour time frame [...] again, we are in that upward trajectory."
- **Verbatim EMA**: "if the price is above that EMA and creating a big gap off of that EMA, then we have that trend confirmation."

---

### REGLE 5 — Slow momentum a l'approche de la zone (Step 3 filtre)
- **Classification**: HEURISTIQUE
- **Source TXT**: L32846-32850
- **Verbatim**: "one of the first things we're looking for is slow momentum [...] we don't want to see [...] that big red candle coming down to your zone. No, no, no. [...] You want to see a slow in momentum. That means, look, there's some green candles in here as well as we're slowly coming down."
- **Formulation normalisee**: Le prix doit arriver dans la zone de demande avec un **ralentissement visible du momentum** : des bougies mixtes (vertes dans le mouvement baissier), pas un seul gros candle baissier. Un mouvement violent vers la zone = invalide.
- **Probleme**: "Slow momentum" est purement visuel. Pas de metrique (taille relative des candles, ratio vert/rouge, vitesse).

---

### REGLE 6 — Entree : candle close dans la zone + reaction positive (Step 3)
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L32851-32854
- **Verbatim**: "the candle to close in the zone or wick into the zone we do not want the candle to close beneath the zone if it does the trade is invalidated [...] once we're closed into the zone on this candle and then we get the positive green candle right here we can enter our trade right here on that candle"
- **Formulation normalisee**:
  1. Attendre qu'un candle **ferme dans la zone** ou **meche dans la zone** (mais NE ferme PAS en-dessous).
  2. Si le candle ferme en-dessous de la zone → **TRADE INVALIDE**.
  3. Attendre un **candle positif** (vert = dans le sens du trade) comme confirmation.
  4. Entrer sur ce candle positif.

---

### REGLE 7 — Stop Loss (Step 3)
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L32854-32856
- **Verbatim**: "your stop loss you can put it tight to the zone or in this case look there's a wick over here you can put it beneath that wick and that's also beneath the ema right here"
- **Formulation normalisee**:
  - Option A : SL juste sous la zone de demande.
  - Option B : SL sous la meche la plus basse dans/autour de la zone.
  - Idealement sous l'EMA aussi.
- **Probleme**: Deux options, aucune priorite explicite. Pas de padding defini.

---

### REGLE 8 — Take Profit : 1:1 a 1.5:1, cibler prix recent (Step 3)
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L32857-32859
- **Verbatim**: "a lot of people just go one to one nothing wrong with that on this one i'm going to target some recent price so let's go something like 1.5 because the price was just at this level right here"
- **Formulation normalisee**:
  - TP = **prix recent** (dernier swing high pour LONG, dernier swing low pour SHORT).
  - RR typique : **1:1 a 1.5:1** (faible par rapport aux autres strategies MASTER).
- **Note**: Les exemples suivants montrent aussi 1.4:1 (L32868) et 1.83:1 (L32922).

---

### REGLE 9 — Zone fraiche uniquement (Key 1 : Untested Zone)
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L32882-32886
- **Verbatim**: "you only use that demand zone when it's fresh [...] when price comes back to that level right there look it doesn't hold [...] it breaks through why because it was already used"
- **Formulation normalisee**: Une zone de demande n'est valide que si elle est **fraiche** (jamais testee). Des que le prix a touche la zone une fois, elle est "usee" et ne doit plus etre utilisee.

---

### REGLE 10 — Close ou wick, pas close beneath (Key 2)
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L32887-32889
- **Verbatim**: "Price wicking like this is good [...] price wicking below closing inside the zone no problem but if the price closes below like this it is invalid we're not using it"
- **Formulation normalisee**: Identique a REGLE 6. Confirmation via repetition : wick sous la zone = OK si le close reste dans la zone. Close sous la zone = invalide.

---

### REGLE 11 — Lowest demand = strongest demand (Key 4)
- **Classification**: HEURISTIQUE
- **Source TXT**: L32896-32898
- **Verbatim**: "the lowest demand is always the strongest demand"
- **Formulation normalisee**: Quand plusieurs zones de demande existent, privilegier la zone la plus basse (la plus profonde dans le retracement). Les zones superieures sont plus faibles.

---

### REGLE 12 — Discounted price : entree sous 50% du Fibonacci (Key 5)
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L32899-32903
- **Verbatim**: "click over here on the left hand side to your fib retracement measure from the bottom of the swing low to the top [...] just make sure that your entry comes below 50"
- **Formulation normalisee**: Tracer le Fibonacci du swing low au swing high. L'entree doit etre **en-dessous du niveau 50%** (zone discount). Zone au-dessus de 50% = premium = eviter pour les longs.

---

### REGLE 13 — Break of Structure requis dans la tendance (Key 6)
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L32904-32909
- **Verbatim**: "what do we want to see we want to see break of structure every single time that just means this high is being taken out by the next high [...] we do not get a break of structure of this high so what do you think is going to happen price is not going to hold it's a bad demand zone"
- **Formulation normalisee**: La zone de demande n'est valide que si la tendance montre des **BOS consecutifs** (chaque swing high depasse par le suivant). Si le dernier swing high n'est PAS casse par le mouvement suivant, la zone est invalide.

---

### REGLE 14 — Opening Range Break (live trade complement)
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L32957-32962
- **Verbatim**: "at 9.30 a.m. Eastern, I was setting up my range high and my range low [...] I look at the first three five-minute candles of the day. They set the range. [...] I just want to see the price break and close out the top or the bottom."
- **Formulation normalisee**:
  1. Range = high/low des **3 premiers candles 5m** (9:30-9:45 ET).
  2. Attendre que le prix **break et close** au-dessus (LONG) ou en-dessous (SHORT) du range.
  3. Ce break confirme la direction du trade S&D.
- **Note**: Ce range 15m (3x5m) est identique au range V065. C'est un filtre supplementaire a la strategie S&D, pas le coeur du systeme.

---

### REGLE 15 — Trailing stop apres entree (complement)
- **Classification**: REGLE EXPLOITABLE
- **Source TXT**: L32934-32944
- **Verbatim**: "we're going to use a trailing stop indicator [...] for time frame i'm setting it to five minutes because i'm trading on the five minute time frame [...] we're not gonna close until price closes beneath the pink line"
- **Formulation normalisee**: Apres entree, le trader utilise un **trailing stop sur le TF 5m**. Le trade est ferme lorsque le prix **close en-dessous** du trailing stop (pas juste une meche).
- **Probleme**: L'indicateur exact ("trailing stop indicator" sur TradingView) n'est pas specifie. Parametre = TF 5m mais pas de type (ATR trailing, chandelier, etc.).

---

## 2. Elements HEURISTIQUES (a valider)

### HEURISTIQUE 1 — Definition de "mouvement impulsif"
- **Classification**: HEURISTIQUE A VALIDER
- **Source TXT**: L32795-32797
- **Verbatim**: "We get 1, 2, 3, 4 big green candles in a row. [...] This would take about a billion dollars"
- **Probleme**: Combien de candles minimum ? Quelle taille = "big" ? Le transcript montre 3-5 candles comme exemples mais ne definit pas de seuil. "60 pips" est mentionne pour un exemple Forex H1, pas applicable aux indices.
- **A calibrer**: Definir N candles consecutives de meme couleur (N >= 3) et/ou mouvement >= X * ATR(H1).

### HEURISTIQUE 2 — "Slow momentum" a l'approche
- **Classification**: HEURISTIQUE A VALIDER
- **Source TXT**: L32846-32850
- **Probleme**: Visuellement clair mais non quantifiable. Un ratio vert/rouge dans les N dernieres bougies ? Une diminution de la taille moyenne des bougies ? Non defini.
- **A calibrer**: Ex. : au moins 1 bougie contraire dans les 5 dernieres bougies avant entree en zone.

### HEURISTIQUE 3 — Taille de zone : body vs wick-to-wick
- **Classification**: HEURISTIQUE A VALIDER
- **Source TXT**: L32802-32807
- **Probleme**: Le choix body-only vs wick-to-wick depend de la taille de la bougie ("big candle" vs "smaller candle"). Pas de seuil quantitatif.
- **A calibrer**: Ex. : si candle range > 2 * ATR(TF) → body-only ; sinon → wick-to-wick.

---

## 3. Contexte discretionnaire (non codable mais informatif)

- **Backtest annonce**: L32779-32780 — "121 trade backtest. It has a 79% win rate at P&L of over 2,100%." Backtest manuel, non auditable.
- **Instruments mentionnes**: L32784 — "Forex, any crypto, futures, gold."
- **Sessions preferees**: L32786 — "I prefer the London and New York."
- **Live trade mentionne**: L32783 — "I had this real live trade using the concepts just this morning."
- **Timeframes**: L32789-32790 — "This can be on any time frame. For this example, I'm on the H1 chart." H1 pour setup, H4 pour confirmation tendance.
- **Broker plug**: L32947-32949 — Triple AFX brokerage.

---

## 4. Bruit / marketing (ignore)

- L32772-32778 : Intro storytelling ("I've been using these concepts for 16 years")
- L32821-32822 : CTA commentaires pour VIP room
- L32840-32841 : CTA like/rewind
- L32863 : "pat you're just cherry picking" defense
- L32946-32949 : Broker plug Triple AFX
- L32975-32978 : Outro/subscribe CTA

---

## 5. Comparaison V055 vs playbooks existants

| Dimension | V055 (cette video) | FVG_Fill_Scalp (plus proche) | NY_Open_Reversal |
|-----------|---------------------|-------------------------------|-------------------|
| TF Setup | **H1** (demand zone) | 5m | 5m |
| TF Confirmation | **H4** (tendance) | 1m | 1m |
| TF Execution | H1 (implicite) | 1m (limit FVG 50%) | 1m |
| Concept central | **Demand zone** (body avant impulsion) | FVG fill (retest milieu FVG) | Sweep London + reversal |
| Direction | BOS H1/H4 + EMA | HTF bias | HTF bias + London sweep |
| Entree | **Reaction positive** dans zone fraiche | Limit a 50% FVG | Limit pattern close |
| SL | Sous zone / sous wick | Sous FVG extreme | Sous recent swing |
| TP | **1:1 a 1.5:1** vers prix recent | 1.5 + 2.0 dual | 3.0 + 5.0 dual |
| Filtre cle | Zone fraiche + FVG + confluence S/R + Fib < 50% | fvg_quality scoring | london_sweep_required |
| Trailing | **Oui** (5m trailing stop) | Non | Non |

### Constat principal
V055 est une strategie **fondamentalement differente** de tout playbook existant. C'est une approche HTF (H1/H4) de type swing/day trade basee sur des zones de demande institutionnelles, pas un scalp 1m/5m. Le RR cible est faible (1:1 a 1.5:1) compense par un taux de gain eleve annonce (79%). Aucun playbook existant n'implemente le concept de "demand zone" (body de la bougie avant impulsion).

---

## 6. ECARTS (Gaps video -> code actuel)

### ECART E1 — Aucun playbook "Supply & Demand Zone" n'existe
- **V055**: Strategie complete basee sur la detection de zones de demande/offre institutionnelles.
- **Code actuel**: Aucun playbook ne detecte des "demand zones" (corps de la bougie avant un mouvement impulsif de N candles).
- **Criticite**: N/A — pas un ecart dans un playbook existant, mais un playbook entierement manquant.

### ECART E2 — Timeframe H1/H4 non supporte
- **V055**: Setup sur H1, confirmation tendance sur H4.
- **Code actuel**: Tous les playbooks operent sur 5m (setup) / 1m (confirmation). L'infrastructure ne gere pas les TF H1/H4 pour les setups.
- **Criticite**: HAUTE si on voulait implementer V055 fidelement.

### ECART E3 — Concept de "zone fraiche" absent
- **V055**: Une zone n'est valide que si elle est "untested" (jamais touchee par le prix).
- **Code actuel**: Pas de tracking d'etat "tested/untested" pour les zones. Les FVG sont detectes mais leur statut "deja touche" n'est pas gere.
- **Criticite**: HAUTE — c'est un filtre central de V055.

### ECART E4 — Fibonacci discount filter absent
- **V055**: Entree doit etre sous le niveau 50% Fibonacci (swing low -> swing high).
- **Code actuel**: Aucun filtre Fibonacci dans les playbooks. Pas de concept "premium/discount" code.
- **Criticite**: MOYENNE — codable mais non implemente.

### ECART E5 — RR 1:1.5 avec trailing stop
- **V055**: TP = 1:1 a 1.5:1 vers prix recent + trailing stop optionnel sur 5m.
- **Code actuel**: TP minimum 1.5:1 avec dual TP et breakeven a 1R. Pas de trailing stop.
- **Criticite**: FAIBLE — si on n'implemente pas V055.

### ECART E6 — "Slow momentum" filter absent
- **V055**: Le prix doit arriver dans la zone avec un ralentissement du momentum (pas un crash violent).
- **Code actuel**: Aucun filtre de "qualite d'approche" dans les playbooks existants.
- **Criticite**: MOYENNE — concept interessant mais non quantifie dans la video.

---

## 7. ENGINE GAPS (ce que le moteur actuel ne peut pas faire)

### ENGINE GAP G1 — Pas de detection de "demand zone" (mouvement impulsif + body avant)
- Le moteur ne detecte pas les sequences de N candles impulsives et n'identifie pas la bougie precedant le mouvement comme zone.
- **Fichiers concernes**: `backend/engines/signal_detector.py`, `backend/engines/setup_engine.py`

### ENGINE GAP G2 — Pas de support H1/H4 comme TF de setup
- Le moteur est concu pour operer sur 5m/1m. Le pipeline de donnees, le backtester, et les engines ne supportent pas les candles H1/H4 comme timeframe primaire de setup.
- **Fichiers concernes**: `backend/engines/context_engine.py`, `backend/data/` (data pipeline)

### ENGINE GAP G3 — Pas de tracking "zone fraiche / zone usee"
- Aucun mecanisme ne suit si une zone (demand, supply, FVG) a deja ete touchee par le prix. Il faudrait un registre persistant de zones avec un statut (fresh / tested / invalidated).
- **Fichiers concernes**: `backend/engines/signal_detector.py`, nouveau composant `zone_tracker`

### ENGINE GAP G4 — Pas de filtre Fibonacci premium/discount
- Aucun calcul de retracement Fibonacci (swing-to-swing) pour determiner si l'entree est en zone discount (< 50%) ou premium (> 50%).
- **Fichiers concernes**: `backend/engines/setup_engine.py`

### ENGINE GAP G5 — Pas de trailing stop candle-by-candle
- Meme gap que V054 G5. Aucun mecanisme de trailing stop ou le SL suit le low/high de chaque nouveau candle.
- **Fichiers concernes**: `backend/engines/risk_engine.py`

### ENGINE GAP G6 — Pas de detection "slow momentum" a l'approche d'une zone
- Aucun filtre mesurant la qualite/vitesse de l'approche du prix vers une zone (ratio de bougies mixtes, diminution de taille, etc.).
- **Fichiers concernes**: `backend/engines/setup_engine.py`

### ENGINE GAP G7 — Pas de S/R flip detection (confluence stack)
- Le moteur ne detecte pas les niveaux ayant servi de resistance et devenant support (ou inversement). Le concept "confluence stack" (overlap demand + ancien S/R) n'est pas implemente.
- **Fichiers concernes**: `backend/engines/context_engine.py`

---

## 8. Resume implementable (V055 fidele)

```
STRATEGIE: Supply & Demand Zone (S7)
TIMEFRAMES: H1 (setup demand zone) + H4 (confirmation tendance) + H1/5m (execution)
SESSION: London et/ou New York preferees
INSTRUMENTS: Forex, Crypto, Futures, Gold (video), SPY/QQQ (notre univers)

STEP 1 — IDENTIFIER LA ZONE DE DEMANDE (H1):
  candles_impulsives = N candles consecutives meme couleur (N >= 3)
  mouvement >= seuil_impulsion (a calibrer, ex: 2 * ATR_H1)
  demand_zone = body de la derniere bougie AVANT le mouvement impulsif
    SI bougie grosse (range > 2*ATR) → zone = body seulement
    SI bougie petite → zone = wick-to-wick
    SI plusieurs petites bougies → zone = regroupement
  FVG_present = verifier qu'un FVG existe dans le mouvement impulsif
  confluence = verifier si la zone correspond a un ancien S/R (flip)

STEP 2 — CONFIRMER LA TENDANCE (H1 + H4):
  SUR H1:
    compter BOS (swing highs croissants ou swing lows decroissants)
    REQUIS: au moins 2 BOS dans la meme direction
  SUR H4:
    meme verification (BOS alignes)
  ALTERNATIVE: prix au-dessus EMA avec separation visible
  SI pas de tendance confirmee → NO TRADE

STEP 3 — ENTREE:
  FILTRES PRE-ENTREE:
    - Zone doit etre FRAICHE (jamais testee)
    - Zone doit etre en DISCOUNT (sous Fibonacci 50% du dernier swing)
    - Zone doit etre la plus BASSE parmi les zones disponibles (preferred)
    - Momentum d'approche doit etre LENT (bougies mixtes, pas de crash)

  CONDITION D'ENTREE:
    ATTENDRE candle qui close dans la zone OU wick dans la zone
    SI candle close SOUS la zone → TRADE INVALIDE
    ATTENDRE candle positif (vert pour LONG) comme confirmation
    ENTRER sur le candle positif (market order implicite)

  STOP LOSS:
    SL = sous la zone de demande (ou sous la meche la plus basse)
    Idealement sous l'EMA aussi

  TAKE PROFIT:
    TP = prix recent (dernier swing high pour LONG)
    RR typique = 1:1 a 1.5:1
    OPTION: trailing stop sur TF 5m apres entree (close beneath trailing = exit)

  INVALIDATION:
    - Candle close sous la zone → annuler
    - Pas de BOS dans la tendance → annuler
    - Zone deja testee → annuler
```

---

## 9. Verifications requises avant implementation

| # | Point | Ligne TXT | Bloquant? |
|---|-------|-----------|-----------|
| 1 | Definir "mouvement impulsif" quantitativement (N candles, taille) | L32795-32797 | Oui — coeur de la detection |
| 2 | Definir "slow momentum" quantitativement | L32846-32850 | Oui — filtre d'entree |
| 3 | Body vs wick-to-wick : seuil de taille du candle | L32802-32807 | Non — proxy ATR possible |
| 4 | EMA period pour confirmation tendance alternative | L32831-32835 | Non — standard 20/50 |
| 5 | Trailing stop : quel indicateur exactement ? | L32934-32936 | Non — si on utilise TP fixe |
| 6 | Supply zones (vente) : memes regles inversees ? | Non explicit | Non — symetrique par inference |
| 7 | Support donnees H1/H4 dans le pipeline | Infra | Oui — pas de donnees H1/H4 actuellement |

---

## 10. Verdict implementabilite

**Score codabilite**: 50% (MOYEN)

**Forces**:
- Le concept "demand zone" est clair conceptuellement (body avant impulsion + zone fraiche).
- Les regles d'invalidation sont nettes (close sous zone = invalide, zone deja testee = invalide).
- BOS + Fibonacci discount sont codables.

**Faiblesses**:
- **TF H1/H4** : le moteur actuel ne supporte pas ces timeframes. Implementation = refonte pipeline.
- **Seuils absents** : "mouvement impulsif", "slow momentum", "big candle" ne sont pas quantifies.
- **RR faible** : 1:1 a 1.5:1 est en-dessous du seuil min_rr de la plupart des playbooks (2.5-3.0). Le modele repose sur un win rate eleve (79% annonce) qui est non verifie.
- **Pas de gate binaire fort** : contrairement a V054 (FVG hors range = gate), V055 empile des confluences sans gate unique clair.

**Recommandation**: V055 est une strategie HTF qui ne s'integre pas facilement dans l'architecture actuelle (1m/5m). Les concepts individuels (zone fraiche, Fibonacci discount, BOS confirmation) sont reutilisables comme filtres dans d'autres playbooks. En tant que playbook standalone, l'implementation fidele necessite un support H1/H4 et la calibration de 3+ seuils heuristiques. Priorite basse vs strategies deja en pipeline.
