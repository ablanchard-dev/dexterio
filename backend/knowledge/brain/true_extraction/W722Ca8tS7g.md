# W722Ca8tS7g — The 4 backtesting techniques behind WINNING strategies

**Source** : https://youtu.be/W722Ca8tS7g · Unbiased Trading · 689 s (~11 min) · Auto-captions EN
**Date extraction** : 2026-04-24

## 1. Thèse centrale

4 techniques de backtesting systématiques empruntées aux quant funds (Renaissance, Susquehanna référencés) qui **séparent un vrai edge d'un artefact statistique** : (1) Parameter Sensitivity, (2) Walk-Forward Optimization, (3) Stress Testing, (4) Monte Carlo Simulations. Méta-message : 90% des retail backtests sont biaisés parce qu'ils sautent ces étapes. Pitch pour son "Backtest Bootcamp" payant à la fin.

## 2. Mécanisme complet

Ce n'est pas une stratégie, c'est une **méthodologie de validation** :

- **Technique 1 — Parameter Sensitivity** : pour chaque paramètre (RSI period, MA length, etc.) tester une plage (ex RSI 12/14/16/18) et exiger que **tous les paramètres voisins produisent des rendements similaires** (pas 22% / 50% / −10% / 5% → curve-fit ; plutôt 18% / 22% / 20% / 17%). Visualisation = heatmap 2D (deux paramètres), chercher un cluster doux et pas une pointe isolée.
- **Technique 2 — Walk-Forward Optimization** : split training (ex 1 an) + testing OOS (ex 0.5 an), rouler dans le temps. Le stratégie ne doit **jamais avoir vu les données OOS** avant de les trader. Acceptable que l'OOS soit un peu sous l'IS (ex IS 10-20% → OOS 6-8%), mais un flip (IS +20% / OOS −10%) = fail. 
- **Technique 3 — Stress Testing** : lancer la stratégie contre les worst-case scenarios : 2008, 2020, flash crashes. **Double commissions**, **triple slippage**, **add execution delays** (ex shift signal-to-execution de 0 à 5 min ou 1-5 jours). Si la stratégie s'effondre → pas robuste.
- **Technique 4 — Monte Carlo Simulations** : randomiser l'ordre des trades historiques des milliers de fois. Visualise "spaghetti d'equity curves" montrant le vrai range de risque. Mesure **survivability** : psychologiquement + sizing, l'account peut-il survivre au worst-case ? Si non, réduire la taille.

## 3. Règles fermées (codables telles quelles)

- Parameter sensitivity : pour chaque param `p`, tester `p ± k*step` sur ≥3 valeurs, calculer rendement par cellule, rejeter si écart-type des rendements voisins >> ampleur moyenne (curve-fit signal)
- Walk-forward : split sliding window, OOS perf ≥ 50% IS perf (threshold souple, verbatim = "should be in a similar sort of range")
- Stress : × 2 commissions, × 3 slippage, signal delay 1-5 bars ou 1-5 jours → strat must still show positive E[R]
- Monte Carlo : N=1000-10000 shuffles des trades, calcul 5e percentile equity, vérifier survivability à la position sizing cible

## 4. Règles floues / discrétionnaires

- "Similar sort of range" entre paramètres voisins : combien de %age de variation autorisée ? L'auteur dit "doesn't have to be exact same value" mais sans borne chiffrée.
- Training/test ratio walk-forward : ex 1/0.5 mais "doesn't always have to be this exact same rolling period" → floue.
- Monte Carlo : il ne précise pas si c'est **bootstrap** des trades, **random permutation de l'ordre**, ou **block bootstrap** (différences techniques importantes).
- Stress test amplitude (×2 commissions, ×3 slippage) : heuristiques pas dérivées d'un modèle de coût.

## 5. Conditions fertiles

- Stratégies mécaniques avec params clairement définis (MA period, RSI period, indicator thresholds) — les 4 techniques s'appliquent directement
- Futures / equities / crypto — l'auteur dit les avoir appliquées across markets ("futures, equities, and even crypto")

## 6. Conditions stériles

