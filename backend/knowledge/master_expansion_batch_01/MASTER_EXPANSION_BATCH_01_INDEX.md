# MASTER_EXPANSION_BATCH_01 — INDEX détaillé vidéo par vidéo

**Scope** : index batch §0.A.bis (v3.1.2 plan), **19 URLs YouTube** à classifier via workflow A-E per §0.A.
**Statut** : `SCAFFOLD` — aucune vidéo encore ingérée (A), transcrite (B), dédupliquée (C), classifiée (D) ou taguée (E).
**Date init** : 2026-04-22 (sous-batch 1, 14 URLs)
**Date extension** : 2026-04-23 (sous-batch 2, 5 URLs user-added après dédup intra-batch + inter-batch)

## Gouvernance — rappel règles dures §0.A.bis

- **R1** — Aucune vidéo n'ouvre un playbook directement.
- **R2** — Aucun code / YAML / module produit pendant §0.A.bis.
- **R3** — Clause anti-réanimation §10 r11 : thèse déjà invalidée sur 10 data points négatifs cross-playbook 2025 SPY/QQQ intraday → tag automatique `DUPLICATE` (pointer vers entrée historique).
- **R4** — Clause anti-borrowed-vocab : vocabulaire ICT sans mécanique fermée → `LOW_SIGNAL` ou `PEDAGOGICAL_ONLY`.
- **R5** — Clause séquentialité §0.5bis : `KEEP_PLAYBOOK_CANDIDATE` ne peut être promu en entrée §0.5bis tant que #1→#4 non épuisé, **sauf amendement Niveau 3 user-commité**.
- **R6** — Non-dispersion §19.2 : §0.A.bis en parallèle route §0.9, par batches de 3 vidéos entre runs longs. Budget total : ~1.5-2.5j pour 19 vidéos.

## Tags terminaux légaux (étape E)

| Tag | Destination |
|---|---|
| `KEEP_PLAYBOOK_CANDIDATE` | Dossier §18 A-D+H → review amendement Niveau 3 |
| `KEEP_OVERLAY` | `backend/knowledge/overlays/<name>/` (post-Stage 2 PASS uniquement) |
| `KEEP_FEATURE` | Extension `backend/engines/regime/` v2 (post-§9.1 débloqué) |
| `KEEP_MANAGEMENT` | Paramètre YAML knob local (pas de dossier) |
| `PEDAGOGICAL_ONLY` | Annotation INDEX — hors pipeline |
| `DUPLICATE` | Pointer vers entrée legacy/batch, stop |
| `LOW_SIGNAL` | Archive, stop |

## Workflow A-E par vidéo (rappel §0.A.bis)

Chaque vidéo doit traverser **intégralement** les 5 étapes :
1. **A — Ingest** : download transcript auto (youtube-transcript-api) ou fallback manuel. Sauvegarde `raw_transcript.txt` + `metadata.json`.
2. **B — Transcript + metadata extract** : `notes.md` ≤300 mots humain (thèse / mécanisme / TF / univers / règles entrée-exit / conditions fertiles-stériles). Interdit : paraphraser sans lire.
3. **C — Dedupe** : cross-check vs (i) 71 MASTER_legacy, (ii) 10 data points négatifs cross-playbook, (iii) vidéos précédentes du batch.
4. **D — Classify** : mini-strategy_card.md (si applicable) + taxonomie tag §0.A étape 3 + codability check §0.A étape 4 (4Q + 1Q classification).
5. **E — Status output** : tag terminal parmi les 7 légaux.

## Pré-checks globaux (cache partagé avant workflow C de chaque vidéo)

**MASTER_legacy (71 transcripts YouTube ICT `MASTER_FINAL.txt` 3.3MB)** — MAP canonique à `MASTER_PLAYBOOK_MAP.md`. Familles A-F déjà instanciées (toutes négatives/rares post-Leg-4.2, cf §0.4 état démarrage).

