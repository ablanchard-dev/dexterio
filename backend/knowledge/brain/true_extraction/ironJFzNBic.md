# ironJFzNBic — Path to Profitability: How To Find Daily Bias (TJR)

**Source** : https://youtu.be/ironJFzNBic · TJR · ~31min · auto-generated EN captions
**Date extraction** : 2026-04-24
**CRITICITÉ** : le bot n'a jamais implémenté HTF bias, uniquement SMA proxy (Phase D.1 audit 0/171 rejected). Cette vidéo décrit LA méthode TJR de daily bias. Substrat potentiellement game-changer pour §0.5bis entrée #1 Aplus_01 Family A v2 TRUE HTF.

## 1. Thèse centrale
Daily bias = combinaison de (a) structure HTF 4h/1h courante (uptrend/downtrend identifié par HH-HL vs LH-LL), (b) high-timeframe imbalances/gaps récemment filled ou à filler, (c) draws on liquidity environnants (session highs/lows, previous day H/L), et (d) signal de "respect vs disrespect" d'un fair value gap HTF qui sert de continuation confluence. Le trend "external → internal → external" : high → FVG/equilibrium → high → FVG/equilibrium (cycle).

## 2. Mécanisme complet

### HTF bias process (étape par étape, verbatim extraction)
1. **Identifier tendance HTF** : regarder 4H et 1H pour pattern HH/HL (uptrend) ou LH/LL (downtrend)
2. **Identifier où on est dans le cycle** : "at what point in time are we in the high time frame trend?" — venons-nous de sweeper une liquidity ? venons-nous de casser structure ? sommes-nous dans un retrace qui revient sur un FVG ?
3. **Identifier la prochaine FVG HTF** (4H ou 1H) que price doit respecter/invalider pour définir la continuation
4. **Identifier draws on liquidity disponibles** (targets ET entries candidats) :
   - Previous day high / previous day low
   - Asia session high / low
   - London session high / low
   - (Aussi : hourly highs/lows stacked récents)
5. **Regarder pre-market + NY open** pour identifier manipulation récente
6. **Déterminer bias** via logique respect/disrespect du FVG HTF :
   - Si uptrend + price dip into FVG HTF puis fait "legs up out of it" = **bullish**, target = highs au-dessus
   - Si price dip into FVG puis **closes underneath / disrespects** it = **no longer bullish**, bias flippe baissier, target = lows
   - Si downtrend + price rally into FVG puis se fait rejeter (down close) = **bearish confirmed**, target = lows
   - Si price closes above bearish FVG = bearish trend invalidated, nouveau bias bullish
7. **SMT divergence cross-index** (S&P vs Nasdaq) : si un index sweeps high mais l'autre non, bearish SMT = signal qu'orders fills au-dessus seraient unilatéraux → downward pressure

### Setup TF
- 5m pour entry confluence (FVG fill, equilibrium fill, break of structure)
- 1m pour confirmation d'execution précise (BOS ou IFVG sur 1m après tap into 5m continuation confluence)

### Entry trigger (décrit dans cette vidéo)
- Attendre que price fill un continuation confluence (FVG 5m ou equilibrium 5m)
- Sur 1m, attendre soit :
  - Break of structure dans la direction bias
  - Inverse fair value gap 1m

### Stop loss
- "Above these highs" (stops au-dessus des highs récents sur short, sous les lows sur long) — NON-CHIFFRÉ précisément (pas de ATR multiple, pas de R unit)

### Take profit
- **Liquidity-targeting explicite** : "target these highs right here", "draws in liquidity up here"
- Multiple targets scaled : "first take profit, second take profit, third take profit" (3 TP mentionnés dans l'exemple)
- Targets = session highs/lows, previous day H/L, hourly highs

### Exit logic
- Pas de detail explicite sur BE ou trailing
- Implicite : "unable to get an entry" = skip day

### Sizing
- NON-SPÉCIFIÉ

## 3. Règles fermées (codables telles quelles)

### Définitions structurelles (codables)
- **Uptrend détecté** : sequence HH + HL confirmés sur 4H
- **Downtrend détecté** : sequence LH + LL confirmés sur 4H
- **BOS (break of structure)** : candlestick close above most recent high (uptrend reversal) ou below most recent low (downtrend reversal)
- **IFVG (inverse FVG)** : candle close **à l'intérieur** d'un FVG opposé direction, invalide le FVG
- **FVG respect** : price dip into FVG ET legs up/down hors avant close — bias continue
- **FVG disrespect** : candle close through FVG vers le côté opposé — bias flip

### Liquidity pools (draws)
- Previous day high / low
- Asia session high / low (18:00-03:00 ET)
- London session high / low (03:00-08:30 ET)
- Hourly highs / lows récents

### Règles de bias
- Rule A : HTF (4H) uptrend + price dip into FVG 4H + legs up candle → bias bullish, target HTF highs
- Rule B : HTF uptrend + price close below FVG 4H (disrespect) → bias flip bearish, target HTF lows
- Rule C : HTF downtrend + price rally into FVG 4H + rejection (down close) → bias bearish, target HTF lows
- Rule D : HTF downtrend + price close above FVG (disrespect/IFVG) → bias flip bullish, target HTF highs
- Rule E : Cross-index SMT divergence (S&P sweeps high, QQQ does not) → bias tilt bearish (for NQ) ou inverse pour ES

### Market flow cyclique
- Uptrend : external (high) → internal (FVG/equilibrium) → external (higher high) → internal → ...
- Downtrend : external (low) → internal (FVG/equilibrium) → external (lower low) → ...

## 4. Règles floues / discrétionnaires
- "We were forming a downtrend. Okay, so on the hourly time frame, we were coming into this hourly fair value gap." — lequel des multiples FVG on choisit n'est pas précisé (le plus récent ? le plus près ? celui avec le plus d'orders ?)
- "High time frame draws in liquidity" — "high time frame" pas quantifié (4H ? Daily ? Weekly ?)
- "Significant low" / "significant high" — pas de critère chiffré
- "We form a down candle right here. Did that hit this fair value gap? No. Did that hit equilibrium? No. Uh-oh." — jugement visual, pas algorithmique
- "The rest is history" (sur un trade winner) — pas de gestion explicite d'exit après take profit 1
- Choix entre "looking at the 4H vs 1H vs 5m" = discrétion cascade

