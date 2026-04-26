# DyS79Eb92Ug — Trading LIVE with the BEST Scalper in the World (Fabio Valentini)

**Source** : https://youtu.be/DyS79Eb92Ug · Words of Wisdom Podcast (guest: Fabio Valentini) · 2h21m38s · auto-generated captions (en)
**Date extraction** : 2026-04-24

## 1. Thèse centrale
**Hyper-scalping NASDAQ (NQ) en orderflow + volume profile**, avec une approche discrétionnaire pilotée par l'**absorption des ordres** (big passive orders vs aggressive market orders) au Point of Control / Value Area High/Low d'un profil de session. Win rate 43-49%, avg winner ~$1k/contract, avg loser ~$600/contract, max winner ~$10k, max loser $3.2k. **La structure du bot n'est PAS ICT** — c'est du Volume Profile + CVD + Big Trades Bubble (footprint/tape reading). **Hors domaine direct MASTER mais informatif.**

## 2. Mécanisme complet

### Approche globale
- **Instrument** : NASDAQ futures (NQ), secondairement ES, crypto futures, et options 0DTE en lecture de sentiment (pas en execution).
- **Plateforme** : Interactive Brokers + Deep Charts (orderflow/footprint) — c'est la plateforme de Fabio (qu'il commercialise en SaaS).
- **Compte** : "multiple millions personal account" revendiqué. 10-30 contrats NQ par position.

### Modèles principaux (il cite 2)
1. **Value Area Low Fade (AAA setup)** : achat au bas du profil de valeur de la session, ciblant le Value Area High. Conditions : **absorption des sellers à la VAL** (aggressive sellers se font manger par passive buyers — visible sur footprint/big trades bubble).
2. **Momentum (breakout) model** : breakout d'un range de consolidation avec **aggressive buyers protection** sur le niveau d'avant.

### HTF bias
- **Volume Profile session-based** : point de contrôle (POC), value area high/low (70% du volume).
- **P-shape / D-shape / b-shape** (TPO-style) pour diagnostiquer le régime (trend / balance / rotation).
- **Cumulative Volume Delta (CVD)** pour confirmer la pression nette.
- **Options 0DTE flow** (matin) pour biais directionnel initial.
- **Power Hour** : 15:00-16:00 ET typiquement = expansion après rebalance.

### Setup TF
- **Range charts (40-range NQ)** préférées aux time charts pour éviter clustering open.
- **1m** si pas de range chart.
- **5m** pour vue contextuelle seulement.

### Entry trigger
- **Absorption visible** = gros ordres agressifs frappent un niveau sans le casser (visible sur "Big Trades" bubbles où chaque bulle ≥ 30 contrats en un trade pour NQ, 20 pour London).
- **Confirmation par CVD** / profil qui reste défensif.
- Multi-entry **scaling-in** : load 1-2 contrats, build jusqu'à 10-15 contrats à mesure que le prix confirme.

### Stop loss
- **Sous le dernier niveau d'absorption défensif** (buyer wall / seller wall).
- **Dollar risk strict** : max $2000 risk par trade (sur son million+), ~0.2% du compte.
- **Max daily drawdown** : $10 000 (~1% du compte).
- **Max 3-5 losing trades consécutifs → stop trading pour la journée**.

### Take profit
- **Scaling out** : partial à VAL/POC/VAH ; trailing dynamique sous niveaux d'absorption au fur et à mesure de la progression.
- **Pas de fixed RR** — exits discrétionnaires basés sur "auction failed" ou "sellers taking control back".

### Exit logic
- **BE shift ultra-rapide** : "in the first minute I want stop to zero" — obsession de mettre le SL à BE dès qu'il y a ~1-2 contrats de move dans la direction.
- **Time-based** : après expansion AAA en 10-20 min, walk away — "90% des sessions qui expand tôt rebalance jusqu'à power hour puis re-expand".
- **Trailing aggressive** : chaque nouveau niveau d'absorption = nouveau stop.

### Sizing
- **Dynamic size** : plus le prix confirme, plus on load. Scale-in pyramidal inversé (plus petits premiers, gros derniers) pour garder risk constant ~$2k.
- Jamais load 10 d'un coup → "maybe you load everything on the top of the market and you risk 4000".

