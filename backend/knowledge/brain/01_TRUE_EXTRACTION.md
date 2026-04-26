# 01_TRUE_EXTRACTION — Phase I consolidation

**Corpus source** : `videos/true/` — 20 vidéos word-for-word (14 TJR + 1 Fabio Valentini + 5 non-TJR méthodo/quant/options + 1 ORB backtest)
**Date** : 2026-04-24
**Fichiers détaillés** : `backend/knowledge/brain/true_extraction/<video_id>.md` (20 fiches)
**Objectif** : révéler ce que MASTER manque ou implémente mal, identifier candidats playbooks structurellement novels, extraire gaps méthodologiques.

---

## 1. Index des 20 extractions (ordre §0.A.bis)

| # | video_id | Titre | Auteur | Durée | Q5 classification | Valeur bot | Fichier |
|---|---|---|---|---|---|---|---|
| 1 | `DyS79Eb92Ug` | Trading LIVE with the BEST Scalper | Fabio Valentini | 2h21m | pédagogique | faible — hors infra (orderflow/CVD/0DTE) | [DyS79Eb92Ug.md](true_extraction/DyS79Eb92Ug.md) |
| 2 | `PlsHO33j6B8` | Advanced Imbalance (NDOG/NWOG/NCOG/BPR) | TJR | 23m | playbook (NWOG) + management | moyenne — **NWOG candidat** | [PlsHO33j6B8.md](true_extraction/PlsHO33j6B8.md) |
| 3 | `4sRDnVmLcMk` | Inverse FVG Explained | TJR | 22m | management + filtre | moyenne — règle stacked FVG manquante Aplus_03 | [4sRDnVmLcMk.md](true_extraction/4sRDnVmLcMk.md) |
| 4 | `joe_XTCn5Bs` | Equilibrium Explained | TJR | 14m | filtre / continuation | moyenne — brique EQ absente repo | [joe_XTCn5Bs.md](true_extraction/joe_XTCn5Bs.md) |
| 5 | `7dTQA0t8SH0` | SMT Divergence Explained | TJR | 16m | filtre + playbook candidat | **ÉLEVÉE — SMT SPY/QQQ** | [7dTQA0t8SH0.md](true_extraction/7dTQA0t8SH0.md) |
| 6 | `L4xz2o23aPQ` | Time Theory | TJR | 11m | filtre temporel | moyenne — overlay time-gate 4/4 | [L4xz2o23aPQ.md](true_extraction/L4xz2o23aPQ.md) |
| 7 | `52nxvJKM57U` | Funded Accounts | TJR | 19m | pédagogique commercial | nulle | [52nxvJKM57U.md](true_extraction/52nxvJKM57U.md) |
| 8 | `ironJFzNBic` | How To Find Daily Bias | TJR | 31m | filtre HTF | **ÉLEVÉE — HTF bias 7-step** | [ironJFzNBic.md](true_extraction/ironJFzNBic.md) |
| 9 | `TEp3a-7GUds` | TJR's Strategy Explained | TJR | 44m | playbook complet | **ÉLEVÉE — pipeline 4-stage** | [TEp3a-7GUds.md](true_extraction/TEp3a-7GUds.md) |
| 10 | `wzq2AMsoJKY` | THE Equilibrium Video | TJR | 19m | brick continuation | moyenne — formalisation EQ 4/4 | [wzq2AMsoJKY.md](true_extraction/wzq2AMsoJKY.md) |
| 11 | `vlnNPFu4rEQ` | 6 Rules (6 years of trading) | TJR | 15m | pédagogique psycho | nulle | [vlnNPFu4rEQ.md](true_extraction/vlnNPFu4rEQ.md) |
| 12 | `FJch02ucIO8` | $1M+ From One Simple Confluence | TJR | 23m | playbook | **ÉLEVÉE — SMT + TP "SMT completion"** | [FJch02ucIO8.md](true_extraction/FJch02ucIO8.md) |
| 13 | `pKIo-aVic-c` | Liquidity Is The Easiest Way | TJR | 25m | contexte + management | **ÉLEVÉE — fresh-pool TP upgrade** | [pKIo-aVic-c.md](true_extraction/pKIo-aVic-c.md) |
| 14 | `BdBxXKGWVjk` | Simple Concept +$1M (IFVG) | TJR | 16m | management | moyenne — stacking rule + pre-sweep gate | [BdBxXKGWVjk.md](true_extraction/BdBxXKGWVjk.md) |
| 15 | `s9HV_jyeUDk` | Backtested Guru's Strategy | IRONCLAD | 15m | méthodologie | **ÉLEVÉE — OB/PD dégradent (8700 combos)** | [s9HV_jyeUDk.md](true_extraction/s9HV_jyeUDk.md) |
| 16 | `6ao3uXE5KhU` | Forward Factor Options SPY | Volatility Vibes | 36m | playbook (hors infra) | moyenne — **pivot Plan B options** | [6ao3uXE5KhU.md](true_extraction/6ao3uXE5KhU.md) |
| 17 | `W722Ca8tS7g` | 4 backtesting techniques | Unbiased Trading | 11m | méthodologie | **ÉLEVÉE — stress+MC gap G5** | [W722Ca8tS7g.md](true_extraction/W722Ca8tS7g.md) |
| 18 | `ATWyVRbrDvs` | Backtesting my 85% WR | Tradewriter | 15m | pédagogique anti-exemple | nulle — catalogue red flags | [ATWyVRbrDvs.md](true_extraction/ATWyVRbrDvs.md) |
| 19 | `fIEwVmJJ06s` | Ivy League Quant (build from scratch) | DeltaTrend | 7m | méta-méthodologie | **ÉLEVÉE — bombe méta "public = mort"** | [fIEwVmJJ06s.md](true_extraction/fIEwVmJJ06s.md) |
| 20 | `ZF8uKPqAu8M` | ORB Breakout+Pullback 5y backtest | Trading Steady | 11m | pédagogique/méthodo | moyenne — **confirme KILL ORB** (11e data point externe) | [ZF8uKPqAu8M.md](true_extraction/ZF8uKPqAu8M.md) |

