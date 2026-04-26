# TEp3a-7GUds — Path to Profitability: TJR's Strategy Explained

**Source** : https://youtu.be/TEp3a-7GUds · TJR · ~44min · auto-generated EN captions
**Date extraction** : 2026-04-24
**CRITICITÉ** : vidéo "final strategy" de la série Path to Profitability — TJR décrit SA stratégie complète en 4 étapes. À comparer avec Aplus_03/04/01 déjà testés.

## 1. Thèse centrale
Strategy TJR = pipeline en 4 étapes : (1) potential to fill orders (liquidity sweep above/below significant H/L), (2) confirmation orders were filled (change in order flow via BOS ou IFVG sur LTF), (3) continuation of new trend (price retraces vers FVG 5m ou equilibrium 5m), (4) exit at draws on liquidity opposées pour liquidate orders filled. Le tout cascade 4H→1H→5m→1m avec SMT cross-index. TJR refuse d'appeler ça "step 1, step 2" parce qu'il veut laisser la discrétion (gros red flag).

## 2. Mécanisme complet

### HTF bias
- 4H bullish/bearish order flow via HH-HL / LH-LL
- 1H confirmation sur même direction
- Identification des draws on liquidity prioritaires :
  - Previous day high / low
  - London session high / low
  - Asia session high / low (si pas déjà sweept)
  - Hourly highs/lows stacked

### Setup TF
- 5m pour identifier continuation confluence (FVG ou equilibrium) après BOS LTF
- 1m pour confirmation précise entry

### Entry trigger (mécanisme 4-stage, verbatim)

**Stage 1 — Potential to fill orders**
- Price sweeps above a significant high (pour short) ou below a significant low (pour long)
- "Significant" = session high/low, previous day H/L, hourly H/L marked
- SMT divergence cross-index = renforcement (ES sweeps H, NQ non → bearish SMT)

**Stage 2 — Confirmation orders filled**
- Change in order flow sur LTF (5m)
- Soit : break of structure (BOS) → candle close opposing direction
- Soit : inverse fair value gap (IFVG) 5m → candle close through a FVG de direction opposée
- Required : 5m BOS ou 5m IFVG dans la direction du nouveau trend

**Stage 3 — Continuation of new trend**
- Attendre retrace : price remonte (après short setup) ou redescend (après long setup) dans un continuation confluence
- 2 continuation confluences autorisées :
  - FVG 5m dans la direction nouveau trend
  - Equilibrium 5m calculé du swing high récent au swing low récent
- Scale down to 1m
- Sur 1m, attendre soit :
  - BOS 1m dans direction trend
  - IFVG 1m (bullish IFVG = 1m candle close bearish à travers un 1m bullish FVG qui était opposé au new trend)

**Stage 4 — Exit**
- Targets = draws on liquidity opposées (where orders filled can be liquidated)
- "Scale targets" : TP1, TP2, TP3 sur multiple levels (session highs, hourly highs, previous day highs)

### Stop loss
- "Above these highs" (sur short) ou "below these lows" (sur long)
- NON-CHIFFRÉ précisément (pas de ATR, pas de fixed tick distance)

### Take profit
- **Explicitement liquidity-targeting** — pas de fixed RR
- 3 TP échelonnés dans l'exemple du trade Friday
- Cible = "significant highs/lows in the market where orders that were filled can be liquidated"

### Exit logic
- NON-SPÉCIFIÉ BE ou trailing
- Implicite : session-end close (PM session 13:00 non-traded par TJR)

### Sizing
- NON-SPÉCIFIÉ (mais cross-ref funded accounts vidéo : 10 contracts max sur $100K Alpha Futures)

## 3. Règles fermées (codables telles quelles)

### Pipeline 4-stage codable
1. **Sweep detection** : price > significant high (bearish setup) ou < significant low (bullish setup). Significant = session H/L, previous day H/L, hourly H/L marked.
2. **LTF confirmation** : 5m BOS (close in opposite direction) OR 5m IFVG (close through opposing FVG). Les deux sont acceptés.
3. **Continuation confluence tap** : price retrace into 5m FVG (new trend direction) OR 5m equilibrium (calculated from recent swing H to recent swing L).
4. **Entry trigger LTF** : 1m BOS OR 1m IFVG dans new trend direction, AT confluence point.
5. **SL** : just above most recent swing H (short) ou below most recent swing L (long) — significant pool.
6. **TP** : liquidity targets multiples (TP1/TP2/TP3) = session H/L, previous day H/L.

