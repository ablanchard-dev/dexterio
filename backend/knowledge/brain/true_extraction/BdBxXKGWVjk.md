# BdBxXKGWVjk — This Simple Concept Made Me +$1,000,000 (Full Breakdown)

**Source** : https://youtu.be/BdBxXKGWVjk · TJR · 942.8 s (~15:43) · auto-generated EN captions (457 entries)
**Date extraction** : 2026-04-24

## 1. Thèse centrale
L'**Inverse Fair Value Gap (IFVG)** est la confluence principale de TJR pour identifier un **market structure shift** AVANT qu'un break of structure (BOS) n'ait formellement lieu. Un FVG qui devait agir comme continuation zone mais qui est **closed through** signale l'invalidation du trend courant → entrée précoce sur reversal. À utiliser toujours **après un liquidity sweep** (pas en isolé).

## 2. Mécanisme complet
- **HTF bias** : non-formalisé dans cette vidéo mais implicite via le draw of liquidity HTF (la vidéo renvoie à sa vidéo sur liquidity). Le setup IFVG est toujours **post-sweep** d'un pool HTF.
- **Setup TF** : FVG et IFVG peuvent être identifiés sur **tous TFs** mais TJR montre principalement 1m / 5m pour l'entry, avec le sweep sur 1H / 4H pool.
- **Entry trigger** (séquence complète "Liquidity Sweep → IFVG → FVG fill" devenant la stratégie full TJR) :
  1. **Sweep d'un pool HTF** (4H / 1H high ou low).
  2. **IFVG** = un FVG formé dans le sens du trend pré-sweep qui se fait **closed through** (candlestick closure au-delà du FVG). Closure au-dessus d'un bearish FVG → invalide bearish order flow → bullish shift. Closure en-dessous d'un bullish FVG → invalide bullish order flow → bearish shift.
  3. **Continuation new trend** : après IFVG, attendre un FVG dans la nouvelle direction et pullback sur ce FVG pour entry.
- **Stop loss** : NON-EXPLICITEMENT-SPÉCIFIÉ. Inférence : extremum pré-IFVG (low du swing avant la bullish IFVG pour LONG, high pré-IFVG pour SHORT).
- **Take profit** : non-explicitement formalisé dans cette vidéo mais renvoie à "continuation of new trend" et target highs/lows (implicitement liquidity pools opposés — vidéo 13 liquidity).
- **Exit logic** : NON-SPÉCIFIÉ ici.
- **Sizing** : NON-SPÉCIFIÉ.

### Règle spéciale : Stacked FVGs
- Quand 2+ FVGs dans la même direction sont **stacked sans contrebougie entre eux** (no opposite-color candle between), ils sont traités comme **un seul grand FVG**.
- Pour qualifier un **inverse valide**, on doit prendre :
  - **Bearish stack** : **low du stack** (le FVG le plus bas) comme frontière d'inversion → closure au-dessus du top de ce lowest gap.
  - **Bullish stack** : **top du stack** (le FVG le plus haut) comme frontière → closure en-dessous du bottom de ce highest gap.
- TJR formule : "we have to take the lowest gap from that stack" (downside) / "we have to wait for the tops and the bottoms of all these stacked up fair value gaps in a row with no different color candlestick in between".

## 3. Règles fermées (codables telles quelles)
- **R1 FVG définition** : 3-candle pattern. Bullish FVG = gap entre high candle 1 et low candle 3 (candle 2 traverse). Bearish FVG = gap entre low candle 1 et high candle 3.
- **R2 IFVG bullish** : FVG initialement bearish → candle **closes above** the gap top → IFVG bullish → expect rally.
- **R3 IFVG bearish** : FVG initialement bullish → candle **closes below** the gap bottom → IFVG bearish → expect sell-off.
- **R4 Closed through = candlestick closure** : c'est la **clôture** de la bougie au-delà du gap qui qualifie l'IFVG, pas juste le wick. Confirmed candle close.
- **R5 Post-sweep only** : IFVG **doit** être précédé d'un liquidity sweep (d'un pool HTF). TJR dit explicitement "notice how pretty much every single one of these examples that I've shown you has been coming off of a liquidity sweep".
- **R6 Stacked FVG aggregation** : 2+ FVGs same-direction sans candle opposite color entre eux → traité comme 1 seul gap, avec les frontières = extrêmes du stack.
- **R7 IFVG = pre-BOS entry** : l'avantage de l'IFVG est d'entrer AVANT le formal break of structure. "We can get an entry right here rather than up here after we break above this high."
- **R8 Follow-through = new FVG + retracement fill** : après IFVG, la stratégie TJR full est :
  1. IFVG forme (confirmation of shift).
  2. Nouveau FVG dans la nouvelle direction se forme.
  3. Pullback dans ce FVG → entry on fill.
  4. Target = liquidity pools dans la nouvelle direction.

