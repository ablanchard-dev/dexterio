# FJch02ucIO8 — $1,000,000+ From One Simple Confluence

**Source** : https://youtu.be/FJch02ucIO8 · TJR · 1375.04 s (~22:55) · auto-generated EN captions (584 entries)
**Date extraction** : 2026-04-24

## 1. Thèse centrale
La "one simple confluence" qui a fait sept figures à TJR est la **SMT divergence** (Smart Money Technique) : comparer deux indexes positivement corrélés (idéalement **S&P 500 et NASDAQ**) — quand l'un casse la structure au draw of liquidity et l'autre continue sa tendance, le casseur est l'index *leading*, l'autre est *lagging* et va suivre. Utilisable comme **bias** ET **entry** ET **target** (liquidity du low/high attaché à la SMT).

## 2. Mécanisme complet
- **HTF bias** : déterminé par une SMT divergence sur **4H** (exemple TJR : "we have a 4-hour high here… the S&P pushed well above it while NASDAQ stayed under"). La SMT HTF donne un **directional bias intraday** (ce jour-là : bearish bias). Actifs préférés : **indexes corrélés SPY/ES + NASDAQ/NQ** ; TJR mentionne EUR/GBP et or/argent mais note que la corrélation est moins forte.
- **Setup TF** : la SMT divergence peut se former sur **n'importe quel TF** (4H pour bias, 1H/15m/5m/1m pour entry). Le setup typique : on attend un **draw on liquidity HTF** (4H high ou low, ou FVG HTF, ou session high/low), price vient s'y chercher.
- **Entry trigger** : un index sweep le pool (fait un higher high / lower low) ET l'autre index **refuse de le faire** (fait un lower high ou higher low sur la même bougie / même fenêtre). C'est la SMT divergence. L'entrée se prend **au moment où la divergence se forme** (c'est-à-dire dès qu'on voit l'index leading mettre son lower-high / higher-low après sweep du draw).
- **Stop loss** : NON-EXPLICITEMENT-SPÉCIFIÉ par TJR dans cette vidéo (il ne parle pas de SL placement). Inférence logique : au-dessus du high/low de la SMT sur l'index qu'on trade (invalidation = l'index lagging refuse de suivre et dépasse à son tour).
- **Take profit** : **LIQUIDITY-TARGETING explicite**. TJR formalise la notion de **"SMT divergence completion"** : "In order for the SMT divergence to be completed, we need to take out the **low that is attached to the high** of the SMT divergence" (bearish) ou "the **high that is attached to the low** that gets put in" (bullish). Le low/high attaché = celui qui a **généré le move up/down vers le pool sweeped**. C'est un TP naturel fondé sur la structure de la divergence elle-même.
- **Exit logic** : TP unique = completion de la SMT. Pas de BE / trailing / time-stop mentionné.
- **Sizing** : NON-SPÉCIFIÉ.

## 3. Règles fermées (codables telles quelles)
- **R1 SMT pair** : trade uniquement sur **deux indexes positivement corrélés**. Nominal : (SPY, QQQ) ou (ES, NQ). Backup : (EURUSD, GBPUSD), (XAU, XAG) (plus bruités selon TJR).
- **R2 Draw of liquidity HTF** : identifier un HTF draw (4H high/low, FVG 4H, session high/low). Pas de SMT "gratuite" — toujours ancrée sur un pool.
- **R3 Bearish SMT** : l'un des 2 indexes fait `high → lower high` pendant que l'autre fait `high → higher high` sur la même fenêtre HTF pivot (même swing), et le second a effectivement sweeped le pool pendant que le premier a échoué à le sweep (ou vice-versa).
- **R4 Bullish SMT** : l'un fait `low → higher low` pendant que l'autre fait `low → lower low`, et le second a sweeped le pool low.
- **R5 Leading vs lagging** : le leading est celui qui **casse la structure** (fait le lower-high / higher-low contre-tendance). Le lagging est celui qui continue le trend. **On trade le lagging dans le sens du leading** (l'hypothèse : le lagging va suivre).
- **R6 Direction du trade** : bearish SMT → SHORT le lagging ; bullish SMT → LONG le lagging.
- **R7 TP = SMT completion** :
  - Bearish : TP = low qui a initié le swing up menant au high/higher-high du pool sweeped (sur l'index lagging qu'on trade).
  - Bullish : TP = high qui a initié le swing down menant au low/lower-low du pool sweeped (sur l'index lagging qu'on trade).
- **R8 Multi-TF** : même règle applicable sur 4H (bias), 1H (intraday bias), 15m/5m/1m (entry).

## 4. Règles floues / discrétionnaires (nécessitent interprétation)
- **Quel pool HTF est "key" ?** TJR dit "key draw on liquidity" sans définir formellement ce qu'est "key". Inference : probablement 4H ou daily swing highs/lows récents, session highs/lows (Asia, London, NY PM).
- **Fenêtre temporelle de comparaison SMT** : TJR dit "comparing highs and lows" sans préciser combien de bars / quelle fenêtre pour qualifier que les deux "highs" sont alignés. Besoin d'un pivot k-lookback type k3 ou k5 des deux séries sur fenêtre commune.
- **Tolérance du pivot** : quand les deux indexes ne sont pas synchronisés à la bar près, que faire ? Réponse TJR implicite : comparer les derniers pivots formés.
- **SL placement** : non-spécifié.
- **Position sizing / R model** : non-spécifié.
- **Quand ignorer une SMT** : non-spécifié (TJR ne mentionne pas de contexte où SMT échoue).

## 5. Conditions fertiles
- **Sessions NY open et pre-market** : exemples TJR tous sur market open 9:30 ET et pre-market.
- **Assets** : **SPY/QQQ (ou ES/NQ)** — c'est LE use-case principal.
- **Après sweep d'un pool HTF** : SMT = divergence seulement valable quand un side (le leading) a effectivement sweeped un level de liquidité identifiable.
- **4H timeframe pour HTF bias** : l'exemple principal est 4H.

## 6. Conditions stériles
- **Pas de pool HTF sweeped** : SMT sans liquidity anchor = invalide (TJR l'implique toute la vidéo en ancrant chaque exemple sur un "key draw on liquidity").
- **Pair peu corrélée** : "gold and silver, Euro and pound — I haven't seen as much correlation as indexes".
- **Timeframes sans divergence claire** : si les deux indexes font la même chose (both higher high OU both lower high), pas de SMT → pas de trade.

## 7. Contradictions internes / red flags
- **Claim de profitabilité non-vérifié** : "seven figures over the past couple years" — standard TJR claim, non-auditable.
- **Exemples cherry-picked** : tous les exemples montrés sont des SMT qui ont fonctionné. Pas de SMT failed montrée, pas de hit-rate statistique.
- **Pas de règle d'invalidation** : TJR ne dit jamais "la SMT est invalidée si X" — donc risk-management floue.
- **Simplisme apparent** : "it's very very simple, very very easy confluence" — red flag typique, les edges rentables sont rarement triviaux.
- **"NASDAQ is eventually going to follow the S&P 500"** — le mot "eventually" est non-codable. Sur quelle fenêtre ? 1 bar ? 10 bars ? 1 session ? TJR ne précise pas.
- **"You can literally get an entry right the now"** — aucune règle sur la qualité d'entrée (entry au prix de la SMT formation = slippage vs entry après confirm break of structure ?).

## 8. Croisement avec MASTER (contexte bot actuel)
- **Concepts MASTER confirmés** : liquidity sweep comme zone où orders se fillent, reversal off sweep of HTF pool, notion de draw of liquidity HTF.
- **Concepts MASTER nuancés/précisés** : SMT divergence est explicitement un **dual-asset confluence** — notre bot actuel ne compare pas deux symbols. Les MASTER mentionnent SMT mais nous n'avons **aucun playbook qui croise SPY et QQQ**. Notre Sprint 3 / Leg 4.1 Stat_Arb_SPY_QQQ v1+v2 regarde la **cointégration** mais pas la SMT. C'est deux concepts distincts : cointégration = stationnarité du spread ; SMT = divergence de structure sur un sweep de pool.
- **Concepts MASTER contredits** : aucun.
- **Concepts nouveaux absents de MASTER** :
  - **"SMT completion" comme TP target structural** — notre bot utilise fixed RR TPs ou (récemment) `tp_logic: liquidity_draw swing_k3`. La SMT completion est un **3e type de TP** : le low/high attaché au swing qui a créé le pool sweeped, pas n'importe quel pool. **Nouveau pour le bot**.
  - **Dual-asset signal** : n'apparaît dans aucun de nos 26 playbooks actuels. **Nouveau pour le bot**.
  - **Leading vs lagging index classification** comme entry trigger — nouveau pour le bot.

## 9. Codability (4Q + 1Q classification)
- **Q1 Briques moteur existent ?** **PARTIELLEMENT**.
  - OUI : détecteur de pivots k-lookback (`directional_change.py` avec swing_k3/k9), détecteur de liquidity pools (FVG / OB / sweep), `PairSpreadTracker` (D2, Sprint 3) peut fournir l'infra dual-symbol.
  - NON : pas de détecteur SMT actuellement, pas de "leading/lagging classifier", pas de "attached low/high" extractor pour le TP completion.
- **Q2 Corpus disponible ?** OUI — `calib_corpus_v1` contient SPY+QQQ sync sur 4 semaines. Polygon/yfinance 18m dispo. ES/NQ = besoin futures data (pas dispo actuellement).
- **Q3 Kill rules falsifiables possibles ?** OUI — classique DexterioBOT : n≥15 / WR≥45% / E[R]_pre_reconcile > 0.197R (post §0.7 G3 budget) sur 4 semaines, sinon KILL.
- **Q4 Gate §20 Cas attendu identifié ?** Probable **Cas A ou B**. Cas A = hypothèse structurelle testable (dual-asset + pool sweep + divergence k3). Cas B possible si les divergences sont rares (le filtre pool HTF + divergence exacte pourrait produire < 10 signals / 4w).
- **Q5 Classification** : **playbook** (new candidate : `SMT_Divergence_SPY_QQQ_v1`) — combinable avec liquidity-targeting TP.

## 10. Valeur pour le bot
**ÉLEVÉE.** Cette vidéo fournit potentiellement la **confluence manquante** que nos 10 data points négatifs ont révélée :
1. **Nouveau playbook candidat prioritaire** : `SMT_Divergence_SPY_QQQ_v1`. Infrastructure 50% en place (pivots k3, liquidity pools, PairSpreadTracker). Reste à coder : détecteur SMT divergence croisé + extracteur "attached low/high" pour TP.
2. **Nouvelle primitive TP** : `tp_logic: smt_completion` — TP non pas sur n'importe quel pool, mais sur le low/high attaché au swing de la SMT. À ajouter au `tp_resolver.py`.
3. **Explication potentielle des échecs** : tous nos playbooks actuels sont **single-asset** (SPY ou QQQ séparément). Si TJR a raison, l'edge vient du **cross-asset signal**. Nos 26 playbooks négatifs × cohérent avec "signal insufficient en single-asset, sufficient seulement en SMT".
4. **Synergie avec quarantine survivors** : un filtre SMT divergence en overlay sur News_Fade / Session_Open / Engulfing (les 3 survivors quasi-BE de Phase D.1/Leg 4.2) pourrait potentiellement leur donner le push cross-E[R]>0 qui a manqué.
5. **Risque** : claim "simple confluence → $1M" suspect ; 10 data points MASTER négatifs suggèrent que l'univers ICT est déjà réfuté. Mais SMT **n'a jamais été testée** sur DexterioBOT (confirmed par Phase D.2 TF audit — 0/26 playbooks utilisent dual-asset SMT). C'est donc un **vrai nouveau data point potentiel**, pas un re-test.

**Priorité suggérée** : candidat §0.5bis backlog, à positionner après §0.7 G4 verdict templating, avant autre pivot. La confluence est précise, codable, kill-rules claires, et adresse directement la dual-asset gap de la Phase D.2.

## 11. Citation-clés
- *"An SMT divergence is as simple as identifying the current trend on one of our two indexes… we are using the S&P 500 and the NASDAQ. These are really the best asset classes to use when using an SMT divergence."* — [21.36–43.84] — **fonde le dual-asset SPY/QQQ pair exactement = notre pair**.
- *"Whichever index is changing the current trend is actually telling us the future of where the other index is going to go… NASDAQ is the lagging index and ES or the S&P 500 is going to move higher off of this key area where orders can be filled and NASDAQ is going to eventually follow suit."* — [93.68–490.24] — la règle de causalité leading→lagging.
- *"In order for the SMT divergence to be completed, we need to take out the lows that are attached to the highs… We have a high, we have a lower high. SMT divergence gets formed. In order for us to complete the SMT divergence, we have to take out this low."* — [1150.16–1178.32] — **la règle de TP structural** (le low/high attaché), à coder en `tp_logic: smt_completion` nouveau dans `tp_resolver.py`.
- *"I use it for two different things. I use it for bias and then I can also use it for entries… on not only the high time frames but also the low time frames."* — [929.2–939.6] — **bias HTF + entry LTF**, pattern applicable à nos TF existants.
