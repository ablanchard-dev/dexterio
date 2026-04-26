# pKIo-aVic-c — Liquidity Is The Easiest Way To Become Profitable FAST

**Source** : https://youtu.be/pKIo-aVic-c · TJR · 1499.92 s (~25:00) · auto-generated EN captions (768 entries)
**Date extraction** : 2026-04-24

## 1. Thèse centrale
Toute la stratégie TJR est fondée sur **liquidity sweeps** comme signal d'entrée **et** comme target de sortie : liquidity = **stop orders / limit orders resting above highs & below lows**. Les market makers doivent sweep ces pools pour filler leurs positions. On trade **en contre-sweep** (reversal trader, pas trend trader) et on **targete les pools opposés** comme TP. Les pools prioritaires sont **4H highs/lows** et **1H highs/lows** pour trader NY open.

## 2. Mécanisme complet
- **HTF bias** : avant market open NY 9:30 ET, TJR marque manuellement les **4H highs/lows** et **1H highs/lows** non encore sweeped (pendant la session précédente ou pre-market ou London). Si déjà sweeped pendant pre-market avec reaction, il prend le trade reactif ; sinon il attend le sweep à NY open.
- **Setup TF** : 4H + 1H pour identifier les pools. 1m / 5m pour l'entry/confirmation post-sweep.
- **Entry trigger** :
  1. Price sweep un pool identifié (low / high préalablement marqué).
  2. **Reaction** sur LTF : break of structure LTF dans le sens opposé au sweep, ou change in market structure LTF.
  3. C'est **la reaction** qui qualifie le sweep comme valide. TJR : "If price comes down and takes out a low and keeps going down, is it a liquidity sweep? No. Because it's not reacting to it."
- **Stop loss** : NON-EXPLICITEMENT-SPÉCIFIÉ dans cette vidéo (TJR ne parle pas de SL exact placement). Inférence standard ICT : au-delà du wick du sweep (quelques ticks au-dessus du high sweeped pour un SHORT, au-dessous du low sweeped pour un LONG).
- **Take profit** : **LIQUIDITY-TARGETING EXPLICITE. C'EST LE CŒUR DU MESSAGE.** TJR dit littéralement : "I use draws on liquidity not only as entry points, but also as exit points. It's literally the only way that I look for entries and exits from the market." TP = **pool opposé** (high si on est LONG, low si on est SHORT) identifié comme **draw on liquidity** (4H ou 1H). Logique : on sort quand les market makers rebookent leurs positions à l'inverse.
- **Exit logic** : TP structural = prochain pool de liquidité dans le sens du trade. Pas de BE / trailing / time-stop explicitement mentionné dans cette vidéo.
- **Sizing** : NON-SPÉCIFIÉ.

## 3. Règles fermées (codables telles quelles)
- **R1 Liquidity définition** : liquidity lies **above highs** (buy-side liquidity, BSL) and **below lows** (sell-side liquidity, SSL). Un high = pattern 2-candles up-then-down. Un low = pattern 2-candles down-then-up.
- **R2 TF priorité pools** : **4H > 1H** pour pools. TJR : "the best time frames or at least for the way that I trade to be able to identify liquidity on for me is going to be the 4 hour and the 1 hour."
- **R3 Pools non-sweeped préservés** : TJR marque les 4H/1H highs/lows qui **n'ont pas encore été touchés** (ni pendant session précédente, ni pendant pre-market, ni pendant London). Si déjà sweeped avec reaction → trade reactif maintenant. Si non-sweeped → attente du sweep à NY open.
- **R4 Session NY open** : focus 9:30 ET. "I'm trading New York market open at 9:30 a.m. Eastern time every single day."
- **R5 Reaction requise** : sweep sans reaction = pas de sweep valide. Reaction = break of structure LTF dans le sens opposé ou change of trend LTF après le touch du pool.
- **R6 Direction du trade** : trade **contre le sweep** (reversal trader). Sweep high → SHORT ; sweep low → LONG.
- **R7 TP = draw on liquidity opposé** :
  - LONG : TP = 4H ou 1H **high non-encore-sweeped** (BSL pool) au-dessus.
  - SHORT : TP = 4H ou 1H **low non-encore-sweeped** (SSL pool) en-dessous.
