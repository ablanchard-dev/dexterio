# Stat Arb SPY-QQQ v2 — dossier (Leg 4.1)

> Plan §0.5 Leg 4.1 — **réouverture légale §10 règle 11** après Sprint 3 v1 SMOKE_FAIL.
> **Changement structurel vs v1** : cointégration calculée sur **close daily rolling 60 jours** (non plus intraday 200 bars 5m). Hypothèse : la coint intraday EG était trop restrictive (1/59 fenêtres PASS dans v1 → gate étouffait le signal). La relation SPY-QQQ est structurellement stable en TF **daily** ; on utilise le daily coint comme **regime gate** pour autoriser le timing d'entrée intraday 5m via z-score.
> Pièces A–H pré-rédigées (§19 phase B) avant code. Kill rules pré-écrites (pièce H) non re-interprétables post-hoc.

---

## Pièce A — fiche d'identité

| Champ | Valeur |
|---|---|
| Nom canonique | `Stat_Arb_SPY_QQQ_v2` |
| Version | `v2` |
| Famille | non-ICT — stat arb / mean reversion sur spread coïntégré, gate régime daily |
| Type | Multi-leg (2 jambes simultanées, beta-neutral) — stateful per-pair, **régime daily gate** per trading day |
| Instruments | SPY (jambe 1) + QQQ (jambe 2). Pair fixe. |
| Timeframes | **Daily (cointégration gate) + 5m (z-score armement + exécution)** |
| Direction | both : `long_spread` (long SPY + short QQQ × β) si z < -seuil ; `short_spread` (short SPY + long QQQ × β) si z > +seuil |
| Régime visé | NY session 09:30–15:00 ET, **seulement si daily coint PASS** ce jour |
| Statut initial | `SPECIFIED_READY` (full infra D1+D2 existe — cf pièce D) |
| Auteur / origine | Plan §0.5 Leg 4.1 + note §10 Sprint 3 verdict "daily TF serait le bon gate" |
| Dernière review | 2026-04-22 (Leg 3 ARCHIVED → démarrage auto Leg 4.1) |

---

## Pièce B — hypothèse formelle (5 sous-blocs, non négociables)

### Thèse
Le spread normalisé entre SPY et QQQ est **mean-reverting intraday 5m** **conditionnellement** à la stabilité structurelle de leur relation en **daily** (test Engle-Granger p<0.05 sur fenêtre 60 jours rolling calculé à la clôture du jour précédent). Quand cette relation daily est coint PASS, les déviations intraday |z| > 2.0σ reviennent vers 0 suffisamment souvent pour générer un edge tradable beta-neutral.

### Mécanisme
Reprise v1 : SPY et QQQ partagent un sous-jacent économique commun (US large-cap) donc leurs returns sont coïntégrés. **Ajout v2** : la coïntégration est une propriété **structurelle multi-jour**, pas micro-structurelle intraday. Le test EG intraday 200 bars 5m capture du bruit (seulement 1/59 fenêtres PASS dans v1 = trop strict et non-informatif). Le test EG daily 60 bars capture la relation vraie de fond (daily PASS la plupart des jours en régime normal, FAIL pendant divergences structurelles — rotation tech/value, stress sectoriel, regime change). Le gate daily filtre les jours où la structure est cassée ; les autres jours, le signal intraday 5m z-score peut opérer.

### Conditions de fertilité
- **Daily EG PASS** (p < 0.05 sur close daily rolling 60 jours, calculé à la clôture du jour précédent).
- Liquidité abondante sur les 2 jambes (NY session, pas de halts).
- Volatilité spread modérée — éviter les régimes de blow-out (z > 4σ → souvent regime change).

### Conditions de stérilité (ne pas trader)
- **Daily EG FAIL** (p ≥ 0.05 sur 60 jours rolling). Gate régime OFF pour toute la journée intraday. **C'est le changement structurel clé vs v1.**
- Lunch 12:00–13:00 ET (liquidité fragmentée).
- News window ±5min (FOMC, CPI, NFP, earnings tech géants).
- z-score déjà > 3.0σ au moment de l'armement (déjà en territoire blow-out).
- Lock-out post-stop : 30 min après un SL pour éviter de retrader la même divergence.

### Risque principal (= falsifiabilité)
**L'hypothèse est fausse si** l'un des cas suivants sur smoke nov_w4 (5 sessions) :
- **Daily EG PASS trop rare** : 0–1 jours sur 5 avec gate ON → Cas A (infra) ou B (structurellement rare) §20. Fenêtre 60j trop stricte ou régime nov_w4 atypique.
- **Daily EG PASS suffisant (≥ 3 jours) mais n < 10 trades émis** : Cas B §20. Le gate régime ne compense pas la rareté de z>2σ intraday.
- **n ≥ 10 mais E[R] gross ≤ 0** ET `mean_rev_rate` < 50 % : Cas C §20. Le daily coint gate ne prédit pas la mean-reversion intraday. Hypothèse réfutée.