**Répartition valeur** : 6 ÉLEVÉE / 7 moyenne / 6 faible-nulle / 1 hors-infra.

---

## 2. Candidats playbooks structurellement novels émergents

### A. SMT Divergence SPY/QQQ v1 — ★★★
**Sources convergentes** : `FJch02ucIO8` (TJR "one confluence") + `7dTQA0t8SH0` (TJR SMT explained) + `ironJFzNBic` (HTF bias SMT component). TJR revient 3× indépendamment sur ce signal.

**Mécanique** :
- **Setup** : deux indices corrélés (SPY / QQQ) après sweep d'un pool HTF (4H > 1H)
- **Signal** : leading index casse structure (LH en downtrend, HL en uptrend), lagging continue le trend
- **Entry** : trade le lagging dans le sens du leading
- **TP "SMT completion"** : low/high attaché au swing qui a créé le pool sweeped — **3e type TP structural inédit** pour `tp_resolver` (les 2 existants : fixed RR + liquidity_draw_swing_k3)

**Dual-asset signal absent de tous les 26 playbooks DexterioBOT** (Phase D.2 TF audit confirme). Corpus disponible (SPY+QQQ intraday). Briques 50% en place (pivots k3 via `directional_change.py`, PairSpreadTracker briques D1+D2 stat_arb, liquidity pools via tp_resolver). À construire : détecteur SMT cross-instrument synchronisé + extracteur attached-high/low.

**Q1 OUI | Q2 OUI | Q3 OUI | Q4 attendu** : C si signal faible (même cas que stat_arb v1/v2), B si sous-exercé (sweep HTF + SMT simultané + lagging entry rare sur 4w).

### B. Aplus_01 Family A v2 TRUE HTF **enrichi** — ★★★
**Sources convergentes** : `ironJFzNBic` (HTF bias 7-step) + `TEp3a-7GUds` (TJR pipeline 4-stage) + `wzq2AMsoJKY` (EQ brick) + `L4xz2o23aPQ` (time-gate).

**Déjà en §0.5bis entrée #1** mais **scope à élargir vs spec actuelle** :
- Spec plan v3.1.2 : vrai sweep 1h/4h + vrai bias D/4H (vs v1 SWEEP@5m + SMA proxy)
- **Enrichissement suggéré par TRUE** : 
  - **Bias HTF 7-step** (pas juste structural HH-HL) : structure 4H/1H + position cycle + FVG HTF respect/disrespect + draws on liquidity ranked + PM manipulation + close-through flip + SMT cross-index
  - **Pipeline 4-stage TJR** : potential orders fill → confirmation BOS **OR IFVG** (double shots) → continuation FVG **OR EQ** → exit at liquidity
  - **Equilibrium 5m** (brique wzq2AMsoJKY) comme alternative FVG continuation
  - **Time-gate** NY open manipulation 9:30-9:50 → macro entry 9:50-10:10 → cut-off 10:30

**Q1 partial** (briques 60% en place, SMT+EQ à construire) | Q2 OUI | Q3 OUI | Q4 attendu B ou C.

### C. NWOG (New Week Opening Gap) — ★★
**Source** : `PlsHO33j6B8` (TJR Advanced Imbalance).

