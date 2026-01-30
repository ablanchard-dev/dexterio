# AUDIT SPRINT 3 — Review Complète + Stabilité Windows

**Date**: 2026-01-27  
**Objectif**: Valider pipeline grading + master candle E2E, stabilité Windows, no lookahead

---

## A) REVIEW STRUCTURÉE (P0/P1/P2)

### A.1 — Backtest Engine

#### P0 — CRITIQUE
| Fichier | Ligne | Problème | Impact | Fix |
|---------|-------|----------|--------|-----|
| `backend/backtest/engine.py` | 1064-1100 | Calcul MC utilise toutes les candles 1m sans limite temporelle stricte | Risque lookahead si candles futures | Limiter à candles <= current_time |
| `backend/backtest/engine.py` | 2800-2835 | Export `master_candle_debug` mais pas de validation post-run | Pas de preuve automatique | Ajouter `post_run_verification` |
| `backend/backtest/engine.py` | 2222-2259 | Propagation MC dans TradeResult mais pas de vérification null | Risque champs vides | Ajouter validation + diagnostic |

#### P1 — IMPORTANT
| Fichier | Ligne | Problème | Impact | Fix |
|---------|-------|----------|--------|-----|
| `backend/backtest/engine.py` | 2580-2598 | Export CSV MC mais pas de vérification cohérence | Risque incohérence données | Ajouter checks cohérence |
| `backend/backtest/engine.py` | 2735-2800 | `grading_debug` export mais pas de validation pipeline_ok | Pas de preuve automatique | Ajouter validation E2E |

#### P2 — AMÉLIORATION
| Fichier | Ligne | Problème | Impact | Fix |
|---------|-------|----------|--------|-----|
| `backend/backtest/engine.py` | 1064 | `mc_window_minutes` hardcodé à 15 | Pas configurable | Ajouter dans BacktestConfig |

---

### A.2 — Time Handling

#### P0 — CRITIQUE
| Fichier | Ligne | Problème | Impact | Fix |
|---------|-------|----------|--------|-----|
| `backend/engines/timeframe_aggregator.py` | 74-85 | Clôture HTF basée sur minutes UTC brutes, pas timezone NY | Risque mélange premarket/after-hours | Vérifier timezone NY avant agrégation |
| `backend/engines/master_candle.py` | 192-220 | Breakout vérifie `>= mc_end_ts` mais pas de vérification stricte | Risque lookahead si timestamp égal | Utiliser `>` strict |
| `backend/backtest/engine.py` | 1073-1090 | Filtre candles par session_date mais pas de limite `<= current_time` | Risque lookahead | Ajouter filtre temporel strict |

#### P1 — IMPORTANT
| Fichier | Ligne | Problème | Impact | Fix |
|---------|-------|----------|--------|-----|
| `backend/engines/master_candle.py` | 35-50 | `get_ny_rth_session_date` ne vérifie pas si timestamp est dans RTH | Risque attribution session incorrecte | Ajouter vérification RTH (09:30-16:00 NY) |

---

### A.3 — Costs (Slippage/Spread/Fees)

#### P1 — IMPORTANT
| Fichier | Ligne | Problème | Impact | Fix |
|---------|-------|----------|--------|-----|
| `backend/backtest/costs.py` | (à vérifier) | Risque double comptage si appelé plusieurs fois | Coûts incorrects | Vérifier appel unique par trade |

---

### A.4 — Jobs/Server (ProcessPool)

#### P0 — CRITIQUE
| Fichier | Ligne | Problème | Impact | Fix |
|---------|-------|----------|--------|-----|
| `backend/jobs/backtest_jobs.py` | 19-27 | `_executor` singleton mais pas de shutdown propre | Crash SpawnProcess après restart | Implémenter shutdown avec `cancel_futures=True` |
| `backend/jobs/backtest_jobs.py` | 474-477 | `executor.submit()` sans gestion erreur si executor shutdown | Workers zombies | Vérifier executor actif avant submit |
| `backend/server.py` | 100-103 | Shutdown handler ne ferme pas ProcessPoolExecutor | Ressources non libérées | Brancher shutdown executor dans lifespan |

---

### A.5 — Sécurité

#### P1 — IMPORTANT
| Fichier | Ligne | Problème | Impact | Fix |
|---------|-------|----------|--------|-----|
| `backend/server.py` | 88 | CORS par défaut `http://localhost:3000` mais pas `127.0.0.1:3000` | Incohérence frontend | Ajouter `127.0.0.1:3000` |
| `backend/server.py` | 94-97 | Logging basique, pas de rotation | Logs peuvent grossir indéfiniment | Ajouter rotation (optionnel) |
| `backend/` | - | Pas de `.env.example` | Secrets potentiellement hardcodés | Créer `.env.example` |

---

## B) CHECKLIST DE VALIDATION

### B.1 — Compilation
```powershell
cd C:\bots\dexterio1-main
python -m compileall backend -q
```
**Critère**: Exit code 0, pas d'erreurs

### B.2 — Tests Unitaires
```powershell
cd C:\bots\dexterio1-main\backend
python -m pytest tests/test_grading_propagation_p0.py tests/test_master_candle_p1.py -v
```
**Critère**: Tous les tests PASS

### B.3 — Backtest E2E
```powershell
# POST /api/backtests/run
# Poll jusqu'à "done"
# Vérifier post_run_verification_{run_id}.json
```
**Critère**: 
- `post_run_verification.pass == true`
- CSV contient colonnes grading + MC non-null
- `grading_debug_{run_id}.json` existe et cohérent
- `master_candle_debug_{run_id}.json` existe et cohérent

### B.4 — Stabilité Windows
```powershell
# Start backend -> run 1 job -> stop backend -> restart
# Vérifier logs: "executor shutdown OK"
# Vérifier: aucun trace SpawnProcess
```
**Critère**: Pas de crash SpawnProcess

### B.5 — No Lookahead
```powershell
# Vérifier sanity_report.lookahead_detector.pass == true
```
**Critère**: `lookahead_detector.pass == true` + samples valides

---

## C) CRITÈRES D'ACCEPTATION

### C.1 — P0 Fixes
- [x] ProcessPoolExecutor shutdown propre
- [ ] Post-run verification automatique
- [ ] No lookahead detector dans sanity_report
- [ ] MC calcul limité à candles <= current_time

### C.2 — P1 Fixes
- [ ] CORS inclut `127.0.0.1:3000`
- [ ] `.env.example` créé
- [ ] HTF aggregator vérifie timezone NY

### C.3 — Preuves
- [ ] `post_run_verification_{run_id}.json` généré après chaque run
- [ ] Tous les artifacts présents et cohérents
- [ ] Logs montrent "executor shutdown OK"

---

## D) FICHIERS À MODIFIER

1. `backend/jobs/backtest_jobs.py` — Shutdown ProcessPoolExecutor
2. `backend/server.py` — Lifespan handler pour shutdown
3. `backend/backtest/engine.py` — Post-run verification + no lookahead detector
4. `backend/engines/master_candle.py` — Filtre strict `>` pour breakout
5. `backend/engines/timeframe_aggregator.py` — Vérification timezone NY
6. `backend/server.py` — CORS + `.env.example`

---

**STATUS**: Audit complet, prêt pour fixes