## 4. Règles floues / discrétionnaires (nécessitent interprétation)
- **"Close through"** : sur quel TF exactement ? 1m closure count ? 5m ? Cohérent avec les exemples 1m/5m mais non-fixé.
- **Tolérance de distance** : un IFVG à 0.5R du sweep vs 5R du sweep, même validité ?
- **Quelle taille minimum du FVG pour être valide ?** Un micro-gap de 0.01% = IFVG ?
- **Combien de temps après le sweep doit arriver l'IFVG ?** 1 bar ? 10 bars ? 1 hour ? Non-spécifié.
- **"Stack sans contrebougie"** : que faire si une doji indécise entre deux FVGs ? Compte-t-elle comme "different color" ?
- **Prioritisation** entre plusieurs IFVGs post-sweep (si 3 FVGs sont invalidés rapidement, lequel on prend ?).
- **Fallback si new FVG post-IFVG n'arrive jamais** : est-ce qu'on entre quand même ? Ou on skip ?

## 5. Conditions fertiles
- **Post liquidity sweep** d'un pool HTF (4H / 1H).
- **Bounded reversals** : catching tops/bottoms, pas mid-trend.
- **TFs intraday** : TJR montre exemples 1m / 5m / 15m.
- **Market structure shift reversal context** (après sweep d'un HTF pool, attendre shift).

## 6. Conditions stériles
- **Pas de sweep préalable** : TJR dit "what I don't want you guys to do is just say 'hey, this fair value gap didn't hold up. We inversed it. We're going to freaking change trends completely.' We need to be able to identify how the market's moving."
- **FVG mid-trend sans context de reversal potential** : invalid use.
- **Stacked FVG mal interprété** : prendre le mauvais gap (pas le lowest/highest) → faux signal.

## 7. Contradictions internes / red flags
- **Claim $1M** — non-auditable.
- **Cherry-picked exemples** : tous les exemples IFVG montrés ont fonctionné. Zéro exemple d'IFVG failed. Aucun hit-rate statistique.
- **"In this case it would have been better to go with the breakout structure to the upside on this candlestick because that's showing a shift in market structure before we get the inverse"** — TJR admet implicitement que parfois un BOS classique est supérieur à l'IFVG, mais ne formalise pas quand.
- **Confirmation bias construction** : "If FVG holds → continuation. If FVG doesn't hold → reversal." Règle no-true-scotsman : toute issue est explicable a posteriori.
- **"Literally this video turned into a strategy video in 2 seconds"** — TJR condense toute sa stratégie en 1 paragraphe à la fin : sweep → IFVG → FVG pullback → target liquidity. Le concept fondamental de sa stratégie est donc dans 4 séquences simples — suspicion de trivialité masquant la complexité réelle du timing.
- **Stacking rule arbitraire** : "no different color candlestick between" — la règle est précise mais non-justifiée théoriquement. Pourquoi pas "no opposite-direction closure" ou "no retracement > X%" ? Règle ad-hoc.

## 8. Croisement avec MASTER (contexte bot actuel)
- **Concepts MASTER confirmés** : FVG définition 3-candle identique à ce qu'on a déjà codé, IFVG concept (Aplus_03 est littéralement "IFVG Flip").
- **Concepts MASTER nuancés/précisés** :
  - **IFVG stacking rule** : règle explicite "prendre le lowest/highest gap du stack sans candle opposite-color entre". **NOUVEAU pour le bot** — notre détecteur IFVG actuel (Aplus_03_v1, R.3, v2) traite chaque FVG individuellement sans logique de stack aggregation. Explique potentiellement un bruit de signal.
  - **"Post-sweep only"** : notre Aplus_03 (IFVG Flip) est utilisé en standalone sans check préalable de sweep HTF. **NOUVEAU** : rajouter un gate "require_prior_sweep: 4h|1h".
  - **Séquence full stratégie "Liquidity Sweep → IFVG → FVG fill → Liquidity target"** : **notre Aplus_01 Family A** (Sprint 1) avait essayé cette séquence (sweep 5m → BOS 5m → confluence touch → 1m pressure) mais **Aplus_01 utilisait BOS au lieu d'IFVG comme signal de shift**. Le upgrade IFVG-as-shift-confirm (pre-BOS) pourrait améliorer le densité de signal (Aplus_01 a failed avec 1 emit / 9345 bars car BOS confirmed très tard).
- **Concepts MASTER contredits** : aucun.
- **Concepts nouveaux absents de MASTER** :
  - **"Pre-BOS entry via IFVG"** : entrer sur le candlestick close de l'IFVG, AVANT qu'un BOS formel ne se forme. Notre bot attend toujours BOS — **nouveau timing potentiel**.
  - **Stacked FVG aggregation rule** — nouveau.

## 9. Codability (4Q + 1Q classification)
- **Q1 Briques moteur existent ?** **OUI pour 80%, NON pour 20%**.
  - OUI : détecteur FVG (utilisé dans FVG_Fill_V065, Aplus_03), détecteur IFVG (Aplus_03_IFVG_Flip_5m existant), détecteur sweep (Liquidity_Sweep patterns), `tp_logic: liquidity_draw` (Option A v2).
  - NON : **règle de stacking FVG** (aggregation multi-FVG en single gap) non-implémentée. **Pre-BOS IFVG entry** timing non-codifié séparément du BOS gate.
- **Q2 Corpus disponible ?** OUI — `calib_corpus_v1` + Polygon 18m.
- **Q3 Kill rules falsifiables possibles ?** OUI.
- **Q4 Gate §20 Cas attendu identifié ?** **Cas C probable (edge absent)** avec risque **Cas B (sous-exercé)** selon density. **Avertissement empirique** : IFVG sur Aplus_03 (v1, R.3, v2) a été testé et a produit E[R]_gross de -0.019 à -0.074 **négatif**. L'IFVG **seul** ne donne pas d'edge sur SPY/QQQ 2025 intraday. Ce que cette vidéo ajoute (stacking rule + pre-sweep gate + post-IFVG FVG-pullback) n'est **pas** encore testé. Mais risque fort de continuation Cas C.
- **Q5 Classification** : **management / playbook**. L'IFVG seule = déjà testée (negative). L'**ensemble séquentiel "sweep → IFVG → FVG pullback → liquidity target"** = nouveau playbook candidat combinatoire, possiblement `Aplus_05_TJR_Full_Sequence_v1`.

## 10. Valeur pour le bot
**MOYENNE.** Cette vidéo apporte deux précisions mais l'IFVG seule est déjà réfutée empiriquement (Aplus_03 v1/R.3/v2 tous négatifs) :

1. **Upgrade stacking rule** : implémenter l'aggregation de FVGs stackés dans le détecteur IFVG. Effet attendu : bruit de signal réduit, quelques faux IFVG éliminés. Potentiellement marginal sur E[R] si le plafond est le signal, pas le détecteur.

2. **Pre-sweep gate** : rajouter un filtre "IFVG must be preceded by 4H or 1H liquidity sweep within N bars" sur Aplus_03_v2. Explique peut-être le fallback 73% observé (Aplus_03_v2 sans sweep context = IFVG décoré, pas IFVG structurel). **Effet attendu** : n réduit mais E[R] potentiellement amélioré si le sweep est le vrai prerequisite.

3. **Nouveau playbook combinatoire `Aplus_05_TJR_Full_Sequence_v1`** : séquence complète sweep HTF → IFVG → new FVG pullback → target opposite liquidity pool. **Différent d'Aplus_01** (qui utilise BOS au lieu d'IFVG comme shift confirm). L'IFVG permet une entrée plus précoce et peut résoudre le "1 emit / 9345 bars" problème d'Aplus_01.