**10 data points négatifs cross-playbook SPY/QQQ intraday 2025 (à éviter réanimation)** :
1. Aplus_03 IFVG_Flip_5m v1 (n=47 E[R]=-0.074, peak_R p80=1.06 vs TP 2R unreachable)
2. Aplus_03_v2 α'' (n=22 E[R]=-0.019 Case B 73% fallback)
3. Aplus_04 HTF_15m_BOS v1 (n=55 E[R]=-0.074 PF 0.56)
4. Aplus_04_v2 α'' (n=15 E[R]=-0.057 Case C borderline)
5. Aplus_04_v2 ε reject_on_fallback (n=12 E[R]=-0.066 schéma isolé)
6. Stat_Arb_SPY_QQQ v1/v2 daily coint (n=8 E[R]=-0.179 byte-identical)
7. Aplus_01 Family A full v1 SWEEP@5m fallback (n=1 E[R]=-0.003 Cas B)
8. Aplus_02 Premarket Family F v1 (2 matches / 0 trades)
9. Quarantine PROMOTE 12w cohort (IFVG+VWAP+HTF_Bias tous cohort FAIL)
10. VIX-regime overlay cohort survivor_v1 (subset destructeur)

**Thèses réfutées rappel rapide** :
- Fixed RR TP (2R / 3R) sur signaux ICT isolés = plafonné winners.
- Schéma α'' liquidity_draw swing_k3 isolé = signal est plafond pas TP.
- ICT vocab-borrowing sans D/4H bias enforcé + liquidity-targeting + 1m confirm = 0/7 MASTER faithful historiquement.
- Calibration single-signal 3+ leviers = asymptote E[R]<0 (Morning_Trap / Liquidity_Sweep / BOS_Scalp).
- Portfolio quasi-BE via cohorte de négatifs marginaux = cross-contamination destructrice.
- HTF alignment SMA proxy = effet nul cross-playbook (Δ +0.040 aligned vs counter, ne croise pas zéro).
- Stat-arb SPY-QQQ 5m intraday z-score 2.0 = edge absent (v1+v2 byte-identical).
- VIX overlay sur survivor_v1 = destructeur (subset pire que baseline).

---

## Sous-batch 1 — Initial 2026-04-22 (14 vidéos)

### Vidéo #1 — `DyS79Eb92Ug` ✓ CLASSIFIED 2026-04-24

- **URL** : https://www.youtube.com/watch?v=DyS79Eb92Ug
- **Titre** : "Trading LIVE with the BEST Scalper in the World (PERFECT Accuracy)"
- **Durée** : 141.6 min (8498 s) — conférence live trading NY session
- **Statut** : `CLASSIFIED`
- **Tag terminal** : **`PEDAGOGICAL_ONLY`**
- **Famille** : orderflow-scalping (non-ICT, non-MASTER)
- **Étape A (ingest)** : DONE — `raw_transcript.txt` (3668 lignes) + `metadata.json`.
- **Étape B (transcript résumé)** : DONE — `notes.md` (thèse / mécanisme / TF / fertilité / stérilité / honnêteté).
- **Étape C (dedupe)** : DONE — pas de DUPLICATE. Famille orderflow NQ (footprint+CVD+aggressor side+range bars) ≠ ICT/MASTER/SPY/QQQ. Aucun chevauchement 10 data points négatifs.
- **Étape D (classify)** : DONE — 4/4 codability NON (pas de CVD/L2/footprint/range bars sur DexterioBOT, pas de règle fermée extractible, discrétionnaire complet). Q5 = not a playbook. Cas §20 A (infra gap massif).
- **Étape E (tag terminal)** : DONE — `PEDAGOGICAL_ONLY`. Système discrétionnaire expert "years of tape reading" (citation auteur), capital-gated ($1M+ NQ), stack data inaccessible. Valeur documentaire = structure session NY (expansion/rebalance/power hour) + gestion risque asymétrique. Aucune action backlog.
- **Artefacts** : `videos/DyS79Eb92Ug/raw_transcript.txt` + `videos/DyS79Eb92Ug/metadata.json` + `videos/DyS79Eb92Ug/notes.md` + `videos/DyS79Eb92Ug/true.md`