Gap weekly open vs previous week close — playbook candidat honnête (différent des FVG intraday). NDOG (daily) présenté comme utile mais moindre que NWOG, NCOG (calendar-based) admis inutile par TJR lui-même, BPR = brick target (pas playbook).

**Q1 NON** (pas de détecteur gap session-based dans le repo) | Q2 OUI | Q3 OUI | Q4 B probable (gaps significatifs rares).

### D. Fresh-pool TP resolver upgrade — ★★ (brique, pas playbook)
**Source** : `pKIo-aVic-c` (TJR Liquidity).

Upgrade `tp_resolver.py` avec :
- `pool_tf=["4h","1h"]` (vs actuel majoritairement 5m/15m)
- `require_unsweeped_since="session_prior"` (freshness filter — absent)
- Reaction confirmation obligatoire (sweep sans reaction ≠ sweep valide)
- Stack density ranking
- Direction alignment

**Brique transversale** applicable à tous playbooks futurs (notamment candidats A+B). **Priorité après §0.7 G4** (ou parallèle).

### E. Options Forward-Factor Calendar — ★ (pivot Plan B long-terme)
**Source** : `6ao3uXE5KhU` (Volatility Vibes).

Long calendar spread piloté par FF = (IV_front − IV_forward)/IV_forward ≥ 0.20, 27% CAGR / 2.4 Sharpe / 19 ans backtest. **Infra options absente** (pas de chain, Greeks, expiry manager). **Candidat pivot §0.3 point 3** si ICT/MASTER définitivement épuisé.

---

## 3. Gaps méthodologiques identifiés (pour §0.7 tech debt)

### G5 candidat — Stress + Monte Carlo gate
**Source** : `W722Ca8tS7g` (Unbiased Trading 4 techniques).

Notre O5.3 actuel (bar permutation 2000 iter) couvre 3/4 techniques citées. **Gaps** :
- **Stress automatique** : ×2 commissions, ×3 slippage, 1-5 bars delay sur candidat Stage 2/3
- **Monte Carlo shuffle** des trades pour mesurer survivability / DD distribution

Proposé comme **G5 post-G4** ou **parallèle** entre runs §0.5bis.

### Méta-gate "public vintage check" — hypothèse
**Source** : `fIEwVmJJ06s` (Ivy League Quant bombe méta).

Règle candidate : si une idée publiée publiquement depuis > 10 ans (cas ICT MASTER, J&T 1993, Avellaneda-Lee 2010), exiger preuve **en corpus propre** avec décote pré-probabilité -25% à -35% avant Stage 2. Formalise l'hypothèse "edge public = arbitré".

**À débattre** : pas consensus — pourrait invalider §0.5bis #2 (J&T) et #3 (Avellaneda) avant même leur test. Alternative : appliquer comme règle d'attente (nécessite résultats ≥ gate × 1.5 pour passer Stage 2).

---

## 4. Thèmes transversaux majeurs

### 4.1 Tension "MASTER mal implémenté" vs "MASTER arbitré"

Les 20 extractions révèlent **deux hypothèses non-exclusives** qui expliquent les 10 data points négatifs :

**Hypothèse A — Implémentation imparfaite** (supporté par vidéos 5, 8, 9, 12, 13) :
- Notre HTF bias = SMA proxy (0/171 rejections Phase D.1) ≠ TJR 7-step
- Notre TP fixed RR ≠ liquidity-draw + SMT completion + pool freshness
- Aucun de nos playbooks n'a jamais fait SMT cross-index
- Aucun n'a fait equilibrium active swing strict

Si A est vraie → Aplus_01 v2 TRUE HTF enrichi + SMT SPY/QQQ **doivent** produire un edge.

**Hypothèse B — ICT public arbitré** (supporté par vidéos 15, 18, 19) :
- 8700 combos Forex : 4/5 gurus perdent 70-86% ; OB/PD dégradent
- Morgan Stanley 1987 pairs → évaporé post-pub ; papers académiques -25% post-pub
- TJR/ICT = domaine public, donc concurrentiellement mort

Si B est vraie → Aplus_01 v2 + SMT échoueront aussi, et il faudra pivoter features non-publiques (microstructure, PCA residuals, news ML) ou options (plan B 6ao3uXE5KhU).

**Décision** : ces hypothèses ne sont **pas mutuellement exclusives**. Le chemin rationnel est :
1. Tester candidats A+B (SMT + Aplus_01 v2 TRUE HTF enrichi) avec budget §19.3 strict
2. Si 2 FAIL convergents → hypothèse B renforcée → pivot §0.3 point 3
3. Si 1 PASS → hypothèse A validée partiellement → continuer backlog

### 4.2 Convergence sur "freshness" et "hierarchy"

