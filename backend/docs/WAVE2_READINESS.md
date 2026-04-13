# Wave 2 — readiness (post multi-week nov 2025 + audit NF exit)

Prérequis demandés : **multi-fenêtres** + **audit sorties News_Fade** → remplis (`MULTI_WEEK_VALIDATION_NOV2025.md`, `AUDIT_NEWS_FADE_SESSION_END.md`). Aucun gros refactor ; pas de décision SAFE/FULL ici.

---

## PREUVE CODE

- Playbooks cibles déjà enregistrés côté knowledge : `FVG_Fill_Scalp`, `Session_Open_Scalp` dans `backend/knowledge/playbooks.yml` (cf. inventaire Phase 2 / loader).
- Exécution **non** élargie dans ce lot : pas de changement d’allowlist « définitif » ; le mini-lab respecte déjà les filtres risk du runner.

---

## PREUVE RUN

Tableau consolidé **nov2025** : `docs/MULTI_WEEK_VALIDATION_NOV2025.md` — sections **FVG_Fill_Scalp** et **Session_Open_Scalp** (funnel M/S/SR/T par `202511_w01` … `w04`).

Lecture rapide : **FVG** varie (**17 / 17 / 0 / 10** trades T) ; **Session_Open** reste un **faible débit** (**9 / 6 / 3 / 13** trades T). **NY** tombe à **0** match sur **w03** (signal « semaine atypique » ou filtres contexte — à noter pour toute comparaison NY vs NF).

---

## PREUVE TEST

- Tests **3B** existants : `backend/tests/test_phase3b_execution.py` (NY/NF session end, LSS time-stop, parité backtest).
- Aucun nouveau test Wave 2 requis pour **ce** jalon (readiness = constat + ordre de travail).

---

## ANALYSE

- **FVG_Fill_Scalp** et **Session_Open_Scalp** sont **observables** sur le même protocole lab que `202511_w01`, mais avec **volume et stabilité** inégaux selon la fenêtre ; **w03 FVG à 0** impose de **ne pas** conclure sur une seule semaine.
- **News_Fade** : l’audit sortie conclut que le profil `session_end` dominant est **cohérent** avec l’implémentation actuelle ; toute évolution du **chemin de trade NF** doit rester **optionnelle** et **isolée** (voir options dans l’audit).

---

## DÉCISION

- **GO** pour planifier des mini-labs / critères d’acceptation **Wave 2** par playbook (FVG puis Session_Open), **sans** merge de politique production SAFE/FULL.
- **NO-GO** pour « activer massivement » Wave 2 tant qu’il n’y a pas de **répétition** sur d’autres mois / presets multi-week.

---

## NEXT STEP

1. **FVG_Fill_Scalp** : définir une ou deux fenêtres lab (comme `run_mini_lab_week.py`) + métriques minimales (funnel, ΣR, `exit_reason`) ; patch playbook / moteur **uniquement** si écart documenté.
2. **Session_Open_Scalp** : idem, en tenant compte du faible T sur nov 2025.
3. **NF trade path** (optionnel) : un seul tweak à la fois parmi ceux listés dans `AUDIT_NEWS_FADE_SESSION_END.md`, puis rerun `run_mini_lab_multiweek.py --preset nov2025` pour régression.