**Prior fort d'échec** (honnêteté cross-playbook) :
- v1 même paire, 5m TF, n=8, E[R]=-0.179 : mean-rev rate 25 %. Les 2 TP produisent les pires pertes (−0.47R, −0.94R).
- Peak_R p80 v1 = 0.15 : le spread n'a pas d'amplitude exploitable dans la configuration 5m.
- **Le gate daily change le "quand" mais pas le "comment"** — si le chemin prix entre z>2σ et z→0.5σ garde ses excursions adverses catastrophiques, v2 répétera la pathologie.

---

## Pièce C — spécification d'état décisionnel

| Étape | Description |
|---|---|
| **Gate régime (daily)** | À la clôture de chaque jour de bourse, calculer EG test sur log(SPY_daily_close) vs log(QQQ_daily_close) sur les 60 derniers jours. Si p < 0.05 → `daily_coint_regime` ON pour le jour **suivant** (pas de look-ahead). Sinon OFF. |
| **Point d'armement (intraday 5m)** | À chaque close 5m pendant NY session, **si** `daily_coint_regime = ON`, recompute z-score = (spread_now − rolling_mean_20) / rolling_std_20 où spread = log(SPY) − β × log(QQQ), β estimé par OLS rolling 60 bars 5m. |
| **Point de confirmation** | `|z|` ≥ 2.0σ ET z-score précédent du même côté (anti-flip). **Pas de test coint intraday** — on fait confiance au gate daily. |
| **Point d'émission setup** | Si z ≤ −2.0 → setup `long_spread` (long SPY + short QQQ × β_hedge). Si z ≥ +2.0 → setup `short_spread`. β_hedge = ratio dollars. |
| **Point d'invalidation (SL)** | `|z|` ≥ 3.0σ (blow-out) OU `bars_in_trade` ≥ 18 bars 5m (1.5h) sans TP (time-stop). |
| **Point d'exit (TP)** | `|z|` ≤ 0.5σ (mean-reversion atteinte). Clôture des 2 jambes simultanément. |
| **Timeouts** | `daily_coint_recompute`: end-of-day. `entry_lockout_post_sl`: 30 min. `max_hold_duration`: 90 min. |

**Différence architecturale clé v1 vs v2** : v1 gate coint à chaque bar 5m (1/59 PASS → trop rare). v2 gate coint = 1 décision par jour (on/off journalier) → libère le timing intraday conditionnellement au régime vrai.

---

## Pièce D — dépendances moteur + audit infra

| Brique | Statut | Note |
|---|---|---|
| `engle_granger_test` (ADF résidus OLS) | EXISTS | [cointegration.py](../../../engines/stat_arb/cointegration.py), 20 tests D1. **Réutilisé tel quel** — numpy-only, agnostique TF. |
| `rolling_zscore`, `rolling_beta`, `compute_spread` | EXISTS | [zscore.py](../../../engines/stat_arb/zscore.py), D1 tests. |
| `pair_sizing(beta_neutral)` | EXISTS | [sizing.py](../../../engines/stat_arb/sizing.py), D1 tests. |
| `PairSpreadTracker` state machine | EXISTS | [tracker.py](../../../engines/stat_arb/tracker.py), D2 11 tests. `require_cointegration=False` OK pour v2 (gate déporté au niveau daily externe). |
| **Daily close aggregator** SPY+QQQ | **MISSING (trivial)** | ~20 lignes : `df.resample("1D", label="right").last()` filtré NY close 16:00 ET. |
| **Daily regime gate** (wrapper call-once-per-day) | **MISSING (trivial)** | ~30 lignes : précompute dict `{trading_date → coint_pvalue, is_coint}` à partir des daily closes. |
| Simultaneous dual-leg open atomique | **MISSING (même bloquant que v1)** | **Contourné** via harness autonome, comme Sprint 3 D3' (pas de commitment `ExecutionEngine` refactor avant verdict). |
| `sl_logic: zscore_blowout` + `tp_logic: zscore_meanrev` | In harness | Pas besoin de resolver YAML-driven pour smoke — logique dans harness. |
| Session NY filter (09:30–15:00 ET) | EXISTS | Post-S1.1 timezone audit + ZoneInfo strict. |

**Résultat audit** : `full infra exists` — les 2 seules briques manquantes sont triviales (~50 lignes) et vivent dans le harness v2. Pas de chantier moteur. Cohérent §0.5 Leg 4.1 "coût ~2-3j par node".

