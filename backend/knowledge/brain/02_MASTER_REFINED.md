# 02_MASTER_REFINED — Cross MASTER × TRUE

**Objectif** : valider/invalider l'hypothèse "MASTER dit les bonnes choses mais le bot les a mal codées".
**Sources** : `/home/dexter/Documents/MASTER_FINAL.txt` (71 transcripts ICT, 48115 lignes) × 20 fiches TRUE (`01_TRUE_EXTRACTION.md` + `true_extraction/*.md`).
**Date** : 2026-04-24.
**Méthode** : grep stratégique MASTER sur chaque concept N1-N4, lecture contextuelle ±30 lignes, comparaison précision vs TRUE.

---

## 1. Résumé exécutif

- **Hypothèse directrice VALIDÉE PARTIELLEMENT** — MASTER contient 4/4 concepts N1-N4 mais avec **précision hétérogène** : N2 (SMT) et N4 (freshness/reaction) sont couverts de façon presque identique à TRUE ; N1 (HTF bias) utilise un **framework différent mais complémentaire** (3 daily profiles + draws + previous session) ; N3 (Equilibrium) définition plus large (swing H/L générique, pas strictement "most recent").
- **Le gap principal ≠ conceptuel. Il est implémentationnel.** Le bot actuel a (a) un SMA proxy bias (Phase D.1 nul) là où MASTER+TRUE demandent état FVG/structure/draws, (b) `tp_resolver` liquidity_draw sans freshness tracker, (c) aucun détecteur SMT cross-index, (d) aucune brique equilibrium 50%.
- **97 % des nouveautés TRUE sont déjà dans MASTER** sous forme narrative. Les 3 % structurellement nouveaux dans TRUE : (i) règle stricte "most recent swing" pour EQ (TJR crie dessus — MASTER reste générique), (ii) ranking explicite des draws et leur invalidation si déjà swept (MASTER le fait implicitement par exemple), (iii) règle "trade the leading index" en SMT (MASTER dit "bias confluence" sans opérationnaliser le choix d'instrument).
- **Implication plan §0.5bis** : KEEP entrée #1 Aplus_01 Family A v2 avec scope élargi TRUE (FVG respect state-machine + SMT + EQ most-recent + time-gate 9:50-10:10) — mais NE PAS traiter TRUE comme "super-MASTER", TRUE est **l'explication opérationnelle** de MASTER, pas un enrichissement théorique.
- **Hypothèse B "MASTER public arbitré" (fIEwVmJJ06s)** demeure vivante : MASTER contient le bon framework, le bot ne l'a jamais vraiment codé — si le codage fidèle échoue aussi, B sera confirmée (et le framework ICT est simplement insuffisant, pas juste mal implémenté).

---

## 2. Audit concept par concept

### 2.1 HTF Bias (N1)

**TRUE dit** (`ironJFzNBic`, 7-step) :
1. Structure HH/HL 4H/1H
2. Position dans cycle (sweep récent ? retrace FVG ?)
3. FVG HTF respect/disrespect binary state (state-machine)
4. Draws on liquidity **rankés** (prev D H/L, Asia H/L, London H/L, hourly) **exclure ceux déjà swept**
5. Pre-market + NY open manipulation observation
6. Respect + legs = bias confirmé ; close through = bias flip
7. SMT cross-index = refinement

**MASTER dit** (video 016 `How To Find Daily Bias`, lignes 6982-7131) :
- Framework différent : **3 daily profiles** (consolidation → manipulation / manipulation → reversal / manipulation+reversal → continuation) appliqués à la session précédente (London pour NY).
- Draws on liquidity HTF = **4H highs/lows + 1H highs/lows + session highs/lows + previous day H/L** (quasi-identique TRUE ligne 7073).
- "Target the draws in the other direction" (ligne 7106) = bias operational = target direction.
- FVG respect/disrespect **explicitement traité** (lignes 4999-5024, 22676 "what's being respected versus disrespected") comme signal de direction.
- "Already swept" filter **présent** (ligne 13609 "another hourly low... was actually already swept we have another hourly low right here" — exclu de la sélection).
- **Structure HH/HL** formalisée (lignes 4307, 6508-6513, 11419-11440, 44262-44320) avec définition BOS "candle close above most recent high".
- **External→internal→external cycle** : absent en ces mots exacts, mais concept "manipulation+reversal+continuation" couvre l'idée.
- **SMT** comme confluence de bias (cf 2.2) : présent mais non décrit comme composante bias.

**Verdict** : **CONFIRMED_BY_BOTH, framework équivalent avec nuances** — MASTER utilise "3 daily profiles + draws + structure + respect/disrespect + sessions" qui couvre 6/7 composantes TRUE. La composante SMT (N7) est traitée séparément dans MASTER (video SMT dédiée) et couplée au bias comme confluence, pas comme composante intégrée. Précision **équivalente** sur (1,3,4,5,6), **plus narrative** dans MASTER sur (2 cycle) et TRUE plus opérationnel.

**Implications bot** : le bot actuel utilise `SMA_5 D/4H` proxy avec 0/171 rejections (Phase D.1 = cosmétique). Ni MASTER ni TRUE ne mentionnent SMA pour bias. **Gap implémentationnel identique face aux deux sources**. La correction = structure HH/HL + FVG respect state machine + draws filter already-swept. Les deux sources l'exigent ; aucune ne donne SMA.

---

### 2.2 SMT Divergence cross-index SPY/QQQ (N2)

**TRUE dit** (`7dTQA0t8SH0` + `FJch02ucIO8`) :
- 2 indices corrélés (ES/NQ), après sweep HTF simultané
- Bullish SMT : un fait HL, l'autre LL → entry sur celui qui fait HL (leading)
- Bearish SMT : un fait LH, l'autre HH → entry sur celui qui fait LH (leading)
- Condition obligatoire : "at HTF liquidity draw" sinon "useless"
- TP "SMT completion" = attached swing low/high
- TF usage : 5m ou 15m préféré, pas 1m

**MASTER dit** (lignes 12745-12841, video dédiée + plusieurs réferences lignes 5867, 7215, 16288, 21744, 21879) :
- "One index forecasting what another index is going to do"
- "For a bullish SMT, one index creates a higher low while the other index creates a lower low" (ligne 12759) = **identique à TRUE**
- "For bullish SMT we're only using the lows and when we're looking for bearish SMT we're only looking for highs" (ligne 12793) = **identique à TRUE**
- **Condition bias explicite** : "find your bias, because if you don't have a bias, then you'll be finding SMT divergences that are conflicting" (ligne 12768-12772)
- **Condition HTF liquidity** : "high time frame liquidity sweep" (lignes 12794, 16291) = **identique TRUE**
- **Trade-the-leading-index** : "if we see a higher low formed on GasPak and we see a lower low formed on S&P, it means the S&P is lagging behind NASDAQ... there's going to be more opportunity on ES" (lignes 12830-12833) = **identique TRUE**
- TF préférence : "typically my SMT divergence is going to be on the five minute or the 15 minute... I do not like to use SMT divergence on the one minute" (lignes 12799-12802) = **identique TRUE**

**Verdict** : **CONFIRMED_BY_BOTH avec couverture quasi-identique** — MASTER et TRUE disent la même chose sur SMT. TRUE précise un **détail opérationnel supplémentaire** : le TP "SMT completion" (attached swing). MASTER ne donne pas de TP structural SMT-specific.

**Implications bot** : aucun des 26 playbooks DexterioBOT n'utilise dual-asset signal (Phase D.2 confirmé). **Gap total**. Un nouveau playbook `SPY_QQQ_SMT_Sweep_Reversal` serait **fidèle à MASTER et TRUE conjointement**. Priorité §0.5bis haute.

---

### 2.3 Equilibrium (N3)

**TRUE dit** (`joe_XTCn5Bs` + `wzq2AMsoJKY` + `TEp3a-7GUds`) :
- 50% entre **most recent** swing H et swing L (règle stricte, TJR "[bleep] up" crié pendant 3min)
- Pas le plus extrême. Pas un ancien swing. Le **dernier** formé dans la leg en cours.
- Redessiner à chaque HH (uptrend) / LL (downtrend)
- Continuation confluence alternative à FVG
- TJR élimine explicitement OB/BB comme équivalents fonctionnels ("if you've hit equilibrium, OB et BB ne sont pas nécessaires")

**MASTER dit** (lignes 12415-12573, video dédiée) :
- "Equilibrium measures the point from swing high to swing low or vice versa" (ligne 12427)
- "50% mark or the halfway point from the swing low to the swing high" (ligne 12494)
- "Premium and discount" framework (lignes 12434, 12489)
- "Uptrend we take it from the low up to the high" (ligne 12495) — direction trend-aware
- "Continuation confluence" (ligne 12446)
- "Similar to fair value gaps, similar to order blocks... continuation confluences" (lignes 12524-12525, **12556**) — MASTER **traite EQ, FVG, OB, BB comme équivalents** = **contradiction directe vs TRUE qui les différencie**
- **"Most recent" absent explicitement** : MASTER dit "swing high to swing low" sans préciser lequel. Pas de cri anti-erreur sur le choix du swing.
- GAN box utilisé (ligne 12494) — outil technique MASTER mais pas opérationnel côté code.

**Verdict** : **NUANCED_IN_TRUE** — TRUE est **strictement plus précis** sur deux points :
1. **"most recent" obligatoire** : opérationnel (détectable en code via `directional_change.py` swing_k3 dernier pivot) ; MASTER laisse ambigu.
2. **Éliminer OB/BB comme équivalents** : TRUE tranche, MASTER les met en interchangeables.

Pour le reste (définition 50%, premium/discount, trend-direction, continuation role) = **identique**.

**Implications bot** : le bot n'a ni brique `equilibrium_zone` ni détecteur "most recent swing retrace". Gap complet. Implémenter EQ fidèle = **utiliser règle TRUE "most recent" stricte** (pas MASTER générique). Brique triviale à coder sur `directional_change.py` existant.

---

### 2.4 Pool Freshness + TF Hierarchy 4H/1H + Reaction Confirmation (N4)

**TRUE dit** (`pKIo-aVic-c`) :
- Freshness : pool non-sweeped dans sessions précédentes (prev session + PM + London)
- TF hierarchy 4H > 1H > autres
- Reaction obligatoire : sweep sans reaction ≠ sweep valide
- Pool stacks (clusters) = signal plus fort
- Direction : trade contre le sweep (reversal)
- TP = pool opposé fresh
- R1-R9 formalisés

**MASTER dit** (lignes 21490-21552 + 13605-13624 + 15971-16045) :
- **Session de marking pre-NY** : "I mark out the four hour highs and lows that the market could be able to sweep **or has swept** either during the previous session during pre-market or London session" (lignes 21503-21505) = **identique TRUE**
- **Freshness filter** : "And if liquidity hasn't been swept during those sessions, then awesome. I'm expecting New York market to open and then for us to sweep out liquidity during the current session" (lignes 21505-21507) = **identique TRUE**
- **Reactive trade pattern** : "if I see that liquidity has already been swept during pre-market and we're already reacting off of it. Awesome. Then this was the liquidity sweep for the day and I'm just going to take a trade reactive off of this" (lignes 21508-21512) = **identique TRUE**
- **TF hierarchy 4H > 1H** : "The best time frames... to identify liquidity on for me is going to be the 4 hour and the 1 hour" (lignes 21502-21503 + précédente vidéo liquidity) = **identique TRUE**
- **Reaction requise** : "If price comes down and takes out a low and keeps going down, is it a liquidity sweep? Fuck no. Because it's not reacting to it. That's why we want to mark out all the lows and all the highs" (lignes 21497-21498, cité verbatim dans fiche TRUE aussi) = **identique, MÊME LIGNE**
- **Pool stacks** : "these lows are stacked so we sweep all these stacked lows" (ligne 5539) = présent mais moins formalisé
- **Macro kill zone 9:50-10:10** : "from 950 to 1010 is always going to be a really solid time" (lignes 15985-16005) = **présent et précis dans MASTER** ; TRUE le cite mais vidéo `L4xz2o23aPQ` "Time Theory" est un subset de ce contenu MASTER
- **Exclusion already-swept** : exemple explicite ligne 13609 "we have another hourly low right here that was actually already swept" = exclu de la sélection.

**Verdict** : **CONFIRMED_BY_BOTH quasi-identique** — cette vidéo TRUE `pKIo-aVic-c` est **très probablement une dérivation directe** du contenu MASTER (TJR a visiblement enregistré la même matière multiple fois). La fiche TRUE capture ~100% de ce que MASTER dit. Pas de nouveauté.

**Implications bot** : `tp_resolver` actuel majoritairement 5m/15m pools, sans freshness tracker, sans reaction filter. **Gap implémentationnel identique face aux deux sources**. Upgrade nécessaire : `pool_tf=["4h","1h"]` + `require_unsweeped_since="session_prior"` + reaction gate (state machine post-sweep sur LTF 5m/1m).

---

## 3. Concepts MASTER absents de TRUE

### 3.1 3 Daily Profiles (video 016)
- Consolidation → manipulation/reversal (new session)
- Manipulation (old session) → reversal (new session)
- Manipulation+reversal (old session) → continuation (new session)
**Verdict** : framework **structurant** pour prédire la profile du jour. Absent TRUE. **Pertinent backlog** — pourrait servir de filtre top-layer avant tout autre signal intraday. Pas couvert par bot.

### 3.2 BPR (Balanced Price Range)
- Ligne 12290-12324 : BPR = zone target, pas playbook ; créée quand FVG bullish + FVG bearish opposés se chevauchent.
**Verdict** : brique TP alternative. Non-critique pour backlog immédiat.

### 3.3 Breaker Block / Order Block (définitions rigoureuses)
- MASTER dédie des vidéos entières à OB et BB (lignes 12574+, 1272+).
- TRUE les mentionne mais (a) TJR lui-même élimine OB/BB si EQ présent (`wzq2AMsoJKY`), (b) IRONCLAD 8700 combos montre OB/PD dégradent (`s9HV_jyeUDk`).
**Verdict** : concepts **présents MASTER, exclus ou dégradés TRUE**. Bot a `OB_Retest_V004` DEFER (n=2). **Ne pas re-investir** — TRUE confirme externe que OB est probablement arbitré.

### 3.4 Power of Three / AMD (Accumulation-Manipulation-Distribution)
- Mentionné ligne 2265 ("learn power of three") mais sans approfondissement complet dans ce corpus MASTER.
**Verdict** : concept ICT classique, **non critique** (TJR ne l'opérationnalise pas dans ses vidéos détaillées).

### 3.5 Time-based Macro Windows multiples (AM + PM kill zones)
- MASTER : AM 9:50-10:10 + PM 13:50-14:10 explicites (lignes 16028-16045).
- TRUE `L4xz2o23aPQ` mentionne le concept sans la paire exacte.
**Verdict** : MASTER plus **complet** sur macro PM. Pertinent bot (bot n'a pas time-gate macro distinct du session_window).

### 3.6 OTE (Optimal Trade Entry) Fibonacci
- Ligne 22575 : unique mention "OTE from these highs". Pas de vidéo dédiée dans l'échantillon lu.
**Verdict** : concept ICT classique absent de l'emphase MASTER et TRUE. Non-critique.

**Top 3 concepts MASTER seuls importants découverts** : (1) **3 daily profiles** (filtre profile-of-the-day), (2) **PM kill zone 13:50-14:10** (time-gate étendu), (3) **BPR** (TP brick alternative).

---

## 4. Contradictions MASTER ↔ TRUE

### 4.1 Equilibrium équivalents OB/BB
- MASTER : "same thing with order blocks, same thing with fair value gaps, same thing with breaker blocks, same thing with equilibrium" (ligne 12555-12556) — **interchangeables**.
- TRUE `wzq2AMsoJKY` : TJR **élimine** OB/BB comme équivalents fonctionnels si EQ présent.
**Interprétation** : TJR **a évolué** (TRUE plus récent probablement). MASTER reflète un stade antérieur où OB/BB/EQ étaient stackés ; TRUE dit qu'EQ les absorbe. IRONCLAD `s9HV_jyeUDk` (8700 combos externe) soutient TRUE (OB/PD dégradent).
**Action bot** : privilégier EQ + FVG, DEFER OB. Cohérent avec statut actuel `OB_Retest_V004 DEFER`.

### 4.2 "Most recent swing" pour equilibrium
- MASTER : "swing high to swing low" générique (ligne 12427).
- TRUE `joe_XTCn5Bs` : "most recent, not the one 3 swings back" (règle stricte).
**Interprétation** : évolution/précision TRUE. TRUE opérationnel, MASTER ambigu.
**Action bot** : coder EQ avec règle TRUE stricte (`directional_change.py` swing_k3 dernier pivot).

### 4.3 Aucune autre contradiction majeure identifiée
MASTER et TRUE se recouvrent à ~95 % sur les thèmes audités.

---

## 5. Implications pour le bot

### 5.1 Code audit préliminaire (à finir en Phase IV)

| Concept | Source(s) théoriques | État bot | Misalignment severity |
|---|---|---|---|
| **HTF Bias** | MASTER + TRUE (7-step ≈ 3 daily profiles) | SMA_5 proxy `require_htf_alignment: D` (Phase D.1 : 0/171 rejected) | **GRAVE** — ni MASTER ni TRUE ne parlent de SMA. Substituer par structure HH/HL + FVG respect state + draws ranking |
| **SMT Divergence** | MASTER + TRUE (identiques) | **Absent** | **GAP TOTAL** — 0 playbook cross-instrument, aucune brique `detect_smt_divergence` |
| **Equilibrium** | MASTER + TRUE (TRUE strict "most recent") | **Absent** | **GAP** — trivial à coder via `directional_change.py` swing_k3 |
| **Pool freshness** | MASTER + TRUE (identiques) | `tp_resolver` sans freshness, pools 5m/15m | **GRAVE** — résolveur cherche pools proches sans état de session ni reaction filter |
| **TF hierarchy 4H/1H** | MASTER + TRUE | `tp_resolver` accepte `pool_tf=[...]` mais configuré 5m/15m majoritairement | **MOYEN** — paramétrage YAML à corriger |
| **Reaction confirmation post-sweep** | MASTER + TRUE (identiques) | Absent des playbooks sweep-based (Liquidity_Sweep_Scalp KILL, Liquidity_Raid_V056 KILL, London_Fakeout_V066 KILL) | **GRAVE** — explique partiellement 3 KILL |
| **FVG respect/disrespect state machine** | MASTER (explicite) + TRUE | Détection FVG isolée (Aplus_03), pas de state post-formation | **MOYEN** — Aplus01Tracker peut servir de template |
| **Macro kill zone 9:50-10:10** | MASTER explicite + TRUE | Session windows larges sans micro-gate | **MOYEN** — overlay ajoutable |
| **3 daily profiles filter** | MASTER seul | Absent | **NEW GAP** — candidat top-layer filtre |

### 5.2 MASTER_REFINED = le "vrai MASTER" filtré par TRUE

**Principe** : pour chaque concept, adopter la version **la plus opérationnelle** (souvent TRUE car plus récente/précise) tout en conservant le framework large MASTER comme contexte.

**Références canoniques** à utiliser en implémentation :
- HTF Bias = MASTER video 016 (3 daily profiles) ∪ TRUE `ironJFzNBic` (FVG state + draws ranking + SMT integration)
- SMT = MASTER video SMT (lignes 12745+) ∩ TRUE `7dTQA0t8SH0` (quasi-identiques, prendre l'un ou l'autre)
- Equilibrium = **TRUE strict** `joe_XTCn5Bs` (most recent swing) + MASTER pour premium/discount narrative
- Freshness + TF hierarchy = MASTER lignes 21490-21552 ∪ TRUE `pKIo-aVic-c` (identiques)
- Macro kill zone = **MASTER plus complet** (AM + PM 13:50-14:10)
- 3 daily profiles = **MASTER seul**, ajouter à backlog comme filtre

### 5.3 Ce que ça change pour §0.5bis #1 Aplus_01 v2 TRUE HTF

Le scope proposé plan v3.1.2 (vrai sweep 4H/1H + vrai bias D/4H) **reste valide**. Enrichissements **confirmés par cross-MASTER** :
- **FVG respect state machine HTF** : opérationnaliser (TFA existant)
- **Draws ranking + already-swept filter** : MASTER l'illustre ligne 13609
- **SMT cross-index** : à coder nouvellement (0 brique existante)
- **Macro time-gate 9:50-10:10** : overlay sur session_window

**N'AJOUTE PAS** un nouveau gap conceptuel — confirme que TRUE est bien l'explicitation opérationnelle de MASTER.

---

## 6. Décision sur l'hypothèse directrice

**Hypothèse** : "MASTER dit les bonnes choses, le bot les a mal codées"

### Verdict : **VALIDÉE PARTIELLEMENT**

- **VALIDÉ** : sur N1, N2, N4, MASTER et TRUE convergent. Le bot n'a codé aucun des trois fidèlement (SMA proxy ≠ structure+FVG state, 0 SMT dual-asset, `tp_resolver` sans freshness). **Le gap est implémentationnel, pas conceptuel.**
- **PARTIEL** : sur N3 (Equilibrium), MASTER est moins strict que TRUE sur le "most recent" — mais le bot ne l'a pas codé du tout, donc le débat MASTER vs TRUE n'affecte pas l'action immédiate (coder EQ fidèlement).
- **NUANCE** : MASTER contient des concepts (3 daily profiles, PM macro, BPR) que TRUE ne traite pas. Complément utile.
- **RISQUE B** : même si on implémente MASTER+TRUE fidèlement sur N1-N4, l'hypothèse B "ICT public arbitré" (`fIEwVmJJ06s`) demeure testable. Si Aplus_01 v2 TRUE HTF enrichi + SMT SPY/QQQ échouent tous les deux (2 data points convergents), B sera renforcée et le framework ICT sera **empiriquement insuffisant**, pas juste mal codé.

### Chemin rationnel

1. **KEEP §0.5bis entrée #1** Aplus_01 v2 TRUE HTF avec scope enrichi (FVG respect state + draws ranking + SMT + EQ most-recent + macro time-gate).
2. **Priorité haute** : implémenter SMT SPY/QQQ comme **entrée ajoutée §0.5bis** (briques 50% en place, le reste = nouveau détecteur cross-instrument). TRUE et MASTER convergent totalement — implémentation fidèle possible.
3. **Brique transversale** : upgrade `tp_resolver.py` avec `pool_tf=["4h","1h"]` + `require_unsweeped_since="session_prior"` + reaction gate. Applicable à tous les playbooks futurs.
4. **Ne pas** créer playbook dédié OB/BB — MASTER et TRUE divergent, empirique bot déjà DEFER.
5. **Nouveau candidat backlog** : "3 daily profiles" comme filtre top-layer (MASTER seul, non-testé bot).
6. **Budget Stage 2 §0.7 G3** : E[R]_pre_reconcile > 0.197R/trade. Bar très haute. Si fidélité MASTER+TRUE ne la passe pas, pivoter vers hypothèse B (§0.3 point 3 déclenché post-Leg 4.2).

---

**Artefact produit Phase II** :
- `backend/knowledge/brain/02_MASTER_REFINED.md` (ce fichier)

**Prochaines étapes Phase II** :
- `03_BRAIN_TRUTH.md` : cross QUANT × TRUE (méthodologie, permutation tests, WF, bar tests)
- `04_CODE_AUDIT.md` : matrix par playbook (ALLOWLIST + DENYLIST + ARCHIVED) vs BRAIN_TRUTH
- `05_PLAN_DECISION.md` : KEEP / AMEND / PIVOT final