## 3. Règles fermées (codables telles quelles)
- **Daily max loss** : $10k (1% absolute).
- **Max consecutive losing trades** : 3 early session → stop. 4-5 mid-session → stop.
- **Risk per trade** : $2k (0.2%).
- **Walk away rule** : "If in 10 min I made $25k, I close the platform. Holding a winner is worse than taking profit." Après expansion AAA en début de session → rebalance prévue jusqu'à power hour.
- **Never engage in contraction** (après expansion verticale) — attendre au moins 1-2h de rebalance.
- **Power hour window** : 15:00-16:00 ET = 90% des re-expansions post-rebalance.
- **"No hold Friday" rule** : Fabio exclut Vendredi de son modèle de contraction crude (post-analyse Python) — data-driven day filter.
- **Afternoon cutoff** : pas de trades "after 7pm Italian / 1pm ET" car win-rate mesuré à 20% seulement (analyse statistique Python par Luca).
- **Don't trade when sick / tired / emotionally off** — l'edge est discrétionnaire, lack of focus = $20-30k d'erreur.
- **Model diversification** : jamais un seul modèle. Un modèle ne marche que dans un régime (trend-following ne marche pas en choppy, etc.) → switch régime-based.

## 4. Règles floues / discrétionnaires
- **"Absorption"** : concept central mais visuel, dépend du footprint reader. Pas de seuil quantitatif (ex : X aggressive buys absorbés par Y passive sells en Z ms) donné.
- **"AAA setup"** : label de qualité (Triple-A) basé sur feeling "value area low + absorption + option flow aligned" — pas défini quantitativement.
- **"Feeling" of buyer/seller winning the battle** : Fabio admet "this is not something you can learn... you need certain traits of behavior".
- **Size d'entry scale-in** : "I fraction because I'm fast" → entièrement décisionnel.
- **Big Trades bubble threshold** : 30 contrats NQ NY / 20 NQ London — arbitraire.

