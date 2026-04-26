# 03_BRAIN_TRUTH — Synthèse 3-corpus (MASTER × TRUE × QUANT)

**Date** : 2026-04-24
**Corpus sources** :
- `MASTER_FINAL.txt` (71 transcripts ICT/TJR smart money) — vérité doctrinale ICT
- `videos/true/TRUE_FINAL.txt` (20 transcripts word-for-word) — validation + extension TRUE, fiches Phase I dans `true_extraction/`
- `videos/quant/QUANT_FINAL.txt` (20 transcripts, ~10 352 lignes) + `QUANT_SYNTHESIS.md` (lecture complète) — méthodologie, features, validation statistique

**Objectif** : canon de vérité pour piloter les prochains playbooks et amendements plan v3.1.2. Identifier ce que QUANT **confirme** de notre pipeline, ce qu'il **ajoute** que le bot n'exploite pas, et les convergences/divergences avec MASTER+TRUE.

---

## 1. Résumé exécutif

- **QUANT confirme à 95 % notre pipeline de validation § 0.6 Stages 1→4** : bar permutation test, walk-forward multi-fold, reconcile slippage/fees — tous présents dans la framework de Timothy Masters (vidéo NLBXgSmRBgU). Seul manque explicite = **Monte Carlo shuffle + stress × 2 fees / × 3 slippage** (candidat G5 déjà flaggé TRUE W722Ca8tS7g).
- **QUANT apporte 2 briques structurelles majeures non exploitées** : (a) `directional_change` ATR-adaptive multi-échelle k1/k3/k9 (EuFakzlBLOA) — déjà partiellement en place via `directional_change.py` (schema α'' tp_resolver) mais pas utilisé comme **feature de bias HTF** ; (b) Market Profile KDE + peak prominence (mNWPSFOVoYA) pour détection de niveaux S/R data-driven → candidat naturel pour upgrade `tp_logic: liquidity_draw`.
- **QUANT confirme le verdict anti-Fibonacci / anti-TP-géométrique** par trois sources indépendantes (ODHlC9YuowY harmonic, 6iFqjd5BOHw H&S, Lb5SPCTp4uY flags) : les TPs "textbook" (head-height, N×R fixe, Fibonacci ratios) sont structurellement sous-optimaux. Converge avec R.3 Aplus_03 + Option B Aplus_04 + α'' schema learnings.
- **QUANT confirme la thèse d'edge decay / arbitrage public** (2XQ3PsZActM : "slowly being arbitraged out of the market", P4u5drToePM : WF 2020 excellent → 2021 OK → 2022 flat). Nuance : les patterns data-mined **localement** gardent un edge marginal mesurable, juste décroissant — pas le "tout edge public mort" radical de TRUE fIEwVmJJ06s.
- **QUANT ne propose aucun playbook ICT ni dual-asset SMT** (aucune vidéo n'aborde SMT cross-index ni HTF bias 7-step), donc **ne contredit PAS ni ne valide** nos candidats TRUE SMT SPY/QQQ + Aplus_01 v2 TRUE HTF. QUANT et TRUE sont complémentaires, pas redondants.
- **QUANT apporte 4 signaux tradables non-testés non-ICT** : (1) Bull/Bear Flag trendline (Lb5SPCTp4uY, marche symétrique BTC — à tester SPY/QQQ), (2) Inverted H&S early ID (6iFqjd5BOHw, seul H&S robuste), (3) Pattern discovery K-means+PIP+MC (P4u5drToePM, méthode de research, pas playbook direct), (4) Metalabeling RF post-primary (jCBnbQ1PUkE, nécessite 500+ trades d'un playbook product-grade — **pas maintenant**).
- **QUANT confirme 0/20 vidéos traitent de cointegration, stat-arb, pairs trading classique, ou PCA residuals** (seule FF factors mentionnée). Implication directe : §0.5bis #3 Avellaneda-Lee PCA stat-arb **n'a aucun support QUANT** — confirme que le corpus QUANT est orienté **single-asset structure/patterns**, pas multi-asset stat-arb. Décision d'inclure #3 doit reposer sur littérature externe (Avellaneda 2010), pas QUANT.

---

## 2. Pipeline de validation (QUANT × DexterioBOT actuel)

### 2.1 Éléments CONFIRMÉS

| Stage DexterioBOT | QUANT équivalent | Source | Verdict |
|---|---|---|---|
| Stage 1 (4w cross-regime, E[R]>0.05R, n≥15, peak_R p60>0.5R) | Walk-forward test sur real data (Masters Step 2) | NLBXgSmRBgU | ✓ Aligné |
| Stage 2 (TP amplify, E[R]_net>0.10R, PF>1.2) | WF + cost modeling | NLBXgSmRBgU, 9Y3yaoi9rUQ | ✓ Aligné |
| Stage 3 O5.3 bar permutation 2000 iter | Masters Step 1 (in-sample) + Step 3 (WF permutation) | NLBXgSmRBgU, P4u5drToePM, 2XQ3PsZActM | ✓ Aligné (seuils plan p<0.05 cohérents avec Masters p<0.01 IS / p<0.05 WF) |
| Stage 3 Sharpe > 1 + Martin > 1 | Sharpe ratio + Martin ratio (Ulcer) | 9HD6xo2iO1g, P4u5drToePM | ✓ Aligné (Sharpe > 1 "bon", > 2 "rare", > 3 "suspect") |
| Stage 4 paper 8 semaines | Non couvert explicitement (implicite pré-live) | — | ✓ Neutre |
| Reconcile G3 slippage -0.097R/trade | "50 % perf brute typiquement érodée par coûts" | NLBXgSmRBgU | ✓ Aligné en ordre de grandeur |
| §19.3 kill rules (≤ 3 itérations max) | Non explicite (QUANT n'a pas de dossier max-iteration) | — | ✓ Neutre |

**Verdict global** : la méthodologie de validation DexterioBOT est **substantiellement conforme** au framework Masters tel que présenté par Neurotrader. Les 4 steps Masters (IS permutation, WF, WF permutation, realistic costs) sont tous présents.

### 2.2 Éléments MANQUANTS (gaps à combler)

| Gap | Source QUANT | Source TRUE convergente | Implication plan |
|---|---|---|---|
| **Monte Carlo shuffle des trades** pour distribution DD / survivability | (implicite via permutation tests) | W722Ca8tS7g | Candidat G5 post-G4 |
| **Stress × 2 costs / × 3 slippage / 1-5 bars delay** automatique | 9Y3yaoi9rUQ (cost modeling, pas × 2/× 3 explicite), reconcile DexterioBOT déjà partiel | W722Ca8tS7g (4/4 techniques) | G5 post-G4 |
| **Pattern discovery workflow** (K-means + PIP + MC + WF) sur corpus SPY/QQQ 5m propre | P4u5drToePM | — | Après G5, workflow recherche non-doctrinale (option F6 §0.3 point 3) |
| **Runs test** / trade dependence check | BM3KZPg6zic | — | Feature risk_engine (post-promotion premier playbook product-grade) |
| **Metalabeling gate RF** post-primary | jCBnbQ1PUkE | — | **Pas maintenant** (pré-requis : playbook avec ≥ 500 trades validés) |

### 2.3 Éléments MAL IMPLÉMENTÉS

| Élément DexterioBOT | Problème | Correction QUANT | Source |
|---|---|---|---|
| HTF bias = SMA_5 proxy D/4H (Phase D.1 : 0/171 rejections, universal nul) | Proxy pauvre, ne reflète pas structure | Remplacer par `structure_k9 direction` (directional change hiérarchique) | EuFakzlBLOA |
| `tp_logic: liquidity_draw (swing_k3)` (schema α'') — 73 % fallback Aplus_03_v2 | Pools swing 5m/15m trop proches, sous-calibrés | Upgrade vers KDE+prominence Market Profile (pools data-driven) + `pool_tf=["4h","1h"]` (TRUE pKIo-aVic-c) | mNWPSFOVoYA + TRUE pKIo-aVic-c |
| Trailing stop "quasi inactif" (B1 review : 75p R=+0.11, trigger 0.8-1.0R) | Trigger statique non-adaptatif | Hawks process self-exciting vol → exit sur death of volatility | wdsiZBIhAFw |
| Volatility estimator intraday actuel = ATR seul | ATR oublie variance intra-bougie | Garman-Klass `log(H/L)² / 2 − (2·log(2)−1) × log(C/O)²` | 9Y3yaoi9rUQ |
| Bar permutation Stage 3 : 2000 iter unique sur full period | Masters impose IS (step 1) **ET** WF (step 3) séparément | Deux passes distinctes, seuils différents (p<0.01 IS / p<0.05 WF) | NLBXgSmRBgU |

---

## 3. Signaux tradables QUANT non-testés

Les 20 vidéos QUANT proposent des signaux **majoritairement single-asset, structure/pattern-based**, pas dual-asset / stat-arb / options. Sélection rankée ROI/complexité :

### 3.1 Bull/Bear Flag trendline v2 — ★★★
**Source** : `Lb5SPCTp4uY`. **Verdict** : marche symétriquement sur BTC hourly 2018-2022, win rate > 50 % consistent sur presque tous ordres testés. **Mécanique** : pole = move ≥ X ATR dans N bougies → flag = retracement ≤ 50 % range + durée ≤ 50 % pole_width → entry breakout trendline upper (bull) / lower (bear) → exit hold flag_width bougies OU liquidity pool.

**Pourquoi non-testé** : `Trend_Continuation_FVG_Retest` DENYLIST (-22R) était probablement **sur-contraint** (exigeait FVG en plus). Un flag simple pourrait fonctionner. **Infra requise** : détecteur 150-300 lignes + trendline fit (vidéo wbFoefnidTU, 100-500 ms/candle). **Budget** : 2-3 j dev.

### 3.2 Inverted H&S early ID — ★★
**Source** : `6iFqjd5BOHw`. **Verdict** : seule config H&S qui marche consistent sur BTC hourly (profit factor > 1 sur presque tous ordres). **Mécanique** : détection 5 pivots rolling-window → entry **anticipée** sous midpoint right shoulder / right armpit → exit hold = head width OU liquidity.

**Pourquoi non-testé** : pattern jamais rebuildé dans DexterioBOT. **Attention edge decay** : BTC ≠ SPY/QQQ, asymétrie "bottoming pattern" BTC spécifique. **Budget** : 2 j dev + validation permutation avant promo.

### 3.3 Pattern discovery K-means + PIP + MC + WF — ★★★ (méthode, pas playbook)
**Source** : `P4u5drToePM`. **Verdict méthode** : pipeline complet de **research non-doctrinale** pour découvrir patterns novels sur SPY/QQQ 5m. Sort naturellement du cadre ICT / MASTER. WF 2018-2019 → 2020 excellent, décroît 2021+.

**Pourquoi intéressant** : DexterioBOT est 100 % doctrine-driven (ICT MASTER). Si hypothèse B "ICT arbitré" (TRUE fIEwVmJJ06s) se renforce → option F6 du §0.3 point 3 = **pivot data-mining**. QUANT fournit le pipeline réplicable. **Budget** : 3-5 j (K-means + PIP + silhouette + Martin ratio + MC test + WF).

### 3.4 Metalabeling RF post-primary — ★★ (pré-requis bloquant)
**Source** : `jCBnbQ1PUkE` (López de Prado). **Verdict** : Sharpe 0.8 → 1.5 en uplift sur primary trend-following BTC. **Pré-requis strict** : ≥ 500 trades d'un playbook stable.

**Pourquoi non-applicable maintenant** : aucun playbook DexterioBOT n'a atteint 500 trades validés. `calib_corpus_v1` = 170 trades, trop petit. **Anti-pattern explicite** (vidéo) : metalabeling ne crée pas d'edge, il raffine précision → inutile sur E[R]<0. À rouvrir **après** premier playbook product-grade Stage 3 PASS.

### 3.5 Garman-Klass intraday vol + GARCH prediction premium — ★★ (features, pas playbook)
**Source** : `9Y3yaoi9rUQ` (freeCodeCamp Project 3). **Features direct drop-in** dans `MarketFeatures` : `gk_vol` (10 lignes), `atr_prediction_premium` via GARCH(1,3) rolling 6 mois. **ROI** : améliore tous les détecteurs qui dépendent de la volatilité, filter régime avancé.

**Budget** : Garman-Klass = 1 h. GARCH = 1 j (dépendance `arch` package).

### 3.6 Signaux NON proposés par QUANT (gaps corpus)

- **Cross-sectional momentum (Jegadeesh-Titman)** : **aucune vidéo QUANT** ne teste J&T. Le plus proche = FF factors freeCodeCamp. **Confirme §0.5bis #2 ne s'appuie PAS sur QUANT** mais sur littérature externe 1993 (décote académique TRUE fIEwVmJJ06s s'applique).
- **Avellaneda-Lee PCA stat-arb** : **aucune vidéo QUANT**. Zéro support interne repo. §0.5bis #3 repose entièrement sur Avellaneda 2010 paper externe.
- **Microstructure / order book imbalance / tick data** : **aucune vidéo QUANT** (granularité minimale = 5m hourly). Gap pour hypothèse "non-public features" §0.3 point 3 option F7.
- **Options Forward-Factor calendar** : **aucune vidéo QUANT** couvre options. TRUE `6ao3uXE5KhU` seule source → plan B longtemps-terme non supporté par QUANT.

---

## 4. Méta-méthodologie : edge decay / overfitting / public vs private

### 4.1 Convergence 3 corpus sur "edge decays in time"

| Source | Affirmation |
|---|---|
| TRUE `fIEwVmJJ06s` (Ivy League Quant) | "tout edge public est mort, papers académiques -25 % post-pub" — **bombe méta radicale** |
| TRUE `s9HV_jyeUDk` (IRONCLAD) | 8700 combos Forex ICT : 4/5 gurus perdent 70-86 %, OB/PD dégradent — **confirme ICT public arbitré** |
| QUANT `P4u5drToePM` (data mining PIP) | WF 2018-2019 → 2020 excellent, 2021 OK, **2022 flat** — edge décroît monotoniquement |
| QUANT `2XQ3PsZActM` (GA candlestick) | "what little edge these patterns have are **slowly being arbitraged out of the market**" |
| QUANT `ODHlC9YuowY` (Harmonic XABCD) | Marginal + erratic. Shark seul robust. **Fibonacci ratios n'ont pas d'edge exact** |
| MASTER (ICT doctrine publique depuis ~2016) | Aucune auto-critique. Pas de méta-awareness d'arbitrage public |

**Convergence** : **2/3 corpus (TRUE + QUANT) affirment explicitement edge decay sur patterns/strategies publics testés**. MASTER est silencieux (ce qui en soi supporte la critique).

**Nuance** : QUANT dit "**slowly arbitraged**, edge mesurable mais décroissant" — **plus nuancé** que TRUE fIEwVmJJ06s "edge public = mort". Les deux visions ne sont pas incompatibles : public ≠ zéro edge, mais edge décroissant au point d'être non-actionnable à terme. **Implication** : décote pré-probabilité (−25 % à −35 %) semble **raisonnable**, pas rejet automatique.

### 4.2 Overfitting / data snooping : consensus fort

- **Masters framework** (NLBXgSmRBgU) : bar permutation test **PRÉCÈDE** toute décision de promotion. Implicite : sans ce test, tout backtest peut être du hasard.
- **Selection bias** (NLBXgSmRBgU timeline 449-476) : "ran 100 strategies, picked best" = selection bias massif. DexterioBOT a testé ~26 playbooks — selection bias réel, d'où l'importance de réserver permutation test Stage 3.
- **K-means instable** (P4u5drToePM) : clustering NP-hard, résultats varient par random seed. Implication méthodologique : tout run de research non-doctrinale nécessite plusieurs seeds + stability check.
- **GA overfit guard** (2XQ3PsZActM) : seuils `min_occurrences` dans l'implémentation pour éviter overfit. Anti-pattern explicite pour DexterioBOT : ne pas faire GA sur params Morning_Trap sans permutation test.

### 4.3 Verdict méta cross-corpus

**L'hypothèse "edge public arbitré" est supportée par 2/3 corpus avec nuance**. Le chemin rationnel plan v3.1.2 reste valide : tester hypothèse A (MASTER mal implémenté → Aplus_01 v2 TRUE HTF + SMT) **avec** décote académique sur #2 (J&T) et #3 (Avellaneda) — pas rejet préventif.

**Anti-pattern consolidé** : déployer live un backtest sans passer **Masters 4-step + Monte Carlo shuffle + stress** = manque de due diligence standard.

---

## 5. Canon de vérité 3-corpus

Pour chaque concept majeur, **la version la plus précise/rigoureuse trouvée** (colonne "Canon"). Les cases "—" signifient que le corpus ne parle pas du concept.

| Concept | MASTER | TRUE | QUANT | Canon (meilleure source) |
|---|---|---|---|---|
| HTF bias (multi-tf) | Doctrinal D/4H structural | 7-step (ironJFzNBic) : structure + cycle position + FVG respect + draws ranked + PM manipulation + close-flip + SMT | `structure_k9` direction (EuFakzlBLOA) | **TRUE 7-step** (doctrinal complet) **+ QUANT structure_k9 comme implémentation rigoureuse non subjective** |
| SMT cross-index | Mentions disparates | FJch02ucIO8 + 7dTQA0t8SH0 explicites (leading break / lagging continue) | — | **TRUE** (QUANT silencieux, MASTER diffus) |
| Equilibrium (EQ) | Brick continuation | joe_XTCn5Bs + wzq2AMsoJKY formalisation 4/4 swings | — | **TRUE wzq2AMsoJKY** |
| Fresh liquidity pool | Doctrinal ("untouched") | pKIo-aVic-c : freshness filter + reaction + stack density | mNWPSFOVoYA (KDE peak prominence, data-driven) | **Hybride** : sémantique TRUE + implémentation QUANT (KDE) |
| TP structurel (vs fixed RR) | Doctrinal "next pool" | pKIo-aVic-c + FJch02ucIO8 (SMT completion) | mNWPSFOVoYA (next S/R KDE) + ODHlC9YuowY (harmonic TP au pivot) | **TRUE sémantique + QUANT détection** |
| Pivot / structure detection | Subjectif (swings) | — | X31hyMhB-3s (3 algos) + EuFakzlBLOA (hiérarchique) | **QUANT EuFakzlBLOA** (rigoureux, non subjectif) |
| Bar permutation test | — | W722Ca8tS7g (mention 4/4 techniques) | NLBXgSmRBgU (Masters framework complet, 4 steps) | **QUANT NLBXgSmRBgU** |
| Monte Carlo / stress test | — | W722Ca8tS7g (× 2 fees / × 3 slippage + MC shuffle) | P4u5drToePM (MC permutation sur pipeline), 2XQ3PsZActM (MC GA) | **TRUE W722Ca8tS7g** (formulation opérationnelle DexterioBOT) |
| Walk-forward | — | — (silent) | NLBXgSmRBgU (train 2y test 1y step 1y) + 9Y3yaoi9rUQ (rolling OLS) | **QUANT NLBXgSmRBgU** |
| Sharpe / Martin promotion metric | — | — | 9HD6xo2iO1g + P4u5drToePM | **QUANT** |
| Edge decay / public arbitrage | — (silencieux, doctrine stable) | fIEwVmJJ06s ("tout public = mort") | 2XQ3PsZActM ("slowly arbitraged"), P4u5drToePM (WF 2022 flat) | **TRUE radical + QUANT nuancé = décote modérée -25 % à -35 %** |
| Garman-Klass volatility | — | — | 9Y3yaoi9rUQ (formule intraday) | **QUANT** |
| Stat-arb / cointegration | — | — | — (aucun) | **Aucun** — repose sur Avellaneda 2010 externe |
| Metalabeling ML | — | — | jCBnbQ1PUkE (López de Prado) | **QUANT** (mais pré-requis 500+ trades non-atteint) |

**Lecture** : TRUE et QUANT sont **complémentaires** — TRUE couvre la sémantique trading ICT + méta-méthodologie ; QUANT couvre la rigueur statistique + briques structure + features non-ICT. MASTER est principalement **source doctrinale** et rarement la meilleure source opérationnelle seule.

---

## 6. Implications pour le plan v3.1.2

### 6.1 §0.7 gates à ajouter

**G5 candidat confirmé par QUANT + TRUE convergent** : Stress + Monte Carlo gate.
- **Stress** : × 2 commissions, × 3 slippage, 1-5 bars delay sur candidat Stage 2/3 → E[R]_net doit rester > 0.
- **Monte Carlo shuffle** : 1000 shuffle des trades → distribution DD, survivability > 80 % (pas de ruin path).
- **Source** : TRUE W722Ca8tS7g (formulation opérationnelle) + QUANT P4u5drToePM/2XQ3PsZActM (MC permutation sur pipeline).
- **Positionnement** : post-G4 (verdict templating), parallèle possible.

### 6.2 §0.5bis backlog amendements

**AMEND #1 Aplus_01 Family A v2 TRUE HTF** — *élargir scope* :
- Bias HTF 7-step (TRUE ironJFzNBic) implémenté via **`structure_k9` direction** (QUANT EuFakzlBLOA) au lieu de SMA proxy
- EQ brick (TRUE wzq2AMsoJKY) comme alternative FVG continuation
- Time-gate (TRUE L4xz2o23aPQ) : NY open manipulation 9:30-9:50 → macro 9:50-10:10 → cut-off 10:30
- TPs structurels via KDE peak prominence (QUANT mNWPSFOVoYA) + freshness filter (TRUE pKIo-aVic-c)

**NEW #1.5 SMT Divergence SPY/QQQ v1** — *insertion avant #1* (TRUE convergence 3 sources, QUANT silencieux) :
- Budget infra plus léger (briques 50 % en place : pivots k3, PairSpreadTracker D1+D2, liquidity pools tp_resolver)
- Dual-asset vs single-asset → **structurellement novel** par rapport aux 26 playbooks DexterioBOT
- QUANT ne confirme ni n'infirme → décote à appliquer = **aucune** (pas académique public)

**AMEND #2 Jegadeesh-Titman cross-sectional momentum** — *décote académique* :
- QUANT silencieux sur J&T. Publication 1993 = 33 ans public = **edge decay très probable**
- Décote -25 % à -35 % ou exiger résultats ≥ gate × 1.5 (TRUE fIEwVmJJ06s hypothèse + QUANT P4u5drToePM/2XQ3PsZActM empirique)
- Reconsidérer priorité (baisser dans backlog)

**AMEND #3 Avellaneda-Lee PCA stat-arb** — *décote académique + gap QUANT* :
- QUANT **aucun support interne** (0/20 vidéos couvrent PCA / stat-arb / pairs)
- Publication 2010 = 16 ans public. Décote similaire -25 % à -35 %
- Cohérent avec SMOKE_FAIL stat_arb_v1 + v2 byte-identical (9e data point négatif cross-playbook) — hypothèse "stat-arb simple arbitré" fortement supportée
- **Recommendation** : descendre priorité, pas supprimer

**NEW #5 Bull/Bear Flag trendline v2 SPY/QQQ 5m** — *candidat QUANT fort* :
- QUANT Lb5SPCTp4uY symétrique (bull+bear) profitable sur BTC → tester SPY/QQQ
- Budget 2-3 j dev, non-doctrinal (sort du MASTER ICT)
- **Potentielle entrée F6 §0.3 point 3** si backlog ICT + TRUE échoue

**NEW #6 Options Forward-Factor calendar** — *pivot Plan B long-terme* :
- TRUE 6ao3uXE5KhU seule source (27 % CAGR / 2.4 Sharpe / 19 ans)
- QUANT silencieux sur options → pas de validation indépendante corpus
- **Infra absente** (pas de chain, Greeks, expiry manager) → budget lourd
- Candidat **F7 §0.3 point 3** si tous backlogs ICT + non-ICT single-asset échouent

### 6.3 Hypothèses A "MASTER mal codé" vs B "MASTER arbitré"

**QUANT apporte information nuancée** :
- QUANT ne dit rien directement sur ICT → ne tranche pas A vs B spécifiquement
- QUANT confirme empiriquement **edge decay public** (P4u5drToePM, 2XQ3PsZActM) → supporte la **forme atténuée** de B ("edge décroissant", pas "mort")
- QUANT fournit outils méthodologiques rigoureux (permutation, GK vol, structure_k9) permettant de **départager A de B empiriquement** : si Aplus_01 v2 TRUE HTF enrichi + SMT passent Masters permutation test + Sharpe > 1, alors A est validé localement ; si échec avec méthodologie rigoureuse → B renforcé.
- **Décision rationnelle inchangée** : tester 1-2 candidats A (SMT + Aplus_01 v2 TRUE HTF enrichi) avec **gate Masters + G5 stress+MC**, puis décider.

### 6.4 MarketFeatures priorités (Bloc B hooks QUANT)

Ordre d'implémentation proposé (repris de `QUANT_SYNTHESIS.md` §3.2, validé) :
1. `structure_k1`, `structure_k3`, `structure_k9` — **débloque HTF bias rigoureux + tp_logic: next_pivot_k9**
2. `sr_levels_top_N` (KDE + prominence) — **débloque tp_logic: liquidity_draw data-driven**
3. `gk_vol` (Garman-Klass) — 10 lignes, universel
4. `vsa_residual` (volume/spread régression rolling) — filter entrée sweep
5. `perm_entropy_D3` — filter régime MR/reversal
6. `intramarket_diff_spy_qqq` — confirmation HTF bias dual-asset

**Skippés** : RAI, ASPL, trend line slopes, harmonic, H&S, GA candlestick (ROI trop bas ou edge marginal documenté).

---

## 7. Prochaines étapes (vers Phase IV Code Audit)

1. **Phase IV — `04_CODE_AUDIT.md`** : matrix par playbook ALLOWLIST + DENYLIST + ARCHIVED × concepts BRAIN_TRUTH (HTF bias 7-step, SMT, EQ, fresh-pool, permutation validation, GK vol, structure_k9). Objectif : identifier pour chaque playbook **quels concepts sont implémentés fidèlement vs absents vs mal implémentés**.
2. **Phase V — `05_PLAN_DECISION.md`** : KEEP / AMEND / PIVOT du plan v3.1.2 basé sur 01+02+03+04. Livrable d'escalade user.
3. **Pré-requis techniques attendus** : G4 verdict templating (§0.7 dernier gate pending) + G5 stress+MC (candidat G5). Ces deux gates conditionnent toute promotion Stage 3.

---

## Notes méthodologiques

- **Corpus lu** : `QUANT_SYNTHESIS.md` lu intégralement (662 lignes, déjà synthèse détaillée des 20 transcripts par l'équipe). `QUANT_FINAL.txt` consulté par grep ciblé (edge decay, cointegration, MC, Fibonacci, cross-sectional) pour vérifier absences/présences clés. Temps lecture ≈ 25 min.
- **Non-invention** : chaque affirmation QUANT est ancrée sur un video_id identifié. Quand QUANT ne couvre pas un concept (stat-arb, options, microstructure, 1m ICT), la section le dit explicitement.
- **Cohérence avec plan v3.1.2** : amendements proposés sont **compatibles** avec §0.5bis backlog existant et §0.3 escalation framework. Aucune proposition ne contredit §0.7 gates pré-backlog (G1 DONE / G2 DONE / G3 DONE / G4 PENDING) ni §19.3 kill rules.

**Fin Phase III.** Passage Phase IV Code Audit.