### Vidéo #2 — `PlsHO33j6B8` ✓ CLASSIFIED 2026-04-24

- **URL** : https://www.youtube.com/watch?v=PlsHO33j6B8
- **Titre** : "Advanced Imbalance Concepts (NDOG / NWOG / NCOG / BPR)"
- **Durée** : 23.1 min (1386 s)
- **Statut** : `CLASSIFIED`
- **Tag terminal** : **`DUPLICATE`**
- **Famille** : ICT-A (imbalance / FVG variants)
- **Étape A (ingest)** : DONE — `raw_transcript.txt` (571 lignes) + `metadata.json`.
- **Étape B (transcript résumé)** : DONE — `notes.md` (NDOG/NWOG/NCOG/BPR mécanismes / fertilité / stérilité / honnêteté).
- **Étape C (dedupe)** : DONE — `DUPLICATE`. NDOG/NWOG/BPR = variantes famille imbalance déjà dans MASTER_legacy (MASTER_FINAL.txt, MASTER_PLAYBOOK_MAP.md, fair_value_gap détecteur). NCOG auto-disqualifié par l'auteur. Aucune nouveauté §10 r11.
- **Étape D (classify)** : DONE — Q1 PARTIEL / Q2 OUI / Q3 NON / Q4 Cas C probable / Q5 NON (pédagogique). DUPLICATE confirmé.
- **Étape E (tag terminal)** : DONE — `DUPLICATE` per R3 §0.A.bis. Pointer : MASTER_FINAL.txt + MASTER_PLAYBOOK_MAP.md + fair_value_gap.py + verdicts Aplus_03 (4 data points négatifs imbalance isolé). NDOG/NWOG comme draws candidates dans tp_resolver différé R5.
- **Artefacts** : `videos/PlsHO33j6B8/raw_transcript.txt` + `videos/PlsHO33j6B8/metadata.json` + `videos/PlsHO33j6B8/notes.md` + `videos/PlsHO33j6B8/true.md`

### Vidéo #3 — `4sRDnVmLcMk` ✓ CLASSIFIED 2026-04-24

- **URL** : https://www.youtube.com/watch?v=4sRDnVmLcMk
- **Titre** : "Path to Profitability: Inverse Fair Value Gaps Explained"
- **Durée** : 22.5 min (1352 s)
- **Statut** : `CLASSIFIED`
- **Tag terminal** : **`DUPLICATE`**
- **Famille** : ICT-A (IFVG / FVG inversion)
- **Étape A (ingest)** : DONE — `raw_transcript.txt` (535 lignes) + `metadata.json`.
- **Étape B (transcript résumé)** : DONE — `notes.md` (IFVG mécanisme / stacked FVG stack_resolve / fertilité / stérilité / lien Aplus_03).
- **Étape C (dedupe)** : DONE — `DUPLICATE`. IFVG = cœur de Aplus_03_IFVG_Flip_5m déjà instancié en 4 versions (R.3/v2/α''/ε) avec verdicts négatifs convergents. Concept dans MASTER_legacy. Aucune nouveauté §10 r11.
- **Étape D (classify)** : DONE — Q1 OUI / Q2 OUI / Q3 OUI hist. mais pas de nouvelle kill rule / Q4 Cas C très probable / Q5 NON (confluence pas playbook). DUPLICATE confirmé.
- **Étape E (tag terminal)** : DONE — `DUPLICATE` per R3 §0.A.bis. Pointer : MASTER_FINAL.txt + MASTER_PLAYBOOK_MAP.md + fair_value_gap.py + verdicts Aplus_03 R.3/v2/aplus04_v2_alpha_pp/aplus04_v2_epsilon (4 data points négatifs convergents). Knob stack_resolve différé R5.
- **Artefacts** : `videos/4sRDnVmLcMk/raw_transcript.txt` + `videos/4sRDnVmLcMk/metadata.json` + `videos/4sRDnVmLcMk/notes.md` + `videos/4sRDnVmLcMk/true.md`