## 5. Conditions fertiles
- **Momentum days** (trend clear dès l'open).
- **NY open first 30 min** (stabilise après open).
- **Power hour 15:00-16:00 ET** (re-expansion post-rebalance).
- **Expansion day sans Trump tweet** (conditions "normales").
- **NASDAQ > S&P** en liquidité relative pour son size (NQ peut absorber 10 contrats, pas 1000).

## 6. Conditions stériles
- **Tweet Trump / news choc** : "the market goes into a collapse of the universe, market makers pull liquidity". Slippage, volatility unreadable.
- **Consolidation / choppy** : 70% du temps selon lui — son modèle AAA ne marche pas, il switch sur "fade range" model.
- **Friday** (data-driven, 3/4 Fridays losing).
- **After 7pm Italian (1pm ET)** : win rate 20% seulement.
- **Post-expansion immediate** : "the elastic needs time to go back to normal before shooting again".
- **Low ATR / dry liquidity** : "auction really slow... it's expensive to trade because commissions".

## 7. Contradictions internes / red flags
- **Discretionary "edge in my brain"** : admet "I couldn't share the model because my edge will go to zero if it was quant". Non-codable fondamentalement.
- **Revendications extraordinaires** : $25k en 20 min, $60k semaine, 500% world cup. Non vérifiables. Personal account "multiple millions" non auditée.
- **Win rate 43-49%** revendiqué avec avg winner $1k / avg loser $600 → E[R] ≈ +0.05R à 0.10R/trade (cohérent si vrai, mais entièrement dépend d'execution speed qu'un bot ne peut probablement pas reproduire).
- **"You cannot have 1:20 RR with 75% WR"** — vraie observation statistique, mais sa propre métrique (43% WR, avg_winner/avg_loser ~1.67) n'est pas non plus remarquable (E[R] ≈ +0.15R).
- **Paid sponsor lock-in** : Alpha Prime, Deep Charts, TradeZella, Market Journal. Il vend l'orderflow platform qu'il utilise. Conflits d'intérêt évidents.
- **Capacity argument** : "this only works with $25-40M max" — reconnaît que l'edge disparaît à scale. Argue contre hedge fund career.
- **Psychologie** : "you need certain behavior traits you cannot learn" = gate sur skills non codables, utile pour justifier pourquoi peu réussissent.
- **ADHD-style decision making** : il choisit des charts/TF pour sa vitesse personnelle (range charts, 4 monitors, trackpad frustration) — non-portable.

## 8. Croisement avec MASTER (contexte bot actuel)
- **Complètement hors MASTER/ICT** — Fabio n'utilise pas FVG, IFVG, BOS, liquidity sweep, HTF bias D/4H. Il utilise Volume Profile, CVD, footprint, options flow.
- **Concepts MASTER confirmés** : aucun directement.
- **Concepts MASTER nuancés** :
  - La "liquidity" MASTER (above highs / below lows) existe aussi chez Fabio mais réinterprétée comme "wall of passive orders" — conceptuellement proche du POI/order block.
  - "Premium/Discount" MASTER correspond à VAH/VAL chez Fabio.
- **Concepts MASTER contredits** :
  - **Pas de TP fixe** — Fabio est anti-"set and forget", trailing dynamique obligatoire. MASTER/ICT est souvent structuré autour de targets fixes (liquidity pools).
  - **Pas de HTF bias structural** — Fabio est pure intraday volume-profile, ne regarde pas daily bias.
- **Concepts nouveaux absents de MASTER** :
  - **Volume Profile session** (POC / VAL / VAH / 70% area).
  - **CVD (Cumulative Volume Delta)**.
  - **Footprint / Big Trades bubbles** (orderflow tick-level).
  - **0DTE options flow as sentiment gauge** — très spécifique, nécessite data options intraday.
  - **Range charts** (40-range NQ) vs time charts.
  - **"Auction market theory"** comme cadre : market makers want to balance inefficiencies.
  - **Day-of-week / time-of-day filters via Python data analysis** (Fridays, after 1pm ET).
  - **Multi-model portfolio diversification** : compte séparé par edge, comparaison sharpe ratio, remplacement auto des models qui décroissent.

## 9. Codability (4Q + 1Q)

### Hyper-scalp orderflow (core model)
- Q1 Briques moteur existent ? **NON massif**. Pas de :
  - Footprint/tick-level data ingestion.
  - Big Trades bubble aggregation par seuil.
  - CVD calculation en temps réel.
  - Volume Profile intraday (POC/VAL/VAH calculation sur window rolling).
  - Options 0DTE flow ingestion.
- Q2 Corpus disponible ? **NON** pour tick-level NQ. **Partiel** pour SPY/QQQ 5m OHLC (pas de tape, pas d'order book).
- Q3 Kill rules falsifiables ? OUI (E[R] > 0.10R, n > 30).
- Q4 Cas §20 attendu ? **B probable** (signal tick-level impossible à reproduire sur 1m OHLC) + **D probable** (hypothèse "orderflow edge transportable sans tape" = fausse).
- Q5 Classification : **hors domaine infra actuelle** → pédagogique.

### Règles de management / risk (transportables)
- Q1 Briques ? **OUI partiellement** : kill-switch daily, max losing trades, time-of-day filter existent dans `risk_engine.py`.
- Q2 Corpus ? OUI.
- Q3 Kill rules ? OUI.
- Q4 Cas §20 ? **A ou C** — règles isolées ne créent pas d'edge, améliorent juste les bad days.
- Q5 Classification : **management rules applicables**.

### Volume Profile / Value Area brique
- Q1 Briques ? **NON** — pas de détecteur POC/VAL/VAH session-based dans le repo. Implémentable sur 5m OHLC + volume via approximation TPO-like.
- Q2 Corpus ? OUI (OHLCV 5m SPY/QQQ).
- Q3 Kill rules ? OUI.
- Q4 Cas §20 ? **C probable** (proxy VWAP déjà testé et neutre).
- Q5 Classification : **brique candidate** (value-area fade comme filtre ou target).

## 10. Valeur pour le bot

### Valeur HAUTE (actionnable)
1. **Règles de management / kill-switch data-driven** :
   - Day-of-week filter (implémenter via analyse Python sur 4w+ survivor data).
   - Time-of-day cutoff après analyse win rate par heure.
   - Max consecutive losing trades (3 early, 4-5 mid) — à ajouter si pas déjà présent.
   - Déjà partiellement dans `risk_engine.py` mais pourrait être étendu.

2. **Multi-model portfolio diversification** avec comparaison sharpe ratio / profit factor :
   - Existe conceptuellement dans DexterioBOT (survivor_v1 cohort, VIX overlay leg 4.2) mais pas comme framework structurant.
   - Idée : chaque playbook = edge indépendant, comparaison via sharpe/PF, kill auto si décay.

3. **Règle "walk away after AAA setup hits in first 20 min"** :
   - Transposable : si cohort fait +2R en first hour, cut daily activity (prevent give-back).

### Valeur MOYENNE (à explorer)
4. **Value Area / POC session** comme brique de contexte :
   - Proxy via `volume × close` sur 5m bars, window = session US 9:30-16:00 ET.
   - À tester en filter : les setups ICT long près de VAL vs près de VAH — différence d'E[R] ?

5. **CVD intraday** comme proxy delta orderflow :
   - Sur 5m OHLCV, pas de delta réel, mais approximation up-vol/down-vol possible (up_volume = volume si close>open, -volume sinon, cumul session).
   - Utilisable comme filter régime.

### Valeur FAIBLE
6. **Footprint / Big Trades** : nécessite tape data, inapplicable sans infra massive.
7. **Options 0DTE flow** : data payante (~$500/mo), ROI incertain.
8. **Range charts** : non-standard, incompatible avec l'infra bar-based actuelle.

### Valeur NULLE (pédagogique only)
9. **Narratif "you need to feel the market"** : non-codable par définition.
10. **Personal compliance narrative** (discipline, OCD organization) : interessant humainement mais sans impact technique.

### Verdict global
**Fabio Valentini vit dans un domaine (tape reading, tick orderflow, scaling-in 10-15 contrats discrétionnaire) que DexterioBOT ne peut structurellement PAS reproduire sur SPY/QQQ 5m OHLC**. L'essence de son edge = **speed of decision + tape reading**, deux choses qu'un bot ML discrétionnaire pourrait éventuellement approcher avec tick data + heavy feature engineering, mais totalement hors scope immédiat.

**Extrait utile concret** : ses règles de risk management (daily max, consecutive losers cutoff, time-of-day filter, day-of-week filter via data analysis) sont **déjà alignées avec ce que DexterioBOT fait** et renforcent la direction actuelle (kill-switch, survivor cohort, Phase D1 bias audit). Valide indirectement que l'approche risk-first du bot est correcte.

**Rien d'exploitable comme nouveau playbook**. Quelques idées de **features / overlays** (value area proxy, CVD proxy, time/DoW filters) mais toutes marginales vs la question de fond du bot (E[R] > 0 sur 2025 SPY/QQQ intraday).

## 11. Citations-clés

- **Sur le RR vs WR tradeoff** [line 913-938] : *"You can shoot for high risk-to-reward but if you shoot for high risk-to-reward you will be completely destroyed in contraction day... My average winning trade is $1000 on one contract, average losing trade is $600. If I try to shoot to get the maximum high, my win rate will get lower. I already don't have a huge win rate. I have 43 to 49%. If I want these numbers to go up and these numbers will go down. It's a balance."* → Valide empiriquement que l'E[R] de +0.10R avec WR 45% est réaliste sur un scalper pro ; DexterioBOT's E[R] < 0 sur tout 2025 est un vrai signal d'absence d'edge, pas juste de "mauvaise calibration WR/RR".

- **Sur le "walk away"** [line 617-634] : *"If I get the 20,000 profit for the day my rules say it's done because probably you will have consolidation after a strong move. We took the best move of the London and of the New York we walk away."* → Pattern "expansion tôt → rebalance → stop trading", transposable en rule bot.

- **Sur les data-driven filters** [line 2622-2647] : *"Luca one guy that helped me on this... it's not worth to take trades for example after 7 Italian time European time. Why? So he goes down the data point. your win rate is low like you have 20% win rate so remove this perfect on Friday you always lose money like uh in four weeks of the month three Friday you lose remove Friday... we removed Wednesday the model was profit factor 2.1."* → Valide la méthodologie de filtres time-of-day / day-of-week appliquée au bot.

- **Sur l'edge quant vs discrétionnaire** [line 2707-2728] : *"Jim Simmons was saying that completely systematic edge have a lot of edge decay. What does it mean that they the system breaks so fast?... I had also a portfolio of system then I start notice every month now the system four system broke out of 20 replace them."* → Rappel que même un systematic gatherer performant doit remplacer des edges régulièrement (cohérent avec bot ARCHIVED pipeline). Suggère que la réponse à "E[R]<0 2025" pourrait être edge decay (marché uptrend asymétrique, LONG toxique / SHORT meilleur documenté sur 5 playbooks DexterioBOT).

- **Sur la capacité / liquidité** [line 2359-2385] : *"NASDAQ and S&P 500 have 95% correlation S&P 500 is a lot more liquid than NASDAQ... my limit is scalability. This is the reason I'm studying with Andrea uh option models."* → Interesting side-point : un scalper pro se rabat sur **options 0DTE** pour scaler. Non pertinent pour DexterioBOT mais signale que les options pourraient être un domaine élargi pour un futur pivot.