- **R8 Pool stacks** : plusieurs highs/lows proches ("hourly lows stacked up") — sweep qui prend tout le stack en une fois = signal fort ("took out this low, took out this low, took out this low, then reaction").
- **R9 Fractal** : même logique applicable sur weekly, daily, 4H, 1H, 15m, 5m, 1m. On choisit le TF selon l'intraday strategy.

## 4. Règles floues / discrétionnaires (nécessitent interprétation)
- **Quelle distance de pool est "actionnable" ?** TJR ne précise pas : un 1H high à 0.1% de l'entry vs 1% de l'entry, même priorité ?
- **Qu'est-ce qu'une "reaction" précise sur LTF ?** TJR dit "reaction" sans définir la taille minimale du move, le nombre de bars nécessaires, la qualité du BOS. Discrétionnaire.
- **Quels pools "key" priorisés ?** Quand plusieurs pools sont dispos (4H high + 1H high + session high + Asia high), lequel targete-t-on en priorité ? TJR ne le précise pas explicitement. Inference : le plus proche dans la direction du trade.
- **Comment filtrer les "fake sweeps" (sweep puis continuation trend) des "real sweeps" (sweep puis reversal) ?** TJR dit "wait for reaction" mais ne définit pas formellement le seuil.
- **Comment combiner avec SMT divergence et IFVG ?** TJR mentionne qu'il a "d'autres vidéos sur d'autres confluences" (SMT, IFVG) mais ici ne formalise pas la stacking.
- **Pre-market pools** : TJR mentionne que les pools pré-NY-open peuvent être sweeped en pre-market. Comment on marque exactement les pools pre-market ? Flou.

## 5. Conditions fertiles
- **NY market open 9:30 ET** : session la plus explicite dans la vidéo.
- **Après pre-market sweep avec reaction** : trade "reactive" au marché open.
- **4H / 1H pools stacked** (plusieurs lows ou highs proches) — sweep qui rase le cluster = meilleur signal.
- **Indexes** (exemples TJR tous sur NASDAQ / SPY).
- **Weekly / monthly flash crash lows** ("flash crash we come down we sweep out this monthly low and next thing you know they're up 50% on their portfolio for the year") — macro reversals.

## 6. Conditions stériles
- **Sweep sans reaction** = not a valid liquidity sweep. "If price comes down and takes out a low and keeps going down, is it a liquidity sweep? Fuck no. Because it's not reacting to it."
- **Pas de pool clair** : si pas de 4H / 1H high/low identifiable ou tous déjà sweeped, pas de trade (implicite).
- **Trend continuation blindly** : TJR dit explicitement qu'il n'est PAS trend trader. Acheter au-dessus d'un high parce qu'on est en uptrend = comportement retail critiqué.

## 7. Contradictions internes / red flags
- **"Manipulation" narrative** : TJR personnifie les "market makers" qui "fuck you to the buyers and fuck you to the short sellers". Narrative psychologique populaire mais **non-vérifiable empiriquement** — on peut implémenter la logique structurelle sans adhérer à la narrative.
- **Claim $1M et "multi six figures on this move up today"** : non-auditable.
- **Exemples cherry-picked** : tous les exemples montrés sont des sweeps qui ont reversé. Pas un seul exemple de sweep failed (continuation). Aucun hit-rate statistique présenté.
- **"There's truly no better confluence in trading than liquidity sweeps. Argue with a fucking wall."** : claim absolu, red flag. Notre corpus a plusieurs playbooks explicitement liquidity-sweep-based (`Liquidity_Sweep_Scalp` KILL, `Liquidity_Raid_V056` KILL, `London_Fakeout_V066` KILL) qui ont tous été négatifs.
- **Confirmation bias inhérent** : "real sweep = reaction, failed sweep = not a sweep" — construction no-true-scotsman : toute continuation post-sweep est reclassée a posteriori comme "not a real sweep". Non-falsifiable.
- **Tone simpliste** : "Literally as simple as…" répété. Edges rentables rarement triviaux.

## 8. Croisement avec MASTER (contexte bot actuel)
- **Concepts MASTER confirmés** : liquidity sweep = orders filled at pool, BSL/SSL définition, fractal TF application, reversal trader archetype.
- **Concepts MASTER nuancés/précisés** :
  - **"Pools non-sweeped sont les seuls actionnables"** — filtre que notre bot n'applique pas actuellement. Nos playbooks sweep-based (Liquidity_Sweep_Scalp, Liquidity_Raid_V056) ne tiennent **pas** compte de si le pool a déjà été sweeped en session précédente, pre-market ou London. Pourrait expliquer partiellement leur fail.
  - **"4H + 1H only"** pour pool selection — notre bot utilise 5m/1m pools majoritairement, parfois 15m. **MASTER précise 4H+1H**. Gap direct.
  - **TP = opposite pool as target** — notre bot utilise `tp_logic: liquidity_draw swing_k3` (nouveau v2) qui cherche le prochain swing_k3 pool, pas spécifiquement un 4H/1H pool. Précision possible : paramétrer `pool_tf: ["4h", "1h"]` dans `tp_resolver`.
