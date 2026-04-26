# Dossier — VWAP_Bounce_5m solo 12w (Leg 2.2 Quarantine PROMOTE)

**Source** : CEO arbre §0.5 Leg 2 — candidats CLAUDE.md "quarantine" E[R]>0 sur n=3-11 : **besoin data, pas calibration**.

---

## Pièce A — fiche d'identité

| Champ | Valeur |
|---|---|
| Nom canonique | VWAP_Bounce_5m (baseline playbooks.yml L1680) |
| Version solo-run | 12w corpus expansion v1 |
| Famille | SCALP mean-reversion (VWAP bounce + RSI extreme) |
| Type | Stateless 5m detector (required_signals: VWAP@5m) |
| Instruments | SPY, QQQ |
| Timeframes | 5m setup + 5m confirmation (no 1m) |
| Direction | both (RSI<35 long, RSI>65 short) |
| Régime visé | toutes htf_bias + day_type confondus (bruit permis — volatility libre) |
| Statut initial | quarantine (CLAUDE.md — E[R]>0 sur n=3-11 à valider sur corpus élargi) |
| Auteur | baseline playbook v0 (non-ICT, quant mean-rev) |
| Dernière review | 2026-04-22 (Leg 2.2 démarrage) |

---

## Pièce B — hypothèse formelle

### Thèse
Sur un touch VWAP 5m dans la session NY (09:35-11:00 et 14:00-15:30), un RSI extreme (<35 ou >65) indique un pullback opportune vers la moyenne pondérée volume. L'entrée MARKET au close du pattern capture la mean-reversion vers VWAP mid-line sur TP 1.5:1.

### Mécanisme
VWAP = prix moyen pondéré volume institutionnel intraday. Les algos et market-makers s'ancrent à VWAP pour rebalancer. RSI oversold/overbought + VWAP touch = convergence technique + flow institutionnel mean-rev. TP serré (1.5:1) exploite la règle de retour statistique sans overstay.

### Conditions de fertilité
- Session NY (pas de préférence étroite — deux fenêtres 09:35-11:00 + 14:00-15:30)
- RSI < 35 OR RSI > 65 (extreme)
- VWAP@5m touch géométrique
- Pas de contrainte ADX, htf_bias ou day_type (accepte toutes conditions)

### Conditions de stérilité
- Hors sessions (lunch 12-13:30 non inclus dans time_windows)
- VWAP non touché
- RSI neutre 35-65

### Risque principal (falsifiabilité)
Si **E[R]_gross ≤ 0 sur n ≥ 20 trades 12 weeks**, l'hypothèse mean-rev VWAP en 2025 est réfutée. Alternatives plausibles : (a) RSI 35/65 pas assez extreme (seuils 25/75 pourraient être requis), (b) TP 1.5:1 plafonne sur mean-rev qui extend, (c) pas d'edge du tout.

---

## Pièce C — spécification d'état décisionnel

**Stateless** (pas de tracker) :

1. **Détection setup** : bar 5m fermée dans time_windows + VWAP@5m required_signal émis + RSI extreme.
2. **Entry** : MARKET order au `pattern_close`, confirmation_tf=5m (pas de 1m confirm).
3. **SL FIXED** : `pattern_extreme` ± 1 tick.
4. **TP fixed RR** : 1.5:1.
5. **Invalidation** : SL touché OR max_duration_minutes=40 OR EOD.

---

## Pièce D — dépendances moteur + audit infra

| Brique | Status | Fichier |
|---|---|---|
| VWAP 5m signal | ✓ (engine sanity v2 B5) | [backend/engines/patterns/vwap_bounce.py](backend/engines/patterns/vwap_bounce.py) |
| RSI computation | ✓ (engine sanity v2 B6) | [backend/engines/features/rsi.py](backend/engines/features/rsi.py) |
| FIXED SL logic | ✓ | [backend/engines/execution/stop_loss.py](backend/engines/execution/stop_loss.py) |
| Fixed RR TP | ✓ | [backend/engines/execution/take_profit.py](backend/engines/execution/take_profit.py) |
| time_windows gate | ✓ | [backend/engines/execution/session_gate.py](backend/engines/execution/session_gate.py) |

**Résultat audit** : `full infra exists` — aucun chantier requis.

---

## Pièce E — YAML d'exécution

Baseline **as-is** (playbooks.yml L1680). Pas d'override. Solo-run via `--calib-allowlist VWAP_Bounce_5m`.

---

## Pièce F — tests

Aucun test dédié (baseline déjà couvert par engine_sanity_v2 B5/B6).

---

## Pièce G — protocole de run

Corpus identique à Leg 2.1 — 12 semaines jun-nov 2025 (voir [dossier 2.1](../ifvg_5m_sweep_solo_12w/dossier.md) Pièce G table).

### Mode de run
- AGGRESSIVE + ALLOW_ALL_PLAYBOOKS + `--calib-allowlist VWAP_Bounce_5m`
- `--no-relax-caps` (caps actives)
- Fill model : Ideal

### Commande canonique par semaine
```bash
cd backend && .venv/bin/python scripts/run_mini_lab_week.py \
  --start <YYYY-MM-DD> --end <YYYY-MM-DD> \
  --label vwap_bounce_5m_solo_12w_<week_label> \
  --output-parent vwap_bounce_5m_solo_12w \
  --no-respect-allowlists --no-relax-caps \
  --calib-allowlist VWAP_Bounce_5m
```

---

## Pièce H — kill rules pré-écrites

### Gate Leg 2 cohort (plan §0.5)
> Kill rule cohort : si 0/3 passe E[R] > 0.05R gross + n ≥ 20 → Leg 3

### Kill rules individuelles VWAP_Bounce_5m 12w
1. **n < 20 trades sur 12 semaines** → ARCHIVED (signal rare)
2. **E[R]_gross ≤ 0** → ARCHIVED (Cas §20 C)
3. **E[R]_gross ∈ [0, +0.05R] ET n ≥ 20** → MARGINAL, pas promotion
4. **E[R]_gross > 0.05R ET n ≥ 20** → PASS Leg 2 criterion

---

**Statut** : SPECIFIED_READY.
