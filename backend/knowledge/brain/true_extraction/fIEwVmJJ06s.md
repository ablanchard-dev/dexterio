# fIEwVmJJ06s — "Build Your Own Trading Strategy" — Ivy League Quant

**Source** : https://youtu.be/fIEwVmJJ06s · DeltaTrend Trading · 439 s (~7 min) · Auto-captions EN
**Date extraction** : 2026-04-24

## 1. Thèse centrale

**Méta-thèse brutale** : tout edge public est par définition mort. Argument en 3 temps : (1) le trading de Morgan Stanley en 1987 sur pairs trading a rapporté $50M / an mais a **disparu dès que les traders sont partis fonder D.E. Shaw / Two Sigma** et que l'edge s'est publicisé ; (2) papers académiques qui "trouvent un edge" le perdent **~25% après publication** (statistical bias supplémentaire ~10% → restant mort) ; (3) les "gurus YouTube" (TJR, ICT) qui vendent leur stratégie ne peuvent pas avoir d'edge réel — si c'était vrai ils la garderaient sous NDA. **Solution** : construire sa stratégie from scratch (step 0 = data + features engineering) plutôt que d'apprendre d'un guru (step 2).

## 2. Mécanisme complet

Ce n'est pas une stratégie tradable, c'est une **méta-critique de l'information publique en trading**. Pipeline implicite esquissé en dernière minute :
- **Step 0** : obtaining data
- **Step 0→1** : pre-processing data
- **Step 1** : engineering features
- **Step 2** : discovering unique & novel relationships between features
- **Step 3** : properly testing (backtesting + OOS)
- **Step 4** : deploying
- **Step silence** : **jamais publier, ne jamais vendre**, NDA pour collaborateurs

Aucun TF / entry / exit / sizing — ce n'est pas une stratégie.

## 3. Règles fermées (codables telles quelles)

- Méta-règle 1 : `if strategy_is_public: expected_edge ≈ 0` (rejeter par défaut)
- Méta-règle 2 : `if author_sells_course: treat_as_unverified_until_independently_replicated`
- Méta-règle 3 : l'edge décline post-publication ≈ 25%, plus 10% bias academic → valeur résiduelle ~65% au mieux, souvent 0

## 4. Règles floues / discrétionnaires

- "Engineering features you notice that others don't notice" : comment, concrètement ?
- "Build from scratch" : quelle méthodologie de discovery ? Pas détaillée (la vidéo est courte, 7 min).
- Le promo final annonce une future série "from step 0 to step done" → la méthodo détaillée est ailleurs (pas dans cette vidéo).

## 5. Conditions fertiles

- Edge **privé** (NDA, code propriétaire protégé légalement)
- Secteurs à infrastructure élevée requise (HFT latency, private datasets)
- Edges non-scalables par big funds (capacity < threshold) MAIS découverts par retail avec effort

## 6. Conditions stériles

- Stratégies **apprises d'un guru YouTube** : "If you can find it published, it doesn't work. If somebody's selling it to you, it doesn't work. You have to build it yourself."
- Analyses naïves sans slippage / transaction costs / latency → créent faux edges qui disparaissent en réel
- "Obvious" strategies (pairs trading simple, classical MA cross) : arbed out par HFT

## 7. Contradictions internes / red flags

