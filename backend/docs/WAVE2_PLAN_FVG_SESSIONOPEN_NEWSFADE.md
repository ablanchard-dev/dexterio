# Wave 2 — plan minimal (3 playbooks uniquement)

**Périmètre strict :** `FVG_Fill_Scalp`, `Session_Open_Scalp`, `News_Fade` (trade path).  
**Non-objectifs :** élargir allowlist aux 15–20 FULL ; toucher Phase 3B (`PHASE3B_PLAYBOOKS`, `paper_trading` 3B) ; refactor global.

**Référence code :** `backtest/engine.py` (`_process_bar_optimized`, boucle d’exécution), `engines/setup_engine_v2.py`, `engines/risk_engine.py`, `knowledge/playbooks.yml`.

---

## 1. Synthèse par playbook

| Playbook | Symptôme labfull_202511 | Blocage exact (repo) |
|----------|-------------------------|----------------------|
| **FVG_Fill_Scalp** | M=96, S=0 | Aucun setup créé après match playbook : rejets dans `generate_setups` / `_determine_direction` / edge filters / `_calculate_price_levels` / absence FVG dans `ict_patterns` sur la plupart des minutes (ICT alimenté surtout aux clôtures 5m/15m — voir `engine.py` ~1076–1093). |
| **Session_Open_Scalp** | M=622, S=0 | Idem funnel setup ; playbook **continuation** : `_determine_direction` exige bias + faible indécision ; `_rebalance_grade_if_needed` pénalise fortement sans sweep/BOS (`setup_engine_v2.py` ~465+). |
| **News_Fade** | SR=1, T=0 | Setup passe risk mais **aucun** trade : après risk, un seul setup par symbole/barre = `max(filtered_setups, key=final_score)` (`engine.py` ~1345–1346) ; puis `_execute_setup` peut échouer (cooldown, session cap, daily cap, `can_take_setup`, `place_order`). |

---

## 2. Patch minimal (proposé — pas implémenté dans ce commit doc)

### 2.1 FVG_Fill_Scalp

- **Diagnostic d’abord :** instrumenter ou lire `setup_engine_reject_reasons` / logs sur un run court avec `RISK_EVAL_*` si besoin ; vérifier présence de `pattern_type == "fvg"` dans `ict_patterns` aux minutes où match FVG_Fill compte.
- **Patch cible minimal :** une seule levier à la fois, par exemple :
  - assouplir **un** filtre documenté (ex. RR structurel edge si `< 1.2` pour ce nom uniquement avec garde `playbook_name == "FVG_Fill_Scalp"`), **ou**
  - enrichir détection FVG sur 1m **uniquement** pour ce playbook (scope étroit — à valider perf).
- **Interdit dans Wave 2 :** changer les règles globales NY ou `PHASE3B_PLAYBOOKS`.

### 2.2 Session_Open_Scalp

- **Diagnostic :** même approche — compteur `_reject_reason_counts` (`regime_chop`, `no_liquidity_event`, `rr_too_low`, `high_indecision_continuation`, `low_conviction`, etc.).
- **Patch minimal :** constante de garde `WAVE2_PLAYBOOKS` ou check explicite sur le nom ; assouplir **un** seuil (ex. `_rebalance_grade_if_needed` ou indecision max) **uniquement** pour `Session_Open_Scalp`.
- **Policy :** reste **LAB** — `SAFE_POLICY_DENYLIST` dans `risk_engine.py` ne doit pas être retiré sans décision produit séparée.

### 2.3 News_Fade (trade path)

- **Cause probable 1 :** même minute qu’un autre setup autorisé avec **score plus haut** → NF jamais choisi (`max(..., key=final_score)`).
- **Cause probable 2 :** `_execute_setup` : cooldown / max trades session / daily cap / sizing invalide.
- **Patch minimal (choix à trancher) :**
  - **A)** Tie-break ou priorité **documentée** pour NF dans un sous-ensemble de minutes (ex. fenêtres `time_windows` du YAML) — **garde stricte** sur le nom.
  - **B)** Log + compteur `debug_counts` pour refus NF après risk (`trades_attempted` vs `opened`) avant tout changement de logique.
- **Recommandation :** commencer par **B** (instrumentation seule), puis **A** si les logs confirment la perte au `max(score)`.

---

## 3. Test court

| Playbook | Test minimal suggéré |
|----------|----------------------|
| FVG_Fill | Run backtest **1 journée** + symbole unique + assert `setups_created_by_playbook["FVG_Fill_Scalp"] > 0` après patch ; ou test unitaire sur `generate_setups` avec `ict_patterns` synthétiques contenant FVG. |
| Session_Open | Idem avec patterns / bias forcés pour satisfaire continuation + reweight. |
| News_Fade | Run court ou test d’intégration : 1 setup NF après risk → `place_order` success **ou** compteur de refus explicite (cooldown vs score). |

**Commande type (manuel) :**

```powershell
Set-Location c:\bots\dexterio1-main\backend
python -m pytest tests/... -q
```

(À compléter avec le fichier de test réel une fois le patch posé.)

---

## 4. Validation

- **FVG / Session_Open :** `debug_counts` : `setups_created_by_playbook` > 0 pour le nom ; idéalement `setups_after_risk_filter_by_playbook` > 0 ; pas de régression sur **NY** (même run lab court : comparer trades NY ou total trades ± tolérance).
- **News_Fade :** `trades_opened_by_playbook["News_Fade"] >= 1` sur une fenêtre où NF a des matches, **ou** preuve documentée que le blocage est uniquement cooldown/cap (acceptable si policy voulue).
- **Wave 1 / NY :** `NY_Open_Reversal` trades et `PHASE3B` inchangés fonctionnellement (pas de modification des fichiers 3B pour ces vagues).

---

## 5. Risque sur Wave 1 / NY

| Risque | Mitigation |
|--------|------------|
| Changer `max(filtered_setups)` ou ordre DAILY/SCALP affecte NY | Toute priorité NF doit être **bornée** (fenêtre horaire NF uniquement) ou derrière flag env. |
| Assouplir filtres edge pour Session/FVG augmente volume global | Patch **par playbook** + lab 1 mois avant merge. |
| Cooldown partagé | Vérifier clé `(symbol, playbook)` — un assouplissement NF ne doit pas ouvrir flood sur NY sans revue. |

---

## 6. Parallèle avec validation post-3B

- **3B :** re-lab + `PHASE_3B_COMPARABILITY` / métriques exit — **indépendant** des patches Wave 2 ci-dessus.
- **Ordre conseillé :** finir **instrumentation NF (étape B)** sans changer 3B ; patches FVG/SOS sur **branche ou commits séparés** après constat chiffré.

---

*Plan Wave 2 — documentation uniquement ; implémentation dans des commits code dédiés.*
