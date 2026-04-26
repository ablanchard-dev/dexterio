# ZF8uKPqAu8M — I Backtested the ORB Breakout + Pullback Strategy (5 Years of Data)

**Source** : https://youtu.be/ZF8uKPqAu8M · Trading Steady · 10.8 min (647.12 s) · Captions auto-generated EN
**Date extraction** : 2026-04-24

## 1. Thèse centrale
L'auteur teste la variante ORB "Breakout + Pullback + Continuation" (au lieu d'ORB pur en breakout immédiat) sur 5 ans de S&P 500 : malgré plusieurs variantes (TP 1.5R→4.5R, stop-order au top ORB, stop-order au midpoint ORB), **toutes les versions échouent**. Le "pullback wait" skippe les breakouts les plus forts et ne garde que les breakouts faibles qui retournent au range — inversion de thèse : *les meilleurs breakouts ne pullback pas*.

## 2. Mécanisme complet
- **HTF bias** : NON-SPÉCIFIÉ (aucun bias HTF D/4H dans le setup, purement structurel intraday)
- **Setup TF** : 5-minute chart pour la variante pullback (1-min non utilisé). Range défini par les **3 premières bougies 5m** (= 15 premières minutes après open NY 09:30 ET). Version originale (breakout pur) sur chart 15m.
- **Entry trigger** :
  - Step 1 : Identifier ORB high/low des 3 premières bougies 5m (09:30-09:45 ET).
  - Step 2 : Breakout = bougie qui **clôture au-delà du range** (pas wick). Height du breakout candle **> 1× ATR** pour qualifier (filtre volatilité).
  - Step 3 : Attendre un **pullback candle** = bougie qui casse dans le range puis **clôture au-dessus du range high** (pour LONG). Signale que l'ancien high agit maintenant comme support.
  - Step 4 : **Confirmation** = attendre que la bougie suivante casse le high de la pullback candle. Entry à l'open de la bougie confirmation (break of recent high).
- **Stop loss** : au bottom du range ORB (fixed). Mentionné alternative possible au bottom de la pullback candle (testé mais pas détaillé).
- **Take profit** : Version baseline **1.5:1 RR**. Variantes testées : 2.5R, 3.0R, 3.5R, 4.0R, 4.5R (pas de 2.0R explicite, increments 0.5).
- **Exit logic** : Cut-off = pas de trade après la bougie 12:00 ET. Pas de BE ni trailing mentionné. Pas de time-stop explicite hors le cut-off.
- **Sizing** : NON-SPÉCIFIÉ (sous-entendu fixed R per trade)

## 3. Règles fermées (codables telles quelles)
- Timezone = UTC-4 (New York), open 09:30 ET.
- Range ORB = high/low des 3 premières bougies 5m (15 premières minutes).
- Breakout candle doit clôturer au-delà du range (pas juste wick).
- Breakout candle height ≥ 1× ATR (rejet des mini-breakouts).
- Pullback candle = casse intra-range puis clôture au-delà du range high (LONG) / range low (SHORT).
- Entry = break of pullback candle high sur la bougie suivante.
- Stop = bottom du range ORB (LONG) / top du range (SHORT).
- TP fixed RR = 1.5× (baseline), testé jusqu'à 4.5×.
- Cut-off entrée : plus de nouveaux trades après 12:00 ET.
- Filtre range size : pas trop petit / pas trop gros **par rapport à l'ATR récent** (version d'origine ORB — non explicité pour la variante pullback).

## 4. Règles floues / discrétionnaires
- Quel ATR exactement (période ? daily ? intraday ?) : NON-SPÉCIFIÉ.
- Gestion des "second breakout" : l'auteur montre un cas où pullback initial retombe dans le range → invalidation → attend un **second breakout** + **second pullback**. Mais pas de règle formelle sur nombre max d'itérations.
- Alternative stop à la bottom of pullback candle : "testée" mais résultats pas rapportés chiffrés.
- Ratio TP 1.5 "optionnel" : "I don't have to always aim for one and a half times".
- Définition exacte de "pullback all the way into the opening range" (variante midpoint) : midpoint = milieu exact du range ORB, mais règle de bounce-off pas formalisée.

## 5. Conditions fertiles
- L'auteur backteste S&P 500 sur 5 ans (2020-2025 implicite). Note que **les 2 dernières années (2023+)** ont mieux performé que les 3 premières (2020-2022 "sideways equity curve").
- Aucun régime VIX / volatilité spécifique isolé.
- Univers testé : S&P 500 (pas de diversification mentionnée).

