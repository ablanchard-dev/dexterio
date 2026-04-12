# Synthèse KEEP / BORROW — repos externes vs Dexterio

Document de **pont** : l’audit détaillé par repo est tenu à jour dans les revues d’ingénierie ; ici on **ancre** ce qui est déjà **emprunté en code** dans ce dépôt (sans dépendance runtime vers ces projets).

| Source | Idée empruntée | Implémentation Dexterio |
|--------|----------------|-------------------------|
| **Freqtrade** | Config / environnement explicite pour reproductibilité (`MINIMAL_CONFIG`, `DRY_RUN_WALLET`, colonnes trades stables) | `lab_environment` dans `run_manifest.json` via `utils/lab_environment_snapshot.py` |
| **Backtrader** | Analyzers post-run sur trades fermés (`TradeAnalyzer`) | `backtest/trade_parquet_analysis.py` + registre `backtest/trade_parquet_analyzer_bundle.py` (`summary_r`, `exit_reason_mix`, `playbook_counts`) |
| **NautilusTrader** | Séparation clients backtest data / exécution, moteur événementiel Rust/Cython | `run_clock_mode: BACKTEST` dans le manifest (point d’accroche futur ; pas de moteur NT) |
| **ML for Trading (Jansen)** | Pipeline recherche : données → features → validation temporelle | **BUILD** : notebooks / scripts dédiés plus tard ; pas d’import du repo |
| **Awesome Systematic Trading** | Curated listes, patterns bibliographiques | **Référence** uniquement ; aucun code |

**REJECT (ne pas importer)** : remplacer `BacktestEngine`, copier le kernel Freqtrade/Nautilus, stratégies génériques, dépendances lourdes additionnelles sans besoin produit.