- Stratégies discrétionnaires non-formalisées (pas de params → pas de sensitivity)
- Peu de trades historiques (< 30) → Monte Carlo et sensitivity ne convergent pas statistiquement
- Optimisation sur full sample sans split : invalide dès le départ (c'est exactement ce que la vidéo dénonce)

## 7. Contradictions internes / red flags

- **Pitch commercial** fort ("Backtest Bootcamp" call-to-action 3 fois dans 11 min) — mais contenu technique solide en amont.
- La vidéo **ne mentionne PAS** : **permutation tests** (bar permutation type O5.3), **Combinatorial Purged Cross-Validation** (Lopez de Prado), **Deflated Sharpe Ratio**, **Probability of Backtest Overfitting** (PBO). Donc "behind WINNING strategies" = marketing — ces 4 techniques sont un **sous-ensemble** de ce qu'on devrait faire.
- Stress delay "signal to 5 minutes later" : l'auteur dit "if unprofitable après 5 min delay → bit worrying". Mais ignore que pour vraies stratégies mean-rev intraday, 5 min = changement de régime → sans info sur TF, le test est ambigu.
- Aucun exemple chiffré de ses propres backtests (juste un teaser "18% last month").

## 8. Croisement avec MASTER / QUANT / bot actuel

- **Révèle sur MASTER** : MASTER ne parle **jamais** de parameter sensitivity, walk-forward, stress, ni Monte Carlo. C'est un corpus **pédagogique-discrétionnaire**, donc **incompatible** avec les 4 techniques sans "mécanisation" préalable — ce qui est précisément ce qu'on fait avec §0.5/§0.5bis. Cette vidéo valide **a posteriori** notre pipeline §0.6 Stages.
- **Croisement QUANT** : QUANT corpus couvre **plus finement** que cette vidéo : QUANT a bar permutation, Monte Carlo shuffle, walk-forward, out-of-sample split, signal-to-noise, Sharpe deflation. La vidéo confirme 3/4 techniques déjà dans notre pipeline mais **ajoute stress-testing avec exec delays** comme primitive que QUANT n'avait pas explicitement formulée. Nouveau angle concret : **tester le bot avec delay 1-5 bars intraday** pour valider robustesse latency.
- **Implications pour le bot** :
  - Notre pipeline O5.3 gate actuel a **bar permutation 2000 iter** → couvre technique 1+4 partiellement. **OK.**
  - Notre Stages 1 (4w) → 2 (4w) → 3 (3 mois) = walk-forward rudimentaire mais **pas sliding window rolling**, juste 3 périodes séquentielles. À formaliser : est-ce qu'on veut un vrai WF rolling ?
  - **Gap identifié** : pas de **stress test explicite avec double slippage / triple commissions / execution delay 1-5 bars**. Avec G1-G3 (ConservativeFillModel + LatencyModel + spread bps) câblés, on a maintenant les briques pour stress-tester. **À transformer en gate §0.7 potentiel** après G4 : "stress = E[R] reste > 0.05R avec ×2 spread et ×3 latence".
  - **Gap identifié** : **Monte Carlo shuffle** des trades de calib_corpus_v1 n'est pas run. Pourrait complémenter O5.3. Budget slippage -0.097R/trade déjà connu, mais distribution de MaxDD intraday sous shuffle inconnu.
  - **Parameter sensitivity heatmap** : nos backlog §0.5bis tests (Aplus_01 TRUE HTF, Jegadeesh-Titman) devraient inclure un sweep systématique des seuils principaux pour éviter de tomber dans un sweet spot isolé (ex swing_n, FF threshold, momentum lookback).

## 9. Codability (4Q + 1Q classification)

- **Q1 Briques moteur existent ?** OUI partiel. Bar permutation existe (O5.3). WF partiel (Stages). Stress testing **non-implémenté** comme gate automatique (mais FillModel + LatencyModel câblés → briques prêtes). Monte Carlo shuffle **non-implémenté** (scripts `stat_arb_smoke.py` et autres ne shufflent pas les trades, juste rejouent bars).
- **Q2 Corpus disponible ?** OUI — tous nos corpus de trades (parquets, calib_corpus_v1, survivor_v1) sont shuffleables trivialement.
- **Q3 Kill rules falsifiables possibles ?** OUI : sensitivity → si écart-type voisins > mean, fail. Stress → si ×2 cost retire E[R] > 0.05R threshold, fail. Monte Carlo → si 5e percentile equity < −30% DD avec sizing cible, fail.
- **Q4 Gate §20 Cas attendu** : sans objet (méthodologie, pas playbook).
- **Q5 Classification** : **méthodologie** pure.

## 10. Valeur pour le bot

**Apport immédiat, actionnable** : ajouter à gate §0.7 une **item G5 "Stress + Monte Carlo gate"** qui runne sur tout candidat §0.5bis avant Stage 2 PASS : (a) re-run avec `ConservativeFillModel(extra=0.1%, spread_bps=2)` (doublé vs G3 default 0.05%/1bp) → E[R]_stress doit rester > 0.05R, (b) Monte Carlo shuffle N=5000 trades → 5th percentile equity > −30% relative DD. Ces 2 briques sont **gratuits à implémenter** vu que G1-G3 sont livrés. **Recommandation concrete** : intégrer après G4 (verdict templating), comme G5 optionnel mais standard pour §0.5bis entrées à partir de #2 Jegadeesh-Titman. La vidéo elle-même n'apporte rien de neuf vs QUANT sur le fond, mais elle **synthétise 4 tests en checklist** que notre `HARNESS_AUDIT` ou un README méthodologique peut répliquer.

## 11. Citation-clés

> "Performance really shouldn't spike for just one magical number. A robust strategy though would look like RSI 12 is plus 18%, RSI 14 is maybe 22%, RSI 16 is 20%, and RSI 18 is 17%. [...] If your strategy only works with one exact setting, it's not an edge, it's most likely a lucky accident in historical data."

> "Most traders though optimize over all their data and then they're surprised why it fails live. And it's basically that your strategy has memorized the test answers and doesn't actually understand the subject itself."

> "You can actually just add things to your backtest. For example, you could double your commissions. Very easy to do on a backtest and just see if the strategy survives. You could triple your slippage [...] adding execution delays, not every code or platform supports this but sometimes you can do it using a bit of code."