- **Concepts MASTER contredits** : aucun.
- **Concepts nouveaux absents de MASTER** :
  - **"Session-bounded pool state"** : mark pools AU DÉBUT de NY session en excluant ceux déjà sweeped en pre-market / London / session précédente. Concept "freshness" des pools. Nouveau pour le bot (notre `tp_resolver` cherche des pools "present" sans état de freshness).
  - **Reactive trade** : si pool déjà sweeped en pre-market avec reaction, prendre le trade dès l'open. Pattern spécifique.
  - **Pool stacks priorité** : quand un sweep rase un cluster de 3+ lows/highs stackés en une seule descente/montée, c'est un signal plus fort.

## 9. Codability (4Q + 1Q classification)
- **Q1 Briques moteur existent ?** **OUI pour 70%, NON pour 30%**.
  - OUI : détecteur swing pivots (`directional_change.py` swing_k3/k9), détecteur sweep (`liquidity_sweep` pattern), 5m/1m resampling (TFA fixée engine_sanity_v1), TP resolver liquidity_draw (Option A v2 schema), pool identification (swing highs/lows).
  - NON : **aucun détecteur "4H pool freshness"** (état non-sweeped tracké depuis session précédente). Aucun détecteur "pre-market sweep with reaction". Aucun filtre "pool stack" (cluster de lows/highs).
- **Q2 Corpus disponible ?** OUI — `calib_corpus_v1` SPY+QQQ 4 semaines, extensible Polygon 18m.
- **Q3 Kill rules falsifiables possibles ?** OUI — classique.
- **Q4 Gate §20 Cas attendu identifié ?** **Cas C probable** (edge absent) avec risque **Cas A (hypothèse testable)** selon implémentation. **Attention** : on a déjà KILL 3 playbooks liquidity-sweep-based (`Liquidity_Sweep_Scalp`, `Liquidity_Raid_V056`, `London_Fakeout_V066`) — donc l'hypothèse "liquidity sweep reversal simple suffit" est **empiriquement refuté**. Ce que cette vidéo propose est une **version plus stricte** (4H+1H pools only, freshness tracking, pool stack filter) qui n'a pas encore été testée en ces termes exacts.
- **Q5 Classification** : **contexte + management**. Plutôt qu'un playbook à part entière, c'est (a) un **overlay de pool freshness** applicable à tous nos playbooks liquidity-based existants, et (b) un **TP rule** (liquidity-targeting 4H+1H) applicable à tous les playbooks. Potentiellement aussi nouveau playbook **`Liquidity_Sweep_Fresh_4H_v1`** avec R1-R9 strictes.

## 10. Valeur pour le bot
**ÉLEVÉE — deux apports distincts.**

**A. TP primitive "liquidity-targeting to next fresh HTF pool"** — notre `tp_logic: liquidity_draw swing_k3` actuel identifie des swing pools mais ne tient pas compte de : (1) le TF du pool (4H > 1H > autre), (2) la freshness (pool sweeped vs non-sweeped en session précédente/pre-market). Upgrade du `tp_resolver.py` :
- Paramètre `pool_tf: list[str]` (default `["4h", "1h"]`).
- Paramètre `require_unsweeped_since: str` (default `"session_prior"`).
- **Priorité** : cette upgrade seule pourrait expliquer une partie du gap "peak_r p80 ≈ 0.7-1.0R < TP fixed 2R" observé sur 5+ playbooks (Aplus_03, Aplus_04, Engulfing, Morning_Trap, IFVG_5m_Sweep).

**B. Overlay "fresh pool filter"** applicable à tous les playbooks sweep-based. Filtre en entry : "le pool sweeped doit être 4H ou 1H freshness=true". **Rappel empirique** : Liquidity_Sweep_Scalp, Liquidity_Raid_V056, London_Fakeout_V066 ont été KILL sans filtre freshness. Avec freshness, peut-être différent. À tester, mais low priority vs SMT divergence (vidéo 12) qui est structurellement plus nouveau.