### SMT cross-index gate
- Si ES sweep H + NQ non → bearish SMT confirmed → prefer short on ES (ES = leading index to downside dans l'exemple)
- Réciproque si inversé

### Règles d'ordering
- "Leading index" = celui qui **sweeps** le significant level = celui qui a comblé plus d'orders → short/long preferé sur l'index leading
- OR celui qui **ne fait pas** le move attendu = faible → short/long opposé logique (TJR ambigu sur ça)

## 4. Règles floues / discrétionnaires (ENORMES)

**TJR refuse explicitement de donner un step-by-step.** Citation verbatim §7 ci-dessous. Problèmes massifs pour codification :

- "Significant high" / "significant low" : non-défini opérationnellement. Pas de lookback window, pas de "at least N candles since", pas de ">= X ATR" critère.
- "Change in order flow" = BOS OR IFVG : lequel prendre si les deux se déclenchent différemment ? Ambigu.
- Continuation confluence "FVG OR equilibrium" : pareil ambigu si les deux existent.
- Timing : "scale down to 1m" quand exactement ? "for me I like to scale down..." = discrétion.
- "Sometimes instead of 5m I scale to 1m" — flip TF selon "feel".
- "Sometimes instead of waiting for this confirmation I wait for another confirmation" — entry trigger changeable.
- Choix entre TP1, TP2, TP3 pour exit = discrétion (partial exit ratios non-définis).
- SL sizing "above these highs" = ambigu quelle high exactement.

## 5. Conditions fertiles
- HTF structure claire (HH-HL ou LH-LL visible sur 4H)
- Multiple liquidity pools alignés dans la direction visée (TP targets)
- SMT divergence cross-index disponible (confirmation)
- NY open avec pre-market manipulation visible
- FVG 5m fraîchement formé dans retrace
- Draws on liquidity "pas encore swept" — liquidity frais

## 6. Conditions stériles
- News days (FOMC, CPI mentionnés)
- Range price action HTF (pas de HH-HL clair)
- Draws on liquidity déjà tous swept récemment (pas de targets "frais")
- Price action "ugly" / indécise
- Absence de FVG 5m ou equilibrium dans la zone retrace

## 7. Contradictions internes / red flags

### Red flag N°1 — Refus de step-by-step
Citation verbatim : "I'm not going to give you like a step-by-step, hey this, this, this, this, this. I'm just going to give you the overall ideations of how I'm going to be looking at trades... like the second that you don't do that exact step-by-step, the comment section is going berserk saying, you didn't follow your strategy. And it's like, shut up, bro."

Traduction : **TJR refuse de déclarer une stratégie falsifiable** parce que ça permet de changer les règles post-hoc. C'est **définitionnellement non-codable** dans sa forme pure. Pour coder ça il faut **figer une version** de la cascade et accepter qu'on ne reproduise pas "TJR personnel".

### Red flag N°2 — "Market proved me wrong"
Même citation que vidéo ironJFzNBic : "The market proved me wrong and instead did what it wanted to do... you're just wrong for the day." Reconnu wrong-bias fréquent mais sans chiffre.

### Red flag N°3 — Aucune métrique
- Zéro WR, E[R], Sharpe, max DD
- "Made me a profitable trader" + "seven figures last year" (dans vidéo Equilibrium) = claims non-vérifiables
- Pas de equity curve partagée
- Pas de backtest période

### Red flag N°4 — "LeBron James analogy"
15 minutes sur 44min de vidéo sont consacrées à expliquer qu'il faut 10,000 heures de chart time. = **auto-protection** contre "ta strat ne marche pas" → réponse "t'as pas mis tes 10k heures". Non-falsifiable.

### Red flag N°5 — Pipeline en 4 stages + discrétion
Chaque stage peut être filled de 2 façons différentes (BOS OR IFVG, FVG OR equilibrium, 5m OR 1m). Donc **2^4 = 16 variantes possibles** de "la même" stratégie. Survivorship garanti : la variante qui match le trade a postériori est validée.

### Red flag N°6 — Cherry-pick examples
Le trade Friday présenté est un winner qui hits TP1/TP2/TP3. Pas d'exemple de loser dans la démo. Sélection biaisée.

## 8. Croisement avec MASTER (contexte bot actuel)

- **Concepts MASTER confirmés** :
  - Pipeline sweep → BOS → retrace → FVG/EQ → entry
  - LTF cascade 5m → 1m
  - Liquidity-targeting TPs
  - Change of order flow concept
- **Concepts MASTER nuancés/précisés** :
  - MASTER parle de "sweep → BOS → FVG retrace" dans plusieurs playbooks (Aplus_01 Family A). Cette vidéo confirme **exactement** la cascade TJR utilise, ce qui valide les tentatives Aplus_01/03/04.
  - Equilibrium explicit comme alternative to FVG (pas juste FVG). Le bot actuel a FVG dans `continuation_confluence` mais **pas equilibrium** formellement.
  - SMT cross-index comme filtre supplémentaire.
- **Concepts MASTER contredits** : aucun direct (les playbooks sont alignés TJR).
- **Concepts nouveaux absents de MASTER** :
  - **Equilibrium comme continuation confluence indépendante** (GAN box tool, 50% entre swing H et swing L). MASTER ne formalise pas equilibrium comme règle d'entry prospective. Le bot n'a aucun détecteur d'équilibre retracement.
  - **BOS OR IFVG alternative** pour stage 2 — actuellement le bot demande BOS strict dans certains playbooks.
  - **Leading index logic** (index qui sweep vs celui qui ne sweep pas) pour choisir quel symbol trade. Le bot trade ES et NQ indépendamment ; logique "trade le leader/laggard" absente.

## 9. Codability (4Q + 1Q classification)
- Q1 Briques moteur existent ?
  - Sweep detection : OUI (Aplus01Tracker, liquidity_sweep detector)
  - BOS 5m/1m : OUI
  - IFVG 5m/1m : OUI (detect_inverse_fvg)
  - **Equilibrium detection** : **NON** — à construire (simple : take recent swing H + swing L, compute (H+L)/2, check if price tap the mid zone dans retrace)
  - **SMT cross-index** : **NON** — à construire (comparer SPY et QQQ highs/lows alignés sur same 15m window)
  - State machine pipeline 4-stage : **PARTIEL** — Aplus01Tracker fait 5 states, à étendre/dupliquer
- Q2 Corpus disponible ? OUI (2025 SPY/QQQ).
- Q3 Kill rules falsifiables ? OUI — n>30, E[R]_pre_reconcile > 0.197R/trade (§0.7 G3 bar), peak_R p60 > 1.0R.
- Q4 Gate §20 Cas attendu ? **Risque B** (cascade très sélective = signal rare, même pattern que Aplus_01 Sprint 1 = 1 emit/9345 bars). **Risque C** (déjà testé en 1ère instantiation Aplus_01 = fail). **D possible** (si discrétion TJR non-reproductible).
- Q5 Classification : **playbook complet** (4-stage pipeline) — potentiellement Aplus_01_v2 avec enrichissements equilibrium + SMT.

## 10. Valeur pour le bot

### Validation de l'approche Aplus_01 / Aplus_03 / Aplus_04
Cette vidéo **confirme** que la cascade sweep → BOS/IFVG → FVG/EQ retrace → LTF confirmation est la stratégie TJR réelle. Les échecs Aplus_01 Sprint 1 (1 emit/9345 bars) + Aplus_03/04 v1/v2 (n=22-55, E[R]<0) suggèrent que **soit la stratégie elle-même n'a pas d'edge sur SPY/QQQ 2025, soit l'implémentation bot manque d'éléments critiques**.

### Éléments manquants identifiés vs Aplus_01 v1 testé
1. **Equilibrium comme confluence** (GAN box / 50% retracement) — jamais implémenté, test devrait l'ajouter
2. **BOS OR IFVG alternative** pour stage 2 — actuellement strict BOS
3. **SMT divergence cross-index** — absent, nouveau concept
4. **Leading index logic** — absent

### Proposition pour §0.5bis entrée #1 Aplus_01 Family A v2 TRUE HTF
Enrichir le pipeline existant avec :
- Bias pipeline TJR (FVG HTF respect/disrespect + structure HH-HL + SMT) de ironJFzNBic
- Equilibrium 5m comme alternative à FVG 5m en stage 3 (double de "shots" → potentiellement plus de matches)
- BOS 5m OR IFVG 5m en stage 2 (double)
- SMT gate cross-index en stage 1 (filter qui renforce le signal)

**Budget Stage 2 §0.7 G3 = E[R]_pre_reconcile > 0.197R/trade = TRÈS haut.** Data points historiques (Engulfing max +0.025 gross 4w M) suggèrent que cette bar ne sera pas franchie par un simple réajout de briques. La méthode TJR **peut n'avoir aucun edge** sur ce corpus/timeframe/instrument.

### Pas un nouveau playbook isolé — c'est la v2 de Aplus_01/03/04 unified.

## 11. Citations-clés
- "I'm not going to give you like a step-by-step... the comment section is going berserk saying, you didn't follow your strategy. And it's like, shut up, bro."
- "Orders being filled to change in order flow to continuation of the new trend and I'm looking to enter and I'm looking to target other draws on liquidity or internal draws on liquidity."
- "My entry confluence? Well, it's simply just waiting for price to push into the 5-minute continuation confluence. And then on the 1-minute, we break structure to the upside. And then we just simply wait for a break back down."
- "We have the potential to fill orders, we see confirmation that orders are filled, we see continuation of the trend once those orders have been filled and then we exit in areas where those orders can be liquidated."
- "The market proved me wrong and instead did what it wanted to do... and that's completely fine. We can let the market prove us wrong and we can still make money." (Admet wrong-bias fréquent.)
- "I'm not the biggest fan of support and resistance. I know there's some people that are very successful with it but me personally I'm not the biggest fan of it." (Distinction S/R vs liquidity → concept ICT.)
