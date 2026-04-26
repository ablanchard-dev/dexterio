# Dossier — Aplus_02 Family F Premarket v1 (Leg 3)

**Source** : CEO arbre §0.5 Leg 3 — 6e et dernière MASTER family non-testée. Kill rules template Sprint 1.

---

## Pièce A — fiche d'identité

| Champ | Valeur |
|---|---|
| Nom canonique | Aplus_02_Premarket_v1 |
| Version | v1 (Leg 3.x) |
| Famille | MASTER Family F Premarket (sweep prior-day RTH range → 5m BOS → 1m confirm en fenêtre premarket NY 04:00-09:30 ET) |
| Type | Stateless 5m detector + 1m confirmation (réutilise SWEEP@5m + BOS@5m existants) |
| Instruments | SPY, QQQ |
| Timeframes | 5m setup + 1m confirmation |
| Direction | both (contrarian sur le sweep) |
| Régime visé | trend + manipulation_reversal, htf_bias bullish/bearish allowed (pas de range) |
| Statut initial | SPECIFIED → SPECIFIED_READY (full infra exists, SWEEP+BOS+timefilter suffisants pour v1) |
| Auteur | CEO autonomous §0.5 Leg 3 (MASTER Family F pragmatic v1) |
| Dernière review | 2026-04-22 (Leg 3 démarrage) |

---

## Pièce B — hypothèse formelle

### Thèse
Dans la fenêtre premarket NY 04:00-09:30 ET, un sweep 5m d'un niveau structurel (prior-day RTH high ou low, ou swing_k3 visible sur 5m) suivi d'un BOS 5m dans la direction contraire capture une continuation pré-open. La thin liquidity premarket rend les sweeps plus propres structurellement (stops drained sur volume léger) tandis que l'afflux volume pré-open valide la continuation.

### Mécanisme
Premarket liquidity ~10-20% du RTH → les sweeps de niveaux structurels (overnight range H/L, prior-day H/L, swing 5m) drainent les stops des participants RTH encore absents. Le BOS 5m subséquent dans la direction opposée signale un repositionnement smart money avant l'open 09:30. 1m confirm réduit les faux BOS bruités typiques premarket.

### Conditions de fertilité
- Fenêtre premarket 04:00-09:30 ET
- SWEEP@5m détecté (signal infra existant)
- BOS@5m dans direction contraire au sweep
- htf_bias bullish OU bearish (éviter range)
- ADX ≥ 20
- pattern_confirmations ≥ 1

### Conditions de stérilité
- Hors fenêtre premarket
- Range pur (ADX < 20)
- htf_bias neutral / unknown
- Volume premarket <5% RTH moyenne (holiday/weekend reduced hours)

### Risque principal (falsifiabilité)
Si **E[R]_gross ≤ 0 sur n ≥ 20 trades smoke+éventuelle 4w**, l'hypothèse Family F premarket v1 est réfutée. **Prior fort de l'échec** : 5 autres MASTER families testées (A, B, C, D, E) toutes négatives ou structurellement rares. Aplus_01 Family A full donne 1 emit / 5 sessions × 2 symbols en RTH. Premarket fenêtre 5h30 + thin liquidity + signaux SWEEP+BOS infra existants suggèrent **Cas B dominant probable** (n<10 structurellement rare sur smoke 1 semaine). Si n=0 ou 1-3, hypothèse non-réfutée mais non-calibrable — même issue que Aplus_01 v1.

---

## Pièce C — spécification d'état décisionnel

**Stateless** (réutilise infra SWEEP@5m + BOS@5m) :

1. **Gate time_window** : bar 5m fermée dans window 04:00-09:30 ET.
2. **Détection setup** : SWEEP@5m required_signal + BOS@5m required_signal (direction contraire au sweep).
3. **Gate context** : htf_bias allowed + ADX ≥ 20 + day_type allowed.
4. **Entry** : MARKET ou LIMIT à `bos_close` ou `sweep_extreme_retest`, confirmation_tf=1m.
5. **SL swing** : recent_swing_k3 ± 3 ticks (padding plus large — bruit premarket).
6. **TP schéma α''** : `tp_logic: liquidity_draw swing_k3 significant` + ceiling 3.0 + structure_alignment k3 (cohérent plan §0.5 3.4).
7. **Invalidation** : SL touché OR EOD OR max_duration_minutes=60 (sortie pré-open si non tenu).