### Vidéo #4 — `joe_XTCn5Bs`

- **URL** : https://www.youtube.com/watch?v=joe_XTCn5Bs
- **Statut** : `PENDING_INGEST`
- **Étapes A-E** : non-démarré.
- **Notes user** : batch initial 2026-04-22.
- **Famille pressentie** : à déterminer.
- **Doublons/thèses réfutées pré-flag** : idem §pré-checks globaux.

### Vidéo #5 — `7dTQA0t8SH0`

- **URL** : https://www.youtube.com/watch?v=7dTQA0t8SH0
- **Statut** : `PENDING_INGEST`
- **Étapes A-E** : non-démarré.
- **Notes user** : batch initial 2026-04-22.
- **Famille pressentie** : à déterminer.
- **Doublons/thèses réfutées pré-flag** : idem §pré-checks globaux.

### Vidéo #6 — `L4xz2o23aPQ`

- **URL** : https://www.youtube.com/watch?v=L4xz2o23aPQ
- **Statut** : `PENDING_INGEST`
- **Étapes A-E** : non-démarré.
- **Notes user** : batch initial 2026-04-22.
- **Famille pressentie** : à déterminer.
- **Doublons/thèses réfutées pré-flag** : idem §pré-checks globaux.

### Vidéo #7 — `52nxvJKM57U`

- **URL** : https://www.youtube.com/watch?v=52nxvJKM57U
- **Statut** : `PENDING_INGEST`
- **Étapes A-E** : non-démarré.
- **Notes user** : batch initial 2026-04-22.
- **Famille pressentie** : à déterminer.
- **Doublons/thèses réfutées pré-flag** : idem §pré-checks globaux.

### Vidéo #8 — `ironJFzNBic`

- **URL** : https://www.youtube.com/watch?v=ironJFzNBic
- **Statut** : `PENDING_INGEST`
- **Étapes A-E** : non-démarré.
- **Notes user** : batch initial 2026-04-22.
- **Famille pressentie** : à déterminer.
- **Doublons/thèses réfutées pré-flag** : idem §pré-checks globaux.

### Vidéo #9 — `TEp3a-7GUds`

- **URL** : https://www.youtube.com/watch?v=TEp3a-7GUds
- **Statut** : `PENDING_INGEST`
- **Étapes A-E** : non-démarré.
- **Notes user** : batch initial 2026-04-22.
- **Famille pressentie** : à déterminer.
- **Doublons/thèses réfutées pré-flag** : idem §pré-checks globaux.

### Vidéo #10 — `wzq2AMsoJKY`

- **URL** : https://www.youtube.com/watch?v=wzq2AMsoJKY
- **Statut** : `PENDING_INGEST`
- **Étapes A-E** : non-démarré.
- **Notes user** : batch initial 2026-04-22.
- **Famille pressentie** : à déterminer.
- **Doublons/thèses réfutées pré-flag** : idem §pré-checks globaux.

### Vidéo #11 — `vlnNPFu4rEQ`

- **URL** : https://www.youtube.com/watch?v=vlnNPFu4rEQ
- **Statut** : `PENDING_INGEST`
- **Étapes A-E** : non-démarré.
- **Notes user** : batch initial 2026-04-22.
- **Famille pressentie** : à déterminer.
- **Doublons/thèses réfutées pré-flag** : idem §pré-checks globaux.

### Vidéo #12 — `FJch02ucIO8`