## 6. Conditions stériles
- **Core finding** : les meilleurs breakouts (momentum fort) **ne retournent jamais pulback dans le range** — le wait-for-pullback les filtre par construction, ne gardant que les breakouts faibles.
- L'exemple 1 (screenshot chart réel) : entry pullback et entry breakout-direct sont "practically identical" en prix → pullback n'apporte pas de meilleur entry.
- 3 premières années de backtest = equity curve sideways.
- Variante stop-order au top ORB : "even worse" — trop de losses sans confirmation.
- Variante midpoint du range : "performed even worse than before" — pour 1 trade qui fonctionne, plein de trades où price barreled through.

## 7. Contradictions internes / red flags
- L'auteur mentionne que les vidéos qui **promeuvent** cette stratégie utilisent du **cherry-picking** ("perfect cherrypicked examples, they make the setup look simple and reliable"). C'est un warning meta positif : il distingue setup idéal vs trading réel.
- Il admet avoir "spent many hours testing" et "decided to stop testing this any further" — honnête sur l'abandon.
- Aucun benchmark statistique formel (WF, permutation, OOS split) — mais explicite sur les outils.
- Pas de ratio Sharpe, pas de DD max chiffré.
- Il offre le code GitHub ("let me know in the comments if you want to see the code") — bonne foi méthodologique.
- Aucun chiffre précis de "current strategy" (breakout pur) pour comparer directement.

## 8. Résultats backtest rapportés
- **Période** : 5 ans S&P 500 (implicite 2020-2025).
- **n trades (variante pullback 1.5R)** : **130 trades** sur 5 ans (vs plus sur ORB pur original).
- **Win rate variante pullback** : "very similar to what my current strategy does" — NON-CHIFFRÉ mais proche baseline ORB (qui est lui-même non chiffré dans cette vidéo).
- **E[R]** : NON-CHIFFRÉ.
- **PF** : NON-CHIFFRÉ.
- **DD max** : NON-CHIFFRÉ.
- **Return** : "pretty poor" overall ; "final balance is far less than what my current strategy does" (ORB pur baseline).
- **Equity curve** : sideways 3 ans (2020-2022) puis up 2 ans (2023+) — mais global sous ORB pur baseline.
- **Variantes TP** (2.5, 3.0, 3.5, 4.0, 4.5) : "each increment made the strategy perform that little bit better" mais equity curve "still pretty poor" et "final balance far less than current strategy".
- **Variante stop-order top ORB** : "results are even worse" — performance "awful".
- **Variante stop-order midpoint ORB** : "performed even worse than before".

