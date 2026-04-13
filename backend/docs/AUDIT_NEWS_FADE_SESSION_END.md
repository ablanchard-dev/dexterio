# Audit — sorties `session_end` sur **News_Fade** (mini-labs nov 2025)

Contexte : sur le protocole mini-lab (`run_mini_lab_week.py`, allowlists respectées, bypass LSS quarantine), les trades **News_Fade** ferment très souvent en `**session_end`**. Question : acceptable métier ? effet « trop mécanique » ? ajustements minimaux sans casser **3B** ni **NY_Open_Reversal** ?

---

## PREUVE CODE

**1. Ordre des contrôles dans `update_open_trades` (paper / backtest)** : le moteur unique est `ExecutionEngine` (`paper_trading.py`), aussi utilisé par `BacktestEngine`. **News_Fade** : TP (TP2 > TP1) **avant** `session_end`. **NY_Open_Reversal** (et tout autre DAILY hors NF) : `session_end` **avant** TP sur le même tick.

```311:342:backend/engines/execution/paper_trading.py
            # 1.b / 2 Phase 3B : News_Fade seul — TP avant session_end (NY et autres inchangés)
            if trade.playbook == "News_Fade":
                if try_take_profits():
                    continue
                if current_time and trade.trade_type == "DAILY" and trade.session_window_end_utc is not None:
                    if current_time >= trade.session_window_end_utc:
                        trades_to_close.append({... 'reason': 'session_end', ...})
                        ...
                        continue
            else:
                if current_time and trade.trade_type == "DAILY" and trade.session_window_end_utc is not None:
                    if current_time >= trade.session_window_end_utc:
                        trades_to_close.append({...})
                        continue
                if try_take_profits():
                    continue
```

Conséquence **NY** : dès que l’horloge dépasse la fin de fenêtre YAML, **TP1 (3R)** n’est **pas** testé sur ce tick : la sortie est `session_end` au prix courant. **News_Fade** : si le prix touche TP **après** la borne horaire, TP l’emporte (voir `test_news_fade_tp_evaluated_before_session_end_when_both_conditions_hold`).

**2. Calcul de `session_window_end_utc`** : borne = **fin de la fenêtre horaire d’entrée** (NY timezone), pas la clôture RTH 16:00.

```31:68:backend/engines/execution/phase3b_execution.py
def compute_session_window_end_utc(
    playbook_def: PlaybookDefinition, entry_utc: datetime
) -> Optional[datetime]:
    """
    Borne de fin de fenêtre NY (timezone America/New_York) pour le jour calendaire d'entrée,
    si l'entrée tombe dans une fenêtre YAML (time_range ou time_windows).
    """
    # ...
    for t0, t1 in windows:
        start = datetime.combine(d, t0, ny)
        end = datetime.combine(d, t1, ny)
        if start <= ny_t <= end:
            return end.astimezone(timezone.utc)
    return None
```

**3. Playbooks concernés par la session window (3B)** : seulement **NY** et **News_Fade** en **DAILY** ; LSS reste sur time-stop scalping.

```71:76:backend/engines/execution/phase3b_execution.py
def should_attach_session_window_end(playbook_name: str, trade_type: str) -> bool:
    """LSS (SCALP) utilise max_duration, pas une sortie de fin de session journalière."""
    return (
        trade_type == "DAILY"
        and playbook_name in ("NY_Open_Reversal", "News_Fade")
    )
```

**4. YAML News_Fade** : deux fenêtres courtes + **tp1_rr: 3.0** (objectif distant vs durée de fenêtre).

```354:360:backend/knowledge/playbooks.yml
  timefilters:
    session: "NY"
    # PATCH C FINAL: Deux fenêtres distinctes (09:30-11:00 ET 14:00-15:30)
    time_windows:
      - ["09:30", "11:00"]
      - ["14:00", "15:30"]
    news_events_only: true
```

```396:399:backend/knowledge/playbooks.yml
  take_profit_logic:
    # RR globalement exigeant, >= 3R
    min_rr: 3.0
    tp1_rr: 3.0
```

---

## PREUVE RUN

**Multi-semaines (preset `nov2025`)** : `backend/results/labs/mini_week/consolidated_mini_week_nov2025.json` + tableau `backend/docs/MULTI_WEEK_VALIDATION_NOV2025.md`.  
Commande : `scripts/run_mini_lab_multiweek.py --preset nov2025 --skip-existing` → `exit_code: 0` (run terminal agent, agrégation incluse).