- **URL** : https://www.youtube.com/watch?v=FJch02ucIO8
- **Statut** : `PENDING_INGEST`
- **Étapes A-E** : non-démarré.
- **Notes user** : batch initial 2026-04-22.
- **Famille pressentie** : à déterminer.
- **Doublons/thèses réfutées pré-flag** : idem §pré-checks globaux.

### Vidéo #13 — `pKIo-aVic-c`

- **URL** : https://www.youtube.com/watch?v=pKIo-aVic-c
- **Statut** : `PENDING_INGEST`
- **Étapes A-E** : non-démarré.
- **Notes user** : batch initial 2026-04-22.
- **Famille pressentie** : à déterminer.
- **Doublons/thèses réfutées pré-flag** : idem §pré-checks globaux.

### Vidéo #14 — `BdBxXKGWVjk`

- **URL** : https://www.youtube.com/watch?v=BdBxXKGWVjk
- **Statut** : `PENDING_INGEST`
- **Étapes A-E** : non-démarré.
- **Notes user** : batch initial 2026-04-22.
- **Famille pressentie** : à déterminer.
- **Doublons/thèses réfutées pré-flag** : idem §pré-checks globaux.

---

## Sous-batch 2 — Extension 2026-04-23 (5 vidéos user-added)

**Contexte user** : "strat des guru téléchargés / explication backtest des strats d'essai / conférence 2H par scalper réputé / recherche d'hedge". Source message user 2026-04-23.

**Dédup pré-ingest** : URLs source user contenaient `DyS79Eb92Ug` 2× (paramètres `?si=uz0ZRCbQDEqtpfiP` et `?si=ISqwvgKd4ViaAbwr` = YouTube tracking params differing, video_id identique). **Cette video_id existe déjà au sous-batch 1 ligne #1 → les 2 occurrences skip** (doublon intra-batch user + inter-batch batch initial). 5 URLs uniques retenues.

### Vidéo #15 — `s9HV_jyeUDk`

- **URL** : https://www.youtube.com/watch?v=s9HV_jyeUDk
- **Statut** : `PENDING_INGEST`
- **Étape A (ingest)** : non-démarré. Cible artefacts : `videos/s9HV_jyeUDk/raw_transcript.txt` + `videos/s9HV_jyeUDk/metadata.json`. Vérifier duration à l'ingest — si >90min possiblement la "conférence 2H par scalper réputé" mentionnée par user (à flag).
- **Étape B (transcript résumé)** : non-démarré. Cible `videos/s9HV_jyeUDk/notes.md`.
- **Étape C (dedupe)** : non-démarré. Pré-flag spécifique : si la thèse chevauche une des 6 MASTER families déjà instanciées (A-F) ou un des 10 data points négatifs → `DUPLICATE`.
- **Étape D (classify)** : non-démarré. Checklist §0.A étape 3+4 complète.
- **Étape E (tag terminal)** : non-démarré.
- **Notes user** : "strat des guru téléchargés / backtest trial explain / conf 2H scalper / hedge research" — bucket user-added 2026-04-23, association fine vidéo↔contexte à effectuer étape B.
- **Famille pressentie** : à déterminer étape B (candidates larges selon contexte user : scalping stateful, hedge/arb, strat-backtest explain = pédagogique possible).
- **Doublons/thèses réfutées pré-flag** : idem §pré-checks globaux. Spécifique hedge research : si thèse = stat-arb cointégration paire US ETFs intraday → évaluer contre Avellaneda-Lee §0.5bis entrée #3 (pivote univers) — si même univers 2-asset SPY/QQQ intraday 5m → `DUPLICATE` pointer data point #6. Si univers enrichi (multi-ETF / PCA / multi-leg) → potentiel `KEEP_PLAYBOOK_CANDIDATE` §10 r11 (nouvelle hypothèse structurelle) mais bloqué R5 (amendement Niveau 3 requis).

### Vidéo #16 — `6ao3uXE5KhU`

