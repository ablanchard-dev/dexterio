# 7dTQA0t8SH0 — Path to Profitability: SMT Divergence Explained

**Source** : https://youtu.be/7dTQA0t8SH0 · TJR · 16m06s · auto-generated captions (en)
**Date extraction** : 2026-04-24

## 1. Thèse centrale
SMT (Smart Money Divergence) = **divergence entre S&P 500 (ES) et NASDAQ (NQ)** sur highs ou lows formés **au même moment** tout en sweepant un draw de liquidité HTF — un fait un HH tandis que l'autre fait un LH (ou inverse en low) = signal précoce de changement de direction, utilisé pour savoir **sur quel instrument entrer** (the leading index).

## 2. Mécanisme complet
- **HTF bias** : déterminé par les draws de liquidité HTF (swing H/L significatifs sur daily/4H/1H).
- **Setup TF** : tout TF ; TJR montre sur 4H pour bias et 5min pour exécution.
- **Entry trigger** : au moment où un sweep de draw HTF se produit SIMULTANÉMENT sur les 2 indexes, on compare :
  - Bearish SMT : S&P fait un LH (ou flat-high), NQ fait un HH au sweep → les deux sont bearish, mais **entry sur l'index qui fait le LH** (le leading bearish).
  - Bullish SMT : un index fait un HL, l'autre fait un LL → entry sur l'index qui fait le HL (leading bullish).
- **Stop loss** : NON-SPÉCIFIÉ explicitement (implicite : au-dessus/sous le swing sweepé).
- **Take profit** : draws de liquidité vers lesquels le prix veut retourner — pas fixed RR.
- **Exit logic** : NON-SPÉCIFIÉ.
- **Sizing** : NON-SPÉCIFIÉ.

## 3. Règles fermées (codables telles quelles)
- SMT nécessite **2 instruments corrélés** (ES/NQ explicitement ; extensible à autres paires corrélées).
- SMT bearish valide uniquement si : **both indexes sweep a HTF high simultaneously** AND one makes HH while the other makes LH (or equal high).
- SMT bullish valide uniquement si : both indexes sweep a HTF low AND one makes HL while the other makes LL.
- **"At a significant draw on liquidity"** = obligatoire. Hors de ce contexte "it will show up all the time and will be pretty much useless to us."
- Trade sur **leading index** (celui qui a fait le LH en bearish / HL en bullish).
- Les 2 highs/lows doivent être formés "at the same time" (bougies alignées temporellement).

## 4. Règles floues / discrétionnaires
- "Significant draw on liquidity" = non codifié (swing age ? lookback ? volume ?).
- "At the same time" = combien de bars de tolérance ? Pas précisé.
- Définition exacte de HH vs LH en low-TF (sensibilité swing detector).
- Extension à d'autres paires (GC/SI ? DJI/ES ? NFLX/META ?) = non abordée.

## 5. Conditions fertiles
- Précisément : **HTF draws of liquidity swept**. Daily / 4H highs-lows.
- Marchés US cash session (implicite, vu les exemples 9:30).
- Bull et bear SMT : les deux documentés.

## 6. Conditions stériles
- **Hors HTF liquidity sweep → inutile** (TJR l'affirme explicitement).
- Forex / commodités : TJR dit que les 2 paires corrélées doivent exister ; "pour les Forex people ce n'est pas utile" (contexte ES/NQ seulement).
- Pas de stat sur fréquence des vrais SMT divergences / semaine.

## 7. Contradictions internes / red flags
- "I have no fucking clue what SMT divergence stands for" → admet ne pas savoir la définition acronymique, ce qui trahit un emprunt ICT sans fondation théorique.
- Aucun win-rate, aucun R:R moyen, aucune stat.
- Exemple 5min "you guys uh the price action isn't that good to the left-hand side" → reconnaît que l'exemple n'est pas propre.
- "I think it just means the difference" → définition approximative.

## 8. Croisement avec MASTER (contexte bot actuel)
- **Confirmé** : MASTER mentionne SMT divergence comme concept ICT classique.
- **Nuancé/précisé** : TJR précise la **condition obligatoire "at HTF liquidity draw"** — sans ça, SMT est bruit pur. Beaucoup d'implems SMT surface-level ratent cette condition.
- **Contredit** : rien de direct.
- **Nouveau relatif à MASTER** : la règle **trade the leading index** (celui qui fait LH en bearish) est une précision actionnable ; MASTER peut mentionner SMT sans dire sur quel instrument entrer.

## 9. Codability (4Q + 1Q)
- Q1 Briques moteur existent ? **NON directement**. Le bot a accès à SPY/QQQ/DIA data mais pas de brique `detect_smt_divergence` ni de cross-instrument swing comparator. Il faudrait :
  - Un swing detector commun sur les 2 symbols alignés par timestamp.
  - Un détecteur de HTF liquidity sweep sur chacun.
  - Un comparator qui flag "at sweep time, sym A = HH and sym B = LH".
- Q2 Corpus disponible ? **OUI pour SPY/QQQ** (5m et HTF dans calib_corpus_v1).
- Q3 Kill rules falsifiables ? OUI (E[R] > 0.05R, n ≥ 20 attend car signal probablement rare).
- Q4 Gate §20 Cas attendu ? **B (signal structurellement rare)** fortement probable — SMT divergences au sweep HTF sont event-scarce (peut-être < 5 / semaine). Cas C possible si le signal sans timing n'a pas d'edge.
- Q5 Classification : **confluence / filtre** principalement ; pourrait fonder un playbook "SMT_Sweep_Reversal" mais densité incertaine.

## 10. Valeur pour le bot
- **Idée neuve actionnable** : playbook candidat "**SPY_QQQ_SMT_Sweep_Reversal**" :
  - Détecter HTF liquidity draw (H1/H4 swing H/L).
  - Détecter sweep simultané sur SPY et QQQ (time-aligned).
  - Confirmer SMT (un fait HH/LH, l'autre inverse).
  - Entry sur le **leading index** (celui qui a fait le LH/HL).
- **Attention** : le bot a **10 data points négatifs** en intraday SPY/QQQ, dont Stat_Arb_SPY_QQQ_v1/v2 (pair mean-rev). SMT est un angle différent (reversal discrétionnaire vs mean-rev statistique) mais risque similaire de Cas B (rareté) ou Cas C (signal existe mais pas d'edge fixed-TP intraday).
- **Valeur réelle** : moyenne-forte — c'est la **seule nouvelle brique cross-instrument concrète** dans le corpus ICT qu'on peut coder sans infra massive. Mérite un smoke 1-semaine si priorisé.
- **Risque** : le fair-value gap de Leg 4.1/4.2 a montré que le signal SPY-QQQ 5m intraday n'est pas statistiquement robuste ; SMT est directionnel et contextualisé différemment, mais le marché 2025 a peut-être épuisé les divergences exploitables.

## 11. Citations-clés
- [line 310-314] *"These things will show up all the time and will be pretty much useless to us... SMT divergences are very powerful when used when sweeping out draws and liquidity."* → condition **obligatoire** HTF sweep.
- [line 262-272] *"I'm going to want to take a trade on the S&P 500. Why? Because it's the leading index. It's the index that is already more bearish."* → règle trade-the-leading-index.
- [line 32-36] *"I have no fucking clue what SMT divergence stands for. Smart money transfer divergence. I don't know. I don't care."* → red flag : concept emprunté sans fondation rigoureuse.