**Priorité suggérée** :
- **Moyenne** : implémenter stacking rule + pre-sweep gate comme upgrade d'Aplus_03_v2, re-smoke 1-week allowlist solo pour data point sur l'effet net.
- **Basse** : nouveau playbook Aplus_05 combinatoire. Risque fort de répéter Aplus_01 smoke fail (signal rare) sans vrai edge.

**Note critique** : la vidéo 12 (SMT divergence) propose un signal **structurellement nouveau** (dual-asset), alors que cette vidéo 14 (IFVG) raffine un signal déjà 4× testé négatif. **La priorité §0.5bis devrait aller à la vidéo 12**, sauf si l'apprentissage méta dit "cross-video synthèse = chain sweep → IFVG → SMT → liquidity completion".

## 11. Citation-clés
- *"We can get an inverse of this bullish confluence first before having to close underneath this low, then that gives us a significant advantage in being able to enter a trade maybe a little bit earlier instead of having it to enter it when we get underneath this low right here."* — [115–130] — **fonde l'avantage pre-BOS entry via IFVG**.
- *"When we have two fair value gaps stacked on top of each other like this without a different candlestick in between… these two fair value gaps are pretty much treated as one. And in order for us to qualify us inversing the gap we need to take the lowest gap from that stack."* — [288–305] — **règle de stacking, nouvelle pour le bot**.
- *"Notice how pretty much every single one of these examples that I've shown you has been coming off of a liquidity sweep. So again, what I don't want you guys to do is just say 'hey, this fair value gap didn't hold up. We inversed it.'… If the market has the potential to fill orders via a liquidity sweep, then we know that market has the potential to reverse."* — [401–417] — **IFVG n'est valide que post-sweep. Gate nécessaire**.
- *"We're looking for potential to fill orders. We're looking for confirmation that those orders were filled through a market structure shift. And then we're looking for a continuation of that trend. We can simply look for a liquidity sweep inverse fair value gap and then fair value gap getting filled and then boom, we're off to the freaking races."* — [427–449] — **la stratégie full TJR en 4 étapes : sweep → IFVG → FVG-pullback → target**.