- **URL** : https://www.youtube.com/watch?v=6ao3uXE5KhU
- **Statut** : `PENDING_INGEST`
- **Étape A (ingest)** : non-démarré. Cible artefacts : `videos/6ao3uXE5KhU/raw_transcript.txt` + `videos/6ao3uXE5KhU/metadata.json`. Vérifier duration.
- **Étape B (transcript résumé)** : non-démarré. Cible `videos/6ao3uXE5KhU/notes.md`.
- **Étape C (dedupe)** : non-démarré.
- **Étape D (classify)** : non-démarré.
- **Étape E (tag terminal)** : non-démarré.
- **Notes user** : bucket user-added 2026-04-23, contexte idem #15.
- **Famille pressentie** : à déterminer.
- **Doublons/thèses réfutées pré-flag** : idem §pré-checks globaux + pré-flag spécifique hedge.

### Vidéo #17 — `W722Ca8tS7g`

- **URL** : https://www.youtube.com/watch?v=W722Ca8tS7g
- **Statut** : `PENDING_INGEST`
- **Étape A (ingest)** : non-démarré. Cible artefacts : `videos/W722Ca8tS7g/raw_transcript.txt` + `videos/W722Ca8tS7g/metadata.json`. Vérifier duration.
- **Étape B (transcript résumé)** : non-démarré. Cible `videos/W722Ca8tS7g/notes.md`.
- **Étape C (dedupe)** : non-démarré.
- **Étape D (classify)** : non-démarré.
- **Étape E (tag terminal)** : non-démarré.
- **Notes user** : bucket user-added 2026-04-23, contexte idem #15.
- **Famille pressentie** : à déterminer.
- **Doublons/thèses réfutées pré-flag** : idem §pré-checks globaux + pré-flag spécifique hedge.

### Vidéo #18 — `ATWyVRbrDvs`

- **URL** : https://www.youtube.com/watch?v=ATWyVRbrDvs
- **Statut** : `PENDING_INGEST`
- **Étape A (ingest)** : non-démarré. Cible artefacts : `videos/ATWyVRbrDvs/raw_transcript.txt` + `videos/ATWyVRbrDvs/metadata.json`. Vérifier duration — user mentionne "conférence 2H par scalper réputé" : si duration >90-120min cette vidéo est candidate forte pour ce bucket contexte.
- **Étape B (transcript résumé)** : non-démarré. Cible `videos/ATWyVRbrDvs/notes.md`. Si confirmé conf 2H scalper : résumé ≤300 mots concentrer sur règles fermées extractibles (entry / exit / sizing / management) vs pédagogie générale — conf longue = typiquement PEDAGOGICAL_ONLY sauf si protocole documentable fermé.
- **Étape C (dedupe)** : non-démarré.
- **Étape D (classify)** : non-démarré.
- **Étape E (tag terminal)** : non-démarré. Si conf 2H = pédagogique générale sans règles fermées extractibles → `PEDAGOGICAL_ONLY` (workflow §0.A étape 4bis tableau routing : "démonstration conceptuelle").
- **Notes user** : bucket user-added 2026-04-23, candidate probable pour "conf 2H par scalper réputé".
- **Famille pressentie** : scalping intraday si protocole fermé, sinon pédagogique.
- **Doublons/thèses réfutées pré-flag** : idem §pré-checks globaux. Si scalping 1m/5m SPY/QQQ sans D/4H bias enforcé + sans liquidity-targeting + sans 1m confirm = `LOW_SIGNAL` (vocab-borrowing R4, cf Phase D.2 audit 0/7 MASTER faithful). Si calibration single-signal tuning seuils → auto-`DUPLICATE` pointer Morning_Trap / Liquidity_Sweep / BOS_Scalp asymptoted E[R]<0.

### Vidéo #19 — `fIEwVmJJ06s`