**Funnel News_Fade (T = trades)** sur les 4 fenêtres : **9 + 1 + 12 + 5 = 27** trades (cf. JSON consolidé).

**Motifs de sortie `News_Fade`** sur les parquets `trades_miniweek_<label>_AGGRESSIVE_DAILY_SCALP.parquet` :


| Fenêtre      | Trades NF | `exit_reason`                    |
| ------------ | --------- | -------------------------------- |
| `202511_w01` | 9         | `session_end` × 9                |
| `202511_w02` | 1         | `session_end` × 1                |
| `202511_w03` | 12        | `session_end` × 11, `**SL` × 1** |
| `202511_w04` | 5         | `session_end` × 5                |


**Exemple w01 (R faibles, cohérent avec sortie « fin de fenêtre » sans TP 3R)** : les 9 NF ont des `r_multiple` entre environ **−0.17** et **+0.07** (lecture `pyarrow` sur `trades_miniweek_202511_w01_AGGRESSIVE_DAILY_SCALP.parquet`).

---

## PREUVE TEST

Le comportement « fermer en `session_end` après la borne » est **verrouillé** par un test unitaire :

```121:158:backend/tests/test_phase3b_execution.py
def test_session_end_news_fade_closes_after_window_end():
    # ...
    events = ex.update_open_trades({"SPY": 100.2}, current_time=t_end)
    assert tr.id not in ex.open_trades
    assert any(e.get("event_type") == "SESSION_END" for e in events)
    assert ex.closed_trades[-1].exit_reason == "session_end"
```

---

## ANALYSE

1. **Acceptable métier (lecture « fade news dans la fenêtre »)** : forcer la sortie à la fin de la fenêtre YAML correspond à une règle de **discipline de risque** (« on ne porte pas le fade au-delà du créneau prévu »). Ce n’est pas un bug de données ; c’est **aligné** avec Phase 3B et le YAML.
2. **« Trop mécanique » ?** Partiellement **oui** côté **P&L attendu** : avec **TP à 3R** et des fenêtres **courtes**, beaucoup de trades se résolvent en **scratch / micro-R** au lieu de TP ou SL — sur **NY**, `**session_end` reste avant TP** ; sur **News_Fade** (code actuel), TP est testé **avant** `session_end`, donc les sorties quasi tout `session_end` observées sur des runs historiques reflètent surtout **prix loin de 3R dans la fenêtre** (ou runs antérieurs au patch NF), pas l’absence de priorité TP côté NF.
3. **Contre-exemple** : **w03** montre **1 SL** — le stop peut toujours précéder `session_end` (ordre SL en premier).
4. **NY_Open_Reversal** : toute modification d’ordre **global** DAILY (TP avant `session_end`) **impacterait aussi NY** ; il faut donc rester sur des garde-fous **spécifiques NF** si on patch.

---

## DÉCISION

- **Garder** le comportement actuel comme **baseline 3B** tant que la priorité est la **comparabilité multi-fenêtres** et la **stabilité NY/LSS**.
- Le profil « presque tout `session_end` » sur NF est **expliqué et attendu** sous les paramètres actuels ; ce n’est **pas** une preuve que NF est « mort » — **w03** montre encore du flux (12 trades) et un SL réel.

---

## NEXT STEP

**Wave 2 (FVG_Fill_Scalp, Session_Open_Scalp, évolution chemin NF)** : **après** stabilisation multi-semaines — pas d’élargissement d’allowlist « SAFE/FULL » avant validation étendue.

**Ajustements minimaux candidats** :

1. ~~**TP avant `session_end` pour `News_Fade` uniquement**~~ — **fait** dans `paper_trading.py` (tests `test_news_fade_tp_evaluated_before_session_end_`* / NY inchangé `test_ny_open_reversal_session_end_still_before_tp_*`). Re-lancer nov2025 si besoin de mesurer l’effet sur les parquets vs baseline documentée ici.
2. `**tp1_rr` NF plus bas (ex. 2.0–2.5)** dans `playbooks.yml` : plus de chances d’atteindre TP1 dans la fenêtre **sans** toucher au moteur ; **PHASE B** (`run_mini_lab_phase_b_nf_tp1_sweep.py`) peut servir de cadre.
3. **(Plus intrusif)** : buffer minutes sur la borne de sortie — à documenter avec précaution.

**Commandes de suivi** : `run_mini_lab_multiweek.py --preset nov2025` après tweak YAML ou campagne PHASE B ; conserver `MULTI_WEEK_VALIDATION_NOV2025.md` + parquets comme preuves RUN.