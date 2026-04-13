# Phase 1 — Data / candles / ingestion (PREUVE)

**Date :** 2026-04-11

---

## PREUVE CODE

### Timezone : stockage UTC, filtres session en ET

- **Ingestion backtest** : `BacktestEngine.load_data` force une colonne `datetime` **tz-aware UTC** (`tz_localize` / `tz_convert`).

```277:283:/home/dexter/dexterio1-main/backend/backtest/engine.py
                # Step 4: Ensure datetime column is tz-aware UTC
                df['datetime'] = pd.to_datetime(df['datetime'], utc=True, errors='coerce')
                if df['datetime'].dt.tz is None:
                    df['datetime'] = df['datetime'].dt.tz_localize('UTC')
                else:
                    df['datetime'] = df['datetime'].dt.tz_convert('UTC')
```

- **Filtres playbook (sessions / fenêtres)** : `playbook_loader` convertit l’instant courant en **America/New_York** pour `time_range` / `time_windows` (évite d’interpréter les heures YAML en UTC brut).

### Lookahead (niveau pipeline chargé)

- Le moteur avance **minute par minute** sur la timeline 1m ; pas de lecture de bougies « futures » dans `load_data` au-delà du tri et du slice `[start_date, end_date]`. Un audit lookahead fin (détecteurs + agrégation HTF) reste un sujet **Phase 8 / profilage** si un cas isolé est suspect.

### Cohérence OHLC, doublons, trous

- Script dédié : `backend/scripts/audit_data_quality.py` — pour chaque symbole et fenêtre : `dup_timestamps`, `ohlc_invalid_rows`, `gaps_gt_60s` / `gaps_gt_300s`, `max_gap_seconds`, monotonie.

### Alignement multi-timeframe

- Boucle 1m + `TimeframeAggregator` (HTF dérivés du flux 1m) — pas de second source HTF disjointe dans le chemin standard décrit par `engine.py` (warmup via données chargées).

---

## PREUVE RUN

- **Workspace actuel :** aucun fichier `SPY.parquet` / `QQQ.parquet` trouvé sous le dépôt → **pas d’exécution locale** d’`audit_data_quality.py` ici.
- **Commande à rejouer dès que les parquet sont présents :**

```bash
cd backend && .venv/bin/python scripts/audit_data_quality.py \
  --symbols SPY,QQQ --start 2025-11-01 --end 2025-11-30 \
  --output results/data_audit_phase1.json
```

---

## PREUVE TEST

- Pas de test unitaire dédié « data audit » dans le périmètre de ce passage ; le script ci-dessus sert de **contrat** de qualité.

---

## ANALYSE

- Le pipeline **normalise explicitement UTC** et sépare bien la sémantique **ET pour les règles métier** — point critique pour éviter les décalages NY vs UTC.
- Sans parquet local, la baseline **quantitative** (trous, OHLC invalides) reste **non validée sur cette machine** ; les labs historiques (`labfull_*`) restent la preuve de runs passés avec données présentes ailleurs.

---

## DÉCISION

| Sujet | Verdict |
|--------|---------|
| TZ / normalisation | **KEEP** |
| Outil d’audit parquet | **KEEP** (`audit_data_quality.py`) |
| Patch code | **Aucun** (rien d’anormal prouvé dans le code sur ce périmètre) |

---

## NEXT STEP

- Rejouer `audit_data_quality.py` sur la **source parquet de vérité** (CI ou poste avec data).
- Phase 2 : inventaire YAML ↔ loader (déjà amorcé en Phase 0).