- **URL** : https://www.youtube.com/watch?v=fIEwVmJJ06s
- **Statut** : `PENDING_INGEST`
- **Étape A (ingest)** : non-démarré. Cible artefacts : `videos/fIEwVmJJ06s/raw_transcript.txt` + `videos/fIEwVmJJ06s/metadata.json`. Vérifier duration.
- **Étape B (transcript résumé)** : non-démarré. Cible `videos/fIEwVmJJ06s/notes.md`.
- **Étape C (dedupe)** : non-démarré.
- **Étape D (classify)** : non-démarré.
- **Étape E (tag terminal)** : non-démarré.
- **Notes user** : bucket user-added 2026-04-23, contexte idem #15.
- **Famille pressentie** : à déterminer.
- **Doublons/thèses réfutées pré-flag** : idem §pré-checks globaux + pré-flag spécifique hedge.

---

## Synthèse provisoire (sera finalisée dans `MASTER_EXPANSION_BATCH_01_SUMMARY.md` post-étape E de tous les vidéos)

**Dernière mise à jour** : 2026-04-24 (batch de traitement #1 complet : vidéos #1-#3)

| Métrique | Valeur actuelle |
|---|---:|
| Total vidéos batch | 19 |
| Sous-batch 1 (2026-04-22) | 14 |
| Sous-batch 2 extension (2026-04-23) | 5 |
| URLs user-source dédupliquées vers #1 | 2 (`DyS79Eb92Ug` × 2 = déjà #1) |
| `PENDING_INGEST` | **16** |
| `INGESTED` (post-étape A) | 0 |
| `TRANSCRIBED` (post-étape B) | 0 |
| `CLASSIFIED` (post-étape D-E) | **3** (#1 #2 #3) |
| `KEEP_PLAYBOOK_CANDIDATE` (post-étape E) | 0 |
| `KEEP_OVERLAY` | 0 |
| `KEEP_FEATURE` | 0 |
| `KEEP_MANAGEMENT` | 0 |
| `PEDAGOGICAL_ONLY` | **1** (#1 `DyS79Eb92Ug`) |
| `DUPLICATE` | **2** (#2 `PlsHO33j6B8`, #3 `4sRDnVmLcMk`) |
| `LOW_SIGNAL` | 0 |

## Prochaine action workflow §0.A.bis (pickable entre runs §0.9 route principale)

Le CEO peut traiter §0.A.bis **par batches de 3 vidéos** entre runs longs, per R6 non-dispersion. **Défaut autonome CEO** : continuer §0.9 route principale (gate pré-backlog §0.7 → §0.5bis entrée #1) ET §0.A.bis en parallèle par lots de 3.

**Batch 1 de traitement — COMPLET 2026-04-24** : vidéos #1-#3 (`DyS79Eb92Ug` PEDAGOGICAL_ONLY, `PlsHO33j6B8` DUPLICATE, `4sRDnVmLcMk` DUPLICATE). 0 KEEP_PLAYBOOK_CANDIDATE.
**Batch 2 — SUIVANT** : #4-#6 (`joe_XTCn5Bs`, `7dTQA0t8SH0`, `L4xz2o23aPQ`).
**Batch 3** : #7-#9 (`52nxvJKM57U`, `ironJFzNBic`, `TEp3a-7GUds`).
**Batch 4** : #10-#12 (`wzq2AMsoJKY`, `vlnNPFu4rEQ`, `FJch02ucIO8`).
**Batch 5** : #13-#14 (sous-batch 1 fin) + #15 (sous-batch 2 début).
**Batch 6** : #16-#18 (#18 candidate conf 2H scalper, flag duration à étape A).
**Batch 7** : #19 (sous-batch 2 fin) → livrable final `MASTER_EXPANSION_BATCH_01_SUMMARY.md` mis à jour.

Livrable INDEX.md **à jour après chaque batch de 3 vidéos** per plan §0.A.bis R6.