**C. Nouveau playbook candidat `Liquidity_Sweep_Fresh_NY_v1`** — stricte R1-R9, 4H+1H pools only, fresh only, NY open only, TP = opposite fresh pool. **Low priority** : l'univers liquidity-sweep reversal a déjà produit 3 KILL. Risque d'overfitting aux exceptions.

**Priorité suggérée** :
- **Haute** : implémenter "fresh pool tracker" dans `tp_resolver.py` et tester comme upgrade TP sur les playbooks REWRITE-partial existants (Aplus_03_v2, Aplus_04_v2).
- **Moyenne** : overlay fresh-pool filter sur survivors quasi-BE (News_Fade, Session_Open_Scalp).
- **Basse** : nouveau playbook dédié — déjà 3 data points négatifs sur liquidity-sweep-reversal.

### Inventaire EXHAUSTIF des types de liquidity pools selon TJR

Demandé par le brief. TJR ne formalise pas une taxonomie stricte mais la vidéo permet d'extraire :

1. **BSL (Buy-Side Liquidity)** = stops & orders above highs.
2. **SSL (Sell-Side Liquidity)** = stops & orders below lows.

Par **timeframe** (TJR cite explicitement):
- **Weekly high/low** (mentioned).
- **Monthly high/low** (mentioned — "monthly liquidity sweep").
- **Daily high/low** (mentioned).
- **4H high/low** — **priorité N°1 TJR**.
- **1H high/low** — **priorité N°2 TJR**.
- **5m / 1m** (mentioned as "shows up on every single time frame" mais non-prioritaire pour entry).

Par **session** (implicite via "pre-market", "London", "previous session"):
- **Pre-market highs/lows**.
- **London session highs/lows**.
- **Previous NY session highs/lows**.
- **Asia session highs/lows** (implied).

Par **structure pattern** (non-formalisés mais extractibles) :
- **Equal highs / Equal lows** (non nommés explicitement mais visibles dans les exemples "stacked up lows").
- **Pool stacks** (clusters de 2-3+ highs ou lows dans une zone proche) — sweep d'un stack = signal plus fort.
- **Relative Equal Highs (REH) / Relative Equal Lows (REL)** — concept ICT classique, non explicitement nommé par TJR dans cette vidéo mais cohérent avec ses exemples.

**Méthode de priorisation TJR** (extraction la plus précise possible du transcript) :
1. **Freshness first** : pool **pas encore sweeped** dans les sessions récentes (précédente + pre-market + London). TJR : "if liquidity hasn't been swept during those sessions, then awesome. I'm expecting New York market to open and then for us to sweep out liquidity during the current session".
2. **TF hierarchy** : 4H > 1H pour entry decision, extensible à daily/weekly pour context HTF.
3. **Stack density** : un pool avec plusieurs highs/lows stackés autour a priorité sur un pool isolé.
4. **Direction alignment** : après entry, le pool **opposé** sert de TP target. Ex : LONG entry sur SSL sweep → TP = prochain BSL pool (4H ou 1H) au-dessus.
5. **Reaction confirmation** : pool sweeped SANS reaction ≠ pool swept. Il faut une reaction LTF pour qualifier le sweep.

## 11. Citation-clés
- *"I use draws on liquidity not only as entry points, but also as exit points. It's literally the only way that I look for entries and exits from the market because it's how the market moves."* — [1308.16–1319.28] — **fonde le TP liquidity-targeting explicite**.
- *"The best time frames or at least for the way that I trade to be able to identify liquidity on for me is going to be the 4 hour and the 1 hour. Now, why is this important? Because I'm trading market open at 9:30 a.m. Eastern time every single day."* — [922.16–934.56] — **fonde R2 (4H+1H priorité) et R4 (NY open focus)**.
- *"If price comes down and takes out a low and keeps going down, is it a liquidity sweep? Fuck no. Because it's not reacting to it. That's why we want to mark out all the lows and all the highs."* — [1005.28–1013.20] — **règle de reaction requise pour qualifier un sweep valide**.
- *"If I see that liquidity has already been swept during pre-market and we're already reacting off of it, awesome. Then this was the liquidity sweep for the day and I'm just going to take a trade reactive off of this."* — [1143.68–1156.08] — **pattern "reactive trade" post-pre-market sweep avec reaction**.