---

## Pièce D — dépendances moteur + audit infra

| Brique | Status | Fichier |
|---|---|---|
| SWEEP@5m detector | ✓ (engine sanity v2 B3) | [backend/engines/patterns/sweep.py](backend/engines/patterns/sweep.py) |
| BOS@5m detector | ✓ (engine sanity v2 B4) | [backend/engines/patterns/bos.py](backend/engines/patterns/bos.py) |
| 1m confirmation gate | ✓ | [backend/engines/execution/entry_gates.py](backend/engines/execution/entry_gates.py) |
| Swing SL logic (k3) | ✓ | [backend/engines/execution/stop_loss.py](backend/engines/execution/stop_loss.py) |
| TP resolver liquidity_draw swing_k3 | ✓ (19/19 tests, α'' validé Aplus_03_v2) | [backend/engines/execution/tp_resolver.py](backend/engines/execution/tp_resolver.py) |
| structure_alignment k3 gate | ✓ (directional_change k3) | [backend/engines/features/directional_change.py](backend/engines/features/directional_change.py) |
| time_windows gate | ✓ | [backend/engines/execution/session_gate.py](backend/engines/execution/session_gate.py) |
| patterns_config PREMARKET_NY alias | ✓ (ajouté 2026-04-22 "04:00-09:30") | [backend/knowledge/patterns_config.yml](backend/knowledge/patterns_config.yml) |

**Résultat audit** : `full infra exists` — aucun chantier requis, aucun tracker nouveau, aucun détecteur neuf.

---

## Pièce E — YAML d'exécution

Nouveau playbook `Aplus_02_Premarket_v1` dans [playbooks.yml](backend/knowledge/playbooks.yml) ajouté en fin de fichier. Pas de campaign override — playbook baseline avec schéma α''.

---

## Pièce F — tests

Aucun test dédié (baseline patterns SWEEP + BOS déjà couverts par engine_sanity_v2 B3/B4 ; tp_resolver α'' couvert 19 tests ; directional_change k3 couvert). v1 = smoke driven sans tests unitaires nouveaux (§19.3 budget — écrire tests après SMOKE_PASS si applicable).

---

## Pièce G — protocole de run

### Smoke nov_w4 seul (2025-11-17 → 2025-11-21)

### Mode de run
- AGGRESSIVE + `RISK_EVAL_ALLOW_ALL_PLAYBOOKS=true` + `--calib-allowlist Aplus_02_Premarket_v1`
- `--no-relax-caps` (caps actives)
- Fill model : Ideal (baseline smoke — exploration avant realistic)

### Commande canonique
```bash
cd backend && .venv/bin/python scripts/run_mini_lab_week.py \
  --start 2025-11-17 --end 2025-11-21 \
  --label aplus02_premarket_v1_smoke_nov_w4 \
  --output-parent aplus02_premarket_family_f \
  --no-respect-allowlists --no-relax-caps \
  --calib-allowlist Aplus_02_Premarket_v1
```

---

## Pièce H — kill rules pré-écrites (AVANT smoke)

### Gate Leg 3 smoke (plan §0.5)
Kill rules template Sprint 1 :

1. **n < 10 trades sur smoke 1 semaine** → **ARCHIVED (Cas B §20, signal structurellement rare, non-calibrable)** + Leg 4 automatique
2. **peak_R p80 < 1R** → **ARCHIVED (Cas C §20, edge absent, signal plafonné)** + Leg 4
3. **E[R]_gross ≤ 0** → **ARCHIVED (Cas C §20, edge absent)** + Leg 4
4. **n ≥ 10 ET peak_R p80 ≥ 1R ET E[R]_gross > 0** → extension 4w canonical Stage 1 (gate E[R] > 0.05R gross + n ≥ 15 + peak_R p60 > 0.5R)

### Décision terminale
- 1+ kill rule atteinte → ARCHIVED terminal + progression automatique Leg 4
- 0 kill rule atteinte → Stage 1 4w canonical gate

---

**Statut** : SPECIFIED_READY (full infra exists, prêt pour exécution).