## 5. Conditions fertiles
- Market structure HTF claire (HH-HL ou LH-LL bien formés, pas de range)
- FVG HTF présent et récent (non-comblé encore ou en train de l'être)
- Draws on liquidity stackés (multiple session highs/lows dans la direction visée)
- Cross-index SMT divergence (confirmation supplémentaire)
- Pre-market manipulation visible ("we came down and we manipulated these lows")
- NY open délivre manipulation puis retrace

## 6. Conditions stériles
- Jours difficiles : "this was a super ugly day, but this was the day before FOMC" — FOMC days = éviter
- "This was a high impact news day, so this isn't going to be super beneficial" — news days
- "Price action kind of sucks" (Monday exemple) — price action indécise, pas de HH-HL clair
- Absence de FVG HTF récent à trade ("we don't have a fair value gap that's formed yet")

## 7. Contradictions internes / red flags
- "The market proved me wrong and instead did what it wanted to do" — **admet que bias est souvent faux**. "My bias was bullish today... what did the market do? The market proved me wrong". Aucun chiffre sur fréquence wrong-bias.
- "I'll be like, hey, these highs look really good. I want us to target those highs, and then we'll have this exact movement happen and it's just like the market was like, you're just wrong for the day" — **concède régulièrement bias invalidé**. Mais continue quand même à présenter la méthode comme robuste.
- "Respect vs disrespect d'un FVG" = après-coup interprétation, pas règle prospective. Un FVG est "disrespected" quand price close through — mais quelle **bougie** détermine le disrespect ? 1m close ? 5m close ? 1H close ? Ambigu.
- Aucun backtest / aucune métrique (WR, E[R]) quantifiée sur la méthode.
- Exemples sélectionnés en cherry-pick ("let's go to a better day") — survivorship bias dans la démo.
- "Look it's just this" puis "unfortunately this was a bad example" → trois exemples, 2 fonctionnent clairement, 1 pas clair — sample trop petit pour conclure.

## 8. Croisement avec MASTER (contexte bot actuel)

- **Concepts MASTER confirmés** :
  - FVG definition (respect/disrespect)
  - BOS definition
  - Liquidity sweep + change of order flow
  - HTF → LTF cascade (4H → 1H → 5m → 1m)
  - Market structure HH/HL, LH/LL
- **Concepts MASTER nuancés/précisés** :
  - MASTER mentionne "HTF bias" vaguement ; cette vidéo **opérationnalise** : la bias est une décision logique **sur la base de respect/disrespect d'UN FVG HTF spécifique combiné à la structure courante + draws on liquidity**. Ce n'est PAS juste "regarder la tendance 4H avec un SMA".
  - Le bot actuel utilise **SMA_5 proxy** sur D/4H (Phase D.1 audit bias_v1). **Cette méthode est structurellement fausse vs TJR**. TJR ne parle JAMAIS de SMA. Il parle de (1) structure HH/HL, (2) FVG respect/disrespect, (3) SMT cross-index.
  - Equilibrium HTF comme continuation confluence (draw-down point).
- **Concepts MASTER contredits** :
  - Bot actuel rejette 0/171 setups sur bias gate (Phase D.1 audit). La vraie méthode TJR devrait **rejeter beaucoup plus** (quand price vient de disrespect un FVG HTF contre direction, tous les signaux de cette direction deviennent filtrés).
- **Concepts nouveaux absents de MASTER** :
  - **SMT divergence cross-index** (ES vs NQ). Signal explicite dans cette vidéo — bearish SMT = ES push high mais NQ non (ou inverse) → signaler bias baissier. **MASTER ne mentionne pas SMT cross-index pour bias daily**. C'est potentiellement NOUVEAU POUR LE BOT.
  - **Flow external → internal → external cyclique** : formalisé en "que fait un uptrend ? external (high), internal (FVG/EQ), external (higher high)". Utile comme invariant pour identifier "où on est dans le cycle".
  - **Logique respect/disrespect prospective** d'un FVG HTF comme binary gate bias = formalisable en code, pas présent sous cette forme dans les playbooks actuels.
  - **Ranking des draws on liquidity** : "Asia session high had already been pushed past London session highs and there was no reaction off of it. So in turn, that draw on liquidity is pretty much useless for us." — règle explicite : liquidity déjà swept = useless. Pas dans MASTER formellement.

## 9. Codability (4Q + 1Q classification)
- Q1 Briques moteur existent ?
  - Structure HH/HL : **PARTIEL** — `directional_change.py` (k1/k3/k9 zigzag) peut servir
  - FVG detection : OUI
  - Session highs/lows : OUI (patterns_config session windows)
  - **SMT cross-index** : **NON** — pas de détecteur cross-symbol synchronized
  - **FVG respect/disrespect state machine** : **NON** — à construire (similaire à Aplus01Tracker)
- Q2 Corpus disponible ? OUI — 2025 SPY/QQQ 1m/5m jun-nov.
- Q3 Kill rules falsifiables ? OUI — "bias gate doit rejeter >20% des setups counter-bias" + "bias-aligned E[R] > counter E[R] delta > 0.05R" (testable).
- Q4 Gate §20 Cas attendu ? **A si bien implémenté** (rejection non-triviale), **B si trop rare** (si FVG HTF + structure + SMT = rarement combinés, signal rare), **D si hypothèse économique "TJR bias method is real edge" fausse empiriquement**.
- Q5 Classification : **filtre HTF (bias gate) + potentiellement sub-playbook SMT divergence**

## 10. Valeur pour le bot

### Valeur CRITIQUE pour §0.5bis entrée #1 Aplus_01 Family A v2 TRUE HTF

Le bot actuel a le bias gate **cosmétique** (SMA proxy 0/171 rejected). Cette vidéo donne la **vraie recette TJR** en 3 composantes opérationnelles :

**Composante 1 — FVG HTF respect/disrespect gate** (codable)
- État : pour chaque symbol, tracker le FVG 4H le plus récent dans la direction de la structure courante
- Si price close through opposite side → bias flip
- Si price dip into + legs out → bias confirm
- Pas de SMA. C'est une state machine.

**Composante 2 — Structure gate HH/HL 4H** (codable avec directional_change.py existant)
- Require recent HH+HL pour bullish bias
- Require recent LH+LL pour bearish bias
- Invalide bias si structure casse sur 4H

**Composante 3 — SMT divergence cross-index filter** (NOUVEAU à coder)
- ES sweeps high t0, NQ does not within same 15m window = bearish SMT pour NQ shorts + ES shorts
- État cross-symbol synchronisé (nouveau — l'engine actuel traite symbols indépendamment)

### Proposition pour §0.5bis #1 v2
Implémenter les 3 composantes comme HTF bias pipeline strict. Re-run le gate `require_htf_alignment: D` sur Aplus_03_v2 + Aplus_04_v2 avec cette nouvelle logique. Attendu : rejection >> 0% (vs actuel 0/171). Valider que 4H-aligned subset E[R] > counter subset delta > +0.05R sur corpus historique (calib_corpus_v1 + survivor_v1).

### Risque d'échec
- La méthode peut être **post-hoc narrative** (TJR pick cherry-pick les exemples qui marchent). Phase D.1 audit trouvé "D/4H disagree about alignment" — possible que FVG respect/disrespect HTF aussi soit inconsistent. Budget Stage 2 §0.7 G3 : E[R]_pre_reconcile > 0.197R/trade = bar très haute.
- **SMT cross-index n'a jamais été testé sur ce bot** — data point nouveau, risque C/D §20.

### Pas de nouveau playbook direct. C'est un filtre HTF / bias pipeline.

## 11. Citations-clés
- "On the hourly time frame, we were coming into this hourly fair value gap. So, awesome. If this is going to continue being a downtrend, I am going to safely assume or we need to see price come into this fair value gap and respect it. If that gets respected, where is price going to draw? Down to all of these high time frame, low resistance draws and liquidity."
- "We disrespect this fair value gap, which means to me, hey, we're probably no longer going to be in bearish price action. Because if we were going to be in bearish price action, we would have respected this gap and we would have continued lower."
- "We are pushing above a high on one of the indexes and then below a high on another one of the indexes... An SMT divergence. Specifically, a bearish SMT divergence."
- "How does a trend move? It moves from boom high. Down to fair value gap equilibrium. Then back up to what? High. Then down into what? Fair value gap or equilibrium. Then back up to what? Highs. It moves from external to internal. External to internal. External to internal."
- "Asia session high had already been pushed past London session highs and there was no reaction off of it. So, in turn, that draw on liquidity is pretty much useless for us."
- "The market proved me wrong and instead did what it wanted to do." (important — auto-concession)