- **Paradoxe évident** : l'auteur lui-même publie une vidéo YouTube qui vante son futur "step 0 to step done" series. Il vend / promeut son propre contenu. Contradiction qu'il **ne résout pas** dans la vidéo.
- **Cherry-pick du case study Morgan Stanley 1987** : exemple ancien, beaucoup d'autres exemples d'edges qui ont survécu plusieurs décennies post-publication (value investing, momentum, low-vol anomaly, Jegadeesh-Titman 1993 qui marche encore in-sample après 30 ans d'études académiques).
- **Affirmation "25% decay post-publication"** : cite un "paper" mais sans titre complet / auteur / date → difficile à vérifier. La stat est probablement McLean & Pontiff 2016 ("Does Academic Research Destroy Stock Return Predictability?") qui trouve ~32-58% decay selon specs, pas 25% — cite-culture imprécise.
- **Argumentation ad hominem** sur TJR : possiblement correcte (TJR = scammer) mais logiquement ça ne démontre pas que **toutes** les stratégies publiées sont mortes.
- **Ignore** : il existe des stratégies publiques **robustes** (academic factor investing, trend-following CTA, momentum Jegadeesh-Titman) qui survivent 20-30+ ans post-publication parce que le "crowding" est absorbé par le flux / les contraintes de mandate / la douleur de draw-down.

## 8. Croisement avec MASTER / QUANT / bot actuel

- **Révèle sur MASTER** : **bombe méthodologique** pour DexterioBOT. Notre thèse bot = "MASTER (71 transcripts ICT YouTube) est exploitable". Cette vidéo dit textuellement : **"If ICT concepts don't work, then what does? Something proprietary. Nothing you're going to find online."** → **attaque frontale** de la thèse du bot. Nos 10 data points négatifs cross-playbook **confirment empiriquement** cette critique : ICT public → pas d'edge réalisable.
- **Croisement QUANT** : QUANT confirme cette méta-règle (edge decay post-publication est un thème récurrent du corpus quant). Rien de neuf sur le fond. Mais la vidéo formule le message **plus brutalement** que QUANT et l'applique explicitement à ICT/TJR.
- **Implications pour le bot (majeures)** :
  - **Si on accepte cette vidéo**, notre hypothèse "MASTER mal compris" (CLAUDE.md) est **partiellement fausse** : ce n'est pas que MASTER soit mal compris, c'est que **MASTER étant public, son edge est déjà arbitragé**. 10 data points négatifs = cohérent avec "edge mort" plutôt que "implémentation imparfaite".
  - Implication stratégique pour le plan v3.1.2 parsed-nibbling-kettle : les 4 entrées §0.5bis (Aplus_01 TRUE HTF, Jegadeesh-Titman pivot TF, Avellaneda-Lee PCA, Flags) → les 2 **académiques** (Jegadeesh-Titman 1993, Avellaneda-Lee 2010) sont **publiées** depuis 15-35 ans → **cette vidéo prédirait qu'elles sont mortes**. Cependant, QUANT corpus et observations empiriques du monde trend-following suggèrent le contraire (l'edge JT survit). **Tension à résoudre**.
  - **Solution pragmatique** : pour §0.5bis entrées académiques, ne pas accepter la conclusion "public = mort" aveuglément. Laisser les Stage 1 / Stage 2 / gate §20 trancher empiriquement sur notre corpus.
  - Pour §0.5bis **Aplus_01 TRUE HTF** (ICT-sourced) : la vidéo renforce notre prudence. Si encore un data point négatif (11e), accepter la méta-hypothèse de la vidéo et pivoter définitivement vers features non-publiques (microstructure, PCA residuals, ML sur notre propre feature engineering).
  - **Méta-prioritaire** : l'auteur promet une série "step 0 to step done". Si cette série existe et couvre feature engineering original, pre-processing, testing → **intéressant à suivre** pour enrichir notre pipeline (mais peut-être dans vidéos futures, pas dans ce corpus-ci).

## 9. Codability (4Q + 1Q classification)

- **Q1 Briques moteur existent ?** Sans objet (pas une stratégie).
- **Q2 Corpus disponible ?** Sans objet.
- **Q3 Kill rules falsifiables possibles ?** Oui comme **meta-gate** : "si X data points cross-playbook sur univers-public convergent négatif → accepter H0 = edge public mort → pivoter strictement privé". Seuil suggéré : **10 data points négatifs** — qu'on a déjà.
- **Q4 Gate §20 Cas attendu** : sans objet.
- **Q5 Classification** : **pédagogique / méta-méthodologique**.

## 10. Valeur pour le bot

**Apport stratégique de plus haut niveau du batch** — cette vidéo **n'est pas** une recette mais une **critique épistémologique** qui s'applique directement à notre situation (10 data points négatifs MASTER/ICT). Apport concret :

1. **Renforce la thèse post-escalade §0.3 point 3** : le plan v3.1.2 parsed-nibbling-kettle a correctement identifié que "nouvelles hypothèses fondamentales" sont requises (ML / data source / pivot). Cette vidéo donne le **cadre théorique** pour justifier pourquoi ICT public a échoué.

2. **Guide backlog §0.5bis** : prioriser les entrées **non-ICT académiques** (Jegadeesh-Titman, Avellaneda-Lee) **avec humilité** (peuvent aussi être mortes post-pub), mais **surtout** préparer un pivot plus ambitieux vers **features propriétaires** (microstructure features sur notre tick data SPY/QQQ Polygon, dérivées PCA de cross-section ETF, news sentiment) — ce qui correspond au futur "step 0" de l'auteur.

3. **Ajoute un test méta** à appliquer à tout futur candidat : avant de backtester, demander "est-ce que cette idée est publique ? depuis quand ? si oui, a-t-elle été crowded?". Si oui, pré-probabilité d'edge 65% décotée → bar Stage 2 PASS doit être encore plus haute.

4. **Pas d'implémentation directe** (rien à coder).

## 11. Citation-clés

> "If you don't create the edge yourself or have to sign an NDA or some legally binding document to keep it secret, it is [ __ ] If the trading strategy is public or for sale, it is a scam. TJR says he sells his strategy to make some extra money on the side. If he had a strategy with an edge on some of the most liquid assets in the world, the most scalable assets in the entire world, why wouldn't he scale it to tens of millions or hundreds of millions of dollars? Why would he still be trading on his phone alone?"

> "If ICT concepts don't work, then what does? Something proprietary. Nothing you're going to find online. If you can find it published, it doesn't work. If somebody's selling it to you, it doesn't work. You have to build it yourself."

> "If we estimate the effect of statistical bias to be about 10% in research papers that claim to have found edges in financial markets, then this paper which analyzes the effects of publication on the returns of edges which were published estimates that they decline by about 25% after publication. Meaning a private edge returning 100% per period would lose 25% of those returns after publication."

> "The entire way that retail has been made to understand trading is fundamentally wrong from the very first step. Everybody is starting from step two, choosing an influencer whose strategy they want to copy and learn. If the strategy is public, it doesn't work in the first place. Step one is building the strategy from scratch. Discovering unique and novel relationships between features that you engineer."
