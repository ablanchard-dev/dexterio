# Lancement paper supervisé court terme — noyau **CORE_PAPER_NOW**

## Périmètre (état réel post–PHASE 1 agrégée)

- **News_Fade** : gate **`REOPEN_1R_VS_1P5R`** — arbitrage **1.0R vs 1.5R** avec YAML dérivés sur les **12 mêmes fenêtres** : **`PHASE_NF_TP1_ARBITRATION.md`**. Ne pas promouvoir NF dans le noyau paper avant **`decision.decision`** dans `_nf_tp1_arbitration_aggregate.json` (les seuls `nf1r_confirm_*` sans `playbooks_yaml` ne prouvent pas tp1=1.0 au moteur).
- **FVG_Fill_Scalp** : patch **W2-1** déployé ; valider 1–2 semaines additionnelles.
- **Session_Open_Scalp** : **READY_WITH_LIMITATIONS**.
- **NY_Open_Reversal** : dans allowlist ; **ne pas modifier** le YAML ; surveiller funnel par run.
- **Liquidity_Sweep_Scalp** : présent et actif ; rester sous **supervision** (LSS quarantaine bypass seulement en lab selon flags).

## Playbooks « noyau » proposés pour une **première** campagne supervisée

| Inclure maintenant | Attendre |
|--------------------|----------|
| NY_Open_Reversal, News_Fade (après décision tp1), Session_Open_Scalp, FVG_Fill_Scalp (post W2-1), LSS (si policy produit OK) | BOS_Momentum, Morning_Trap, Power_Hour, A+ packs — hors noyau jusqu’à labs dédiés |

## Garde-fous obligatoires

- `respect_allowlists=true` sauf lab explicite.
- Caps risk AGGRESSIVE inchangés.
- **Pas** d’allow-all en paper supervisé.
- Logs + `mini_lab_summary` + `run_manifest.json` + parquet trades par fenêtre.

## Protocole opérationnel

### Préchecks

1. `git status` propre ; `git_sha` noté dans le manifest du run.  
   Automatiser : `cd backend && .venv/bin/python scripts/paper_preflight.py` (avertit si sale ; `--strict` → code 2 si non propre). Sortie machine : `--json`.  
   **Vue consolidée** (preflight + rappels + option rapport parquet) : `scripts/paper_supervised_precheck.py [--json] [--strict] [--trades-parquet PATH [--playbook X]]`.
2. Données 1m SPY/QQQ couvrent la fenêtre.
3. YAML review : NY intact ; NF **tp1** tranché après REOPEN.
4. Diagnostic rapide sur un parquet trades : `scripts/report_trades_parquet.py <fichier.parquet> --json`.

### Lancement

```bash
cd backend
.venv/bin/python scripts/run_mini_lab_multiweek.py \
  --preset <nov2025|sep2025|...> \
  --output-parent paper_supervised_<YYYYMMDD> \
  --skip-existing \
  --no-aggregate
```

### Surveillance

- Lire `funnel` NY / NF / FVG / SOS par semaine.
-Comparer E[R] NF à la ref PHASE B si tp1=1.0 maintenu.

### Artefacts attendus

Par semaine : `mini_lab_summary_*.json`, `run_manifest.json`, `trades_*_AGGRESSIVE_DAILY_SCALP.parquet`, `debug_counts_*.json`.

### Critères d’arrêt

- Drawdown / kill-switch risk (si activé en prod paper).
- Divergence funnel NY vs historique sur **même** fenêtre (signaler régression).
- Gate NF : si E[R] << 0 sur n ≥ 40 → stop et rouvrir tp1.

## NEXT

1. Exécuter sweep **1.0 vs 1.5** sur les **12 fenêtres** `nf1r_confirm_*` (copie YAML dérivée, comme PHASE B).
2. Décider tp1 NF puis figer `playbooks.yml` avant campagne paper multi-semaine brandée `paper_supervised_*`.