Plusieurs vidéos insistent indépendamment sur :
- **Freshness** des pools/liquidity (pKIo-aVic-c, ironJFzNBic, TEp3a-7GUds)
- **TF hierarchy** 4H > 1H > 15m > 5m > 1m (ironJFzNBic, pKIo-aVic-c, TEp3a-7GUds)
- **Pre-market + NY open manipulation** comme fertile (L4xz2o23aPQ, ironJFzNBic, TEp3a-7GUds)

Notre bot fait majoritairement l'opposé : pools 5m/15m, pas de freshness tracker, NY mid-session sans distinction du cut-off 10:30.

### 4.3 Red flags TJR lui-même

`TEp3a-7GUds` : TJR refuse explicitement de donner step-by-step ("shut up, bro") = non-falsifiable pur dans sa forme originale. `vlnNPFu4rEQ` + `52nxvJKM57U` = contenus commerciaux sans edge. `BdBxXKGWVjk` = IFVG déjà réfutée 3× chez nous. **Le corpus TJR est exploitable mais nécessite reconstruction critique, pas copie littérale.**

### 4.4 Validation externes de 2 décisions internes

- `ZF8uKPqAu8M` (ORB Pullback) **confirme externe KILL d'ORB_Breakout_5m** DENYLIST → 11e data point convergent
- `s9HV_jyeUDk` (IRONCLAD 8700 combos) **confirme** que **OB et premium/discount dégradent** → justifie OB_Retest_V004 DEFER + Phase D.1 HTF nul
- `wzq2AMsoJKY` (TJR EQ équivaut OB/BB) → 2e justification OB_Retest_V004 DEFER

---

## 5. Implications pour le plan v3.1.2

### KEEP (validé par TRUE)
- §0.5bis entrée #1 Aplus_01 Family A v2 TRUE HTF — direction correcte, **scope à élargir** (bias 7-step + SMT + EQ + time-gate)
- §0.6 Stages 1→4 — pipeline robuste (W722Ca8tS7g confirme 3/4 techniques déjà couvertes)
- §0.7 G1-G4 DONE — budget slippage correctement intégré
- Kill switch §19.3 itérations max 3 — confirmé par ZF8uKPqAu8M (3 variantes ORB échouent)

### AMEND candidats (à valider en Phase V)
- **AMEND §0.5bis** : insérer **SMT Divergence SPY/QQQ v1 AVANT Aplus_01 v2 TRUE HTF** — signal plus structurellement novel (dual-asset vs single-asset bias), briques 50% en place, budget infra plus léger
- **AMEND §0.7** : G5 Stress+Monte Carlo gate (optional, post-G4)
- **AMEND §0.5bis** : décote académique (#2 J&T, #3 Avellaneda) post fIEwVmJJ06s — ou exiger preuve × 1.5
- **AMEND §0.5bis** : entrée #5 Options forward-factor comme pivot Plan B long-terme

### NEW candidates (post-épuisement backlog ou insertion)
- NWOG playbook
- Fresh-pool TP resolver upgrade (brique parallèle)

### RISK : hypothèse B "ICT arbitré"
Si A+B testés et convergents négatifs sur §0.5bis #1-4, l'argument fIEwVmJJ06s devient fort. §0.3 point 3 redéclenchera avec options F1-F5 + nouvelle option F6 "Options forward-factor" + F7 "Non-public features (microstructure, news ML)".

---

## 6. Prochaines étapes Phase II

1. **Cross MASTER × TRUE** : lire MASTER_FINAL.txt pour vérifier que les 4 nouveautés majeures (HTF bias 7-step, SMT SPY/QQQ, EQ active swing strict, fresh-pool TP) sont **vraiment absentes** ou juste mal implémentées. Produit `02_MASTER_REFINED.md`.
2. **QUANT overlay** : QUANT_FINAL.txt (20 vidéos) croisé avec TRUE — permutation tests + bar tests + WF + méthodologie. Produit `03_BRAIN_TRUTH.md`.
3. **CODE_AUDIT** : matrix par playbook (ALLOWLIST + DENYLIST + ARCHIVED) vs BRAIN_TRUTH. Produit `04_CODE_AUDIT.md`.
4. **PLAN_DECISION** : KEEP / AMEND / PIVOT. Produit `05_PLAN_DECISION.md`.

---

**Artefacts produits Phase I** :
- `backend/knowledge/brain/01_TRUE_EXTRACTION.md` (ce fichier, index+synthèse)
- `backend/knowledge/brain/true_extraction/<video_id>.md` × 20 (fiches détaillées)
- Corpus source : `videos/true/` (20 transcripts word-for-word + TRUE_FINAL.txt + manifest.json)

Phase I close. Passage Phase II.