---

## Pièce E — YAML / config d'exécution

À ce stade : **pas de YAML dans playbooks.yml** (comme Sprint 3 v1) car harness autonome. Config via dataclass `SmokeConfigV2` dans [stat_arb_smoke_v2.py](../../../scripts/stat_arb_smoke_v2.py) (à créer).

Paramètres principaux :
```python
beta_window = 60            # 5m bars (5h)
z_window = 60               # 5m bars
daily_coint_window = 60     # trading days (~3 mois calendar)
daily_coint_alpha = 0.05
daily_coint_lookback_days = 120  # load 120 days calendar ≈ 80 trading days pour remplir les 60 bars coint
entry_z = 2.0
exit_z = 0.5
blowout_z = 3.0
time_stop_bars = 18
lockout_bars = 6
risk_dollars = 100.0
```

Pas de `require_cointegration` intraday (v1 l'avait off par défaut faute de PASS). v2 remplace par gate daily externe au tracker.

---

## Pièce F — tests

Briques D1+D2 déjà couvertes par **31 tests PASS** (v1). v2 n'introduit que 2 briques triviales (daily aggregator + daily gate dict), testables implicitement via run smoke + audit `daily_coint_bars` counter dans `debug_counts.json`.

**Pas de tests unitaires nouveaux obligatoires** pour le smoke v2 — §19.3 budget : écrire tests si smoke PASS (avant phase D3 full engine). Si smoke FAIL → ARCHIVED, tests inutiles.

**Audit obligatoire dans verdict** :
- Nombre de trading days dans la fenêtre où `daily_coint_regime = ON` (doit être > 0 sinon Cas A §20 infra).
- Nombre total setups emitted et trades closed.
- Distribution `exit_reason` : TP_MEAN_REVERSION / SL_BLOWOUT / TIME_STOP / EOD.
- `mean_reversion_rate` (part TP / total).

---

## Pièce G — protocole de run

| Champ | Valeur |
|---|---|
| Smoke week canon | nov_w4 (2025-11-17 → 2025-11-21), 5 sessions NY |
| Corpus daily | Septembre → novembre 2025 (≥ 60 trading days avant 2025-11-17 pour remplir coint window) |
| Mode | harness autonome (pas `run_mini_lab_week.py`), IdealFillModel équivalent (no costs v1-smoke parity) |
| Allowlist | N/A (harness) |
| Caps | N/A (harness, 1 paire max à la fois) |
| Artefacts | `backend/results/labs/mini_week/stat_arb_spy_qqq_v2/stat_arb_spy_qqq_v2_smoke_nov_w4/` : `trades.parquet` + `debug_counts.json` + `daily_coint_trace.json` |

Commande canonique :
```bash
cd backend && .venv/bin/python scripts/stat_arb_smoke_v2.py \
  --start 2025-11-17 --end 2025-11-21 \
  --label stat_arb_spy_qqq_v2_smoke_nov_w4
```

---

## Pièce H — kill rules pré-écrites (AVANT smoke, non re-interprétables post-hoc)

**Smoke nov_w4 — KILL si une seule condition tient :**

| Rule | Threshold | Action |
|---|---|---|
| 1. `daily_coint_pass_days` | **< 1 sur 5 trading days** | KILL → SMOKE_FAIL → ARCHIVED. Cas A/B §20 (gate infra trop strict ou régime nov_w4 atypique). |
| 2. `n` (trades émis) | **< 10** | KILL → SMOKE_FAIL → ARCHIVED. Cas B §20. Même avec gate ON le signal intraday reste rare. |
| 3. `mean_reversion_rate` | **< 50 %** | KILL → SMOKE_FAIL → ARCHIVED. Cas C §20. Le gate daily ne prédit pas la mean-rev intraday. |
| 4. `E[R] gross` | **≤ 0** | KILL → SMOKE_FAIL → ARCHIVED. Cas C §20. |
| 5. Gate promotion (si tout PASS) | n ≥ 10 ET mean_rev ≥ 50 % ET E[R] > 0 | → Stage 1 4-semaines validation avec `--realistic` |

**Gate promotion final** (Stage 3, si Stage 1 PASS) : `E[R] net+slippage > 0.10R + n > 30 + PF > 1.2 + gates O5.3 PASS`.

**Pas de tuning post-smoke v2** §19.3 budget & §10 r11. Si smoke FAIL, hypothèse réfutée dans la configuration testée. Une v3 (paire alternative, TF différent, gate autre que EG daily) = nouvelle hypothèse = nouveau dossier.

---

**Statut** : `SPECIFIED_READY` — full infra existe, harness v2 à écrire (~150 lignes, 30 min).