## 9. Méthodologie backtest
- Custom back-tester Python (code GitHub proposé).
- **In-sample only** 5 ans, pas de WF, pas d'OOS split, pas de permutation.
- Pas de test de significativité statistique.
- L'auteur **regarde les trades à la main** ("I actually looked at some of the trades that I was getting") → inspection qualitative, pas framework formel.
- Itératif : debug → fix bugs → re-run. Admet : "regularly had to check my simulated trade log and fix any bugs".
- Pas de coûts de transaction / slippage / spread mentionnés.
- Pas de filtre de régime marché (VIX, volatilité, trend HTF).
- **Rigueur estimée : moyenne** — honnête, inspection manuelle, mais pas de framework formel (pas de WF, pas d'OOS, pas de stat tests, pas de coûts).

## 10. Croisement avec bot actuel
- **Vs ORB_Breakout_5m DexterioBOT** (DENYLIST, E[R]=-0.10, WR=25%, n=16 sur 4 semaines 2025 SPY/QQQ) : la vidéo **ne sauve pas** ORB_Breakout_5m. Au contraire, l'auteur **confirme empiriquement** sur 5 ans S&P 500 que l'ajout d'une mécanique pullback **dégrade** le système. Les 3 variantes (pullback+confirmation / stop-order top ORB / stop-order midpoint) sont **toutes négatives**. Le bot DexterioBOT n'aurait **aucun edge à récupérer** de cette vidéo.
- **Insight négatif majeur** (cité par l'auteur comme conclusion) : "the best breakouts are the ones that have strong momentum, and they don't often pull back". → Inversion de thèse : **pullback-wait = adverse selection** (ne garde que les breakouts faibles qui retournent). Cela explique potentiellement pourquoi ORB_Breakout_5m DexterioBOT (breakout immédiat) serait déjà au mieux de ce design — et que le problème est ailleurs (signal quality, TP/SL, régime 2025).
- **Concepts MASTER/ICT applicables** : **aucun**. L'auteur n'utilise pas FVG, liquidity sweep, BOS, order block, IFVG, HTF bias, breaker, mitigation block. Approche **purement structurelle** (high/low range + bougie close + ATR filter). Aucun croisement MASTER Family A/B/C/D/E/F.
- **Gap méthodologique** : DexterioBOT = 4 semaines 2025 uniquement (Stage 1 `survivor_v1` caps actives), auteur = 5 ans IS continu. Mais même sur 5 ans, l'auteur trouve un système "poor". Le fait que DexterioBOT ORB_Breakout_5m soit négatif sur 4 semaines **n'est pas contredit** par 5 ans externes. Pas d'argument pour étendre à Polygon 18m sur ORB (pas de réouverture justifiée).
- **Ce qu'on pourrait emprunter** (si on voulait itérer sur ORB) : le filtre `breakout_candle_height >= 1× ATR` n'est pas dans notre détecteur actuel (à vérifier). Mais l'auteur montre que ce filtre n'est pas suffisant pour rendre ORB+pullback profitable.

## 11. Codability (4Q + 1Q classification)
- **Q1 Briques moteur existent ?** Partiellement. `ORB_Breakout_5m` existe déjà (DENYLIST). Détecteur ORB range 3-candle 5m = OUI. Détecteur pullback candle (casse + close back above range) = NON (à implémenter). Filtre ATR sur breakout candle height = NON implémenté spécifiquement pour ORB. Time cut-off 12:00 ET = règle standard (engine supporte session_end mais pas cut-off partiel vérifier).
- **Q2 Corpus disponible ?** OUI SPY/QQQ 1m/5m jun-nov 2025 calib_corpus_v1. Mais vidéo = S&P 500 cash 5 ans → pas directement comparable (SPY = proxy). Corpus actuel insuffisant pour 5 ans.
- **Q3 Kill rules falsifiables possibles ?** OUI sans difficulté : `n≥30 sur 4w` + `E[R]_pre_reconcile > 0.197R/trade` (Stage 2 post-G3 budget -0.097R/trade) + `peak_R p80 ≥ 1.5R` (sinon TP 1.5R inatteignable).
- **Q4 Gate §20 Cas attendu identifié ?** **Cas C dominant attendu** (edge absent — l'auteur le démontre empiriquement sur 5 ans). Cas D secondaire possible (hypothèse économique fausse : pullback-wait = adverse selection). **Hypothèse déjà réfutée par l'auteur lui-même** avant même qu'on teste.
- **Q5 Classification** : **pédagogique / méthodologie** (negative result instructive) — **PAS un playbook à tester**. L'insight "pullback wait = adverse selection sur les meilleurs breakouts" est utile comme **heuristique de design** (ne pas ajouter de pullback-wait à ORB_Breakout_5m pour le sauver).

## 12. Valeur pour le bot
**Verdict : AUCUNE réouverture §10 r11 justifiée. Confirmation externe du KILL/DENYLIST.**

Raisonnement :
1. Auteur backteste 5 ans S&P 500 la variante exacte "ORB + pullback + continuation" + 2 variantes supplémentaires (stop-order top ORB, stop-order midpoint) → **les 3 échouent**.
2. Pas de métriques quantifiées publiables, mais insight structurel fort : pullback-wait = adverse selection contre les breakouts les plus profitables.
3. DexterioBOT ORB_Breakout_5m était déjà DENYLIST sur 4 semaines 2025 (n=16 E[R]=-0.10) — la vidéo **confirme** que même avec 5 ans de data et une mécanique pullback plus élaborée, l'ORB cash index intraday est "poor". Aucun élément pour réouvrir.
4. Pas de concept MASTER (FVG/liquidity/BOS) → hors scope MASTER Family A-F.
5. **Valeur pédagogique** : l'heuristique "best breakouts ne pullback pas" est utile à noter pour éviter toute future tentation de calibrer ORB via pullback-wait. À archiver comme **data point externe convergent** avec notre propre KILL ORB.
6. Aucun playbook `Aplus_XX_ORB_Pullback` à créer. Aucune brique moteur à ajouter. Le temps de dev serait gaspillé.

Recommandation : noter le learning dans `/knowledge/brain/true_extraction/` (ce fichier) et **ne rien faire d'autre**. Pas d'entrée §0.5bis. Pas de nouvelle hypothèse.

## 13. Citations-clés
> "But I think most importantly, the best breakouts are the ones that have strong momentum, and they don't often pull back down to the opening range. [...] By sitting and waiting for a pullback, I'm essentially skipping out on the strongest breakouts, trading only those that were weak enough to come back down to the opening range."

> "Looking at the stats here, the win rate is actually very similar to what my current strategy does. I expected that waiting for a pullback to get a better price would actually give me a better win rate, but it doesn't seem to have made much of a difference. What it has done, though, is reduce the overall number of trades. So now over that 5-year period, I only got 130 trades with this system, and the overall return for the strategy was pretty poor."

> "The first problem, I think, is that many of the screenshots that we see in all of these videos that promote the strategy are these perfect cherrypicked examples. They make the setup look really simple and reliable, but as I've shown, the majority of trades don't look like this at all."
