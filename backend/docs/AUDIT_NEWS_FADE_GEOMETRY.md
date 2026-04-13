# Audit — géométrie **News_Fade** (multi-week nov2025, 27 trades)

**Erratum :** les **9** cas `entry == stop_loss` sur w03 provenaient du **breakeven** (stop déplacé à l’entrée) + export du stop **final** — voir `DIAGNOSTIC_NF_W03_ENTRY_EQ_STOP.md` et le correctif `initial_stop_loss` (les métriques « dégénérées » de ce doc sur parquets **avant** correctif étaient biaisées). **Après** rerun nov2025 + parquets corrigés : `AUDIT_NEWS_FADE_GEOMETRY_REVALIDATION_NOV2025.md`.

**Objectif :** trancher si le goulot vient du **RR**, du **stop**, de la **fenêtre**, ou de la **qualité d’entrée** — **sans patch moteur** dans ce livrable.

**Sources :** parquets `results/labs/mini_week/202511_w0*/trades_miniweek_*_AGGRESSIVE_DAILY_SCALP.parquet` + OHLC 1m `data/historical/1m/{SPY,QQQ}.parquet`.

---

## PREUVE CODE

### YAML — intention métier (stop « spike » + RR 3)

```391:401:backend/knowledge/playbooks.yml
  stop_loss_logic:
    type: "FIXED"
    distance: "spike_extreme"
    padding_ticks: 5
  
  take_profit_logic:
    # RR globalement exigeant, >= 3R
    min_rr: 3.0
    tp1_rr: 3.0
    tp2_rr: 5.0
    breakeven_at_rr: 1.0
```

### Moteur — géométrie réellement calculée aujourd’hui (`setup_engine_v2`)

`_calculate_price_levels` **ne lit pas** `sl_distance` / `spike_extreme` : il fixe le stop à **±0,5 %** de l’entrée (approximation « structure pattern » commentée, mais en pratique pourcentage fixe).

```343:357:backend/engines/setup_engine_v2.py
        # Stop basé sur la structure locale du pattern
        if direction == 'LONG':
            # SL sous le low du pattern (approximé par une distance fixe pour l'instant)
            stop_loss = entry_price * 0.995  # 0.5% sous l'entrée
        else:
            # SL au-dessus du high du pattern
            stop_loss = entry_price * 1.005  # 0.5% au-dessus

        # TP1 basé sur le RR cible
        if direction == 'LONG':
            risk = entry_price - stop_loss
            tp1 = entry_price + risk * tp1_rr
        else:
            risk = stop_loss - entry_price
            tp1 = entry_price - risk * tp1_rr
```

**Conséquence audit :** la question « le stop **spike_extreme** gonfle-t-il R ? » ne peut pas être répondue à partir du **code path actuel** : ce n’est **pas** `spike_extreme` qui est appliqué, mais **0,5 % du prix**. Le **YAML et le moteur sont désalignés** sur la définition du stop.

### Fenêtres d’activation (contexte durée)

```354:360:backend/knowledge/playbooks.yml
  timefilters:
    session: "NY"
    time_windows:
      - ["09:30", "11:00"]
      - ["14:00", "15:30"]
    news_events_only: true
```

---

## PREUVE RUN

### Méthode

- **27** lignes **News_Fade** (4 semaines nov2025).
- Par trade : `risk_pts = |entry − stop|`, `reward_pts = |TP1 − entry|`, durée = `duration_minutes`, `exit_reason`.
- **MFE_R** / **MAE_R** sur bougies 1m **entre** `timestamp_entry` et `timestamp_exit` (même méthode que l’audit intrabar) :
  - **LONG** : MFE = (max high − entry) / risk, MAE = (entry − min low) / risk.
  - **SHORT** : MFE = (entry − min low) / risk, MAE = (max high − entry) / risk.

### Anomalie : trades « dégénérés » (risque nul)

**9 / 27** trades ont **`entry_price == stop_loss`** (tous sur **`202511_w03`**). Dans ces cas, **R n’est pas défini** ; les métriques en R (MFE/MAE) sont **non fiables**. Ils sont exclus des agrégats « valides » ci-dessous.

| Catégorie | Nombre |
|-----------|-------:|
| Total NF | 27 |
| `entry == stop` (dégénérés) | 9 |
| **Valides** (`risk > 0`) | **18** |

### Géométrie des **18** trades valides

| Indicateur | Valeur |
|------------|--------|
| `reward_pts / risk_pts` (RR géométrique TP1) | **exactement 3,0** partout (cohérent `tp1_rr: 3`) |
| `risk_pts / entry` | **exactement 0,5 %** partout (cohérent `setup_engine_v2` ±0,5 %) |
| `exit_reason` | `session_end` × 17, `SL` × 1 (sur l’échantillon valide) |

**Distribution MFE_R / MAE_R (n = 18)** — MFE max **≈ 0,92 R**, MAE max **≈ 1,16 R** (un trade va jusqu’au-delà de 1R défavorable intraminute avant sortie).

**Durée (minutes)** — tous les trades : médiane **41** ; valides : médiane **≈ 38,5** ; dégénérés : médiane **41**. Des tenues vont jusqu’à **~86 min** (fenêtre matin max ~90 min ou après-midi ~90 min — la fenêtre n’est pas toujours le facteur limitant si le prix ne progresse pas vers TP).

### Grille de franchissement **MFE** (combien de trades atteignent au moins une fois le seuil pendant la vie du trade)

Seuil | Nombre / **18** valides | Nombre / **27** (brut, dont MFE non défini pour 9)
------|-------------------------|--------------------------------------------------
≥ 0,25 R | 10 | 10
≥ 0,50 R | 7 | 7
≥ 0,75 R | 5 | 5
≥ **1,0 R** | **0** | **0**
≥ 1,5 R | 0 | 0
≥ 2,0 R | 0 | 0
≥ **3,0 R** (TP1) | **0** | **0**

**Grille MAE** (adversité intraminute, n = 18 valides) : ≥ 0,25 R → 10 ; ≥ 0,5 R → 3 ; ≥ 0,75 R → 2 ; ≥ 1,0 R → 1.

### Synthèse géométrique

- Avec **stop à 0,5 %** et **TP à 3R**, il faut environ **1,5 %** de mouvement favorable depuis l’entrée pour toucher TP1 (SHORT : baisse ~1,5 % depuis l’entrée si risque = +0,5 % au-dessus).
- Les **mèches 1m** pendant la vie du trade **n’atteignent jamais 1R** de favorable sur les trades valides ; le plafond observé reste **< 1R**. Le **3R TP** est donc **hors d’atteinte** sur cet échantillon, indépendamment de l’ordre TP / `session_end`.

---

## PREUVE TEST

- **Aucun** test automatisé ne vérifie aujourd’hui l’alignement **YAML `spike_extreme`** ↔ **`_calculate_price_levels`**, ni l’absence de trades **`entry == stop`** sur NF.
- Les tests Phase 3B portent sur l’**exécution** (ordre SL / session / TP), pas sur la **construction** des niveaux dans `setup_engine_v2`.

---

## ANALYSE

1. **RR trop élevé (tp1_rr = 3)** : la grille MFE montre de la progression **jusqu’à ~0,75–0,92 R**, mais **zéro** trade ne franchit **1R**. Baisser **tp1_rr** (ex. 1R–1,5R) est le levier **le plus directement aligné** avec la courbe observée de mouvement favorable.

2. **Stop trop large** : sur les trades **valides**, le stop n’est **pas** « gonflé » par `spike_extreme` — il est **fixe à 0,5 %** dans le code. Ce n’est pas énorme en pourcentage ; le vrai problème est le **ratio** avec un TP à **3R**. **Élargir** le stop empirerait la distance en dollars vers TP ; **resserrer** le stop augmenterait la fréquence de SL sans résoudre seul l’écart vers 3R. **Aligner** le stop sur la vraie logique **spike + padding** (si c’est la spec) est un chantier **YAML + moteur** séparé, pas constaté comme « padding qui gonfle R » dans le run actuel (car autre formule).

3. **Fenêtre trop courte** : des trades restent ouverts **jusqu’à ~86 min** ; le prix ne va pas pour autant vers 1R favorable. La fenêtre **peut** couper des extensions plus tardives, mais ici le constat dominant est **déjà** « pas assez de mouvement **même intraminute** pour 1R », pas seulement « coupés trop tôt par le créneau ».

4. **Qualité des entrées** : **9 / 27** trades avec **stop = entrée** indiquent un **défaut de pipeline / journalisation** sur une session (**w03**), pas une géométrie métier saine. Cela **pollue** les stats globales et doit être **corrigé avant** toute décision fine sur RR ou stop.

---

## DÉCISION

| Levier | Pertinence sur nov2025 (après audit) |
|--------|----------------------------------------|
| **Baisser `tp1_rr`** | **La plus élevée** — les mouvements observés se situent surtout **sous 1R** ; TP à **3R** est inatteignable sur l’échantillon valide. |
| **Revoir le stop NF** | **Moyenne** — priorité = **aligner moteur et YAML** (`spike_extreme` vs 0,5 %) + **éliminer les entrées dégénérées** ; ce n’est pas d’abord « padding trop large » dans le run mesuré. |
| **Revoir la fenêtre** | **Plus basse** — utile seulement après constat de trades qui **approchent** TP sans l’atteindre à la clôture de fenêtre ; ici le goulot est **sous 1R** de MFE. |
| **Laisser tel quel** | **Non recommandé** si l’objectif est d’obtenir des TP crédibles sans changer le reste : la géométrie **3R** est **incompatible** avec les excursions mesurées. |

**À ne pas confondre :** « pas de patch dans cet audit » ≠ « le playbook est bon tel quel » ; l’audit conclut que **la géométrie cible (3R avec stop 0,5 %)** est **hors portée** des mouvements réalisés sur ces 18 trades valides.

---

## NEXT STEP

1. **Qualité données** : investiguer **pourquoi 9 trades NF (w03) ont `entry == stop`** (chemin setup, arrondi, rejet SL, bug journal) — **avant** toute optimisation RR.
2. **Décision métier** : si on garde l’esprit « fade news », trancher une **cible RR réaliste** (ex. 1R–2R) **au YAML** puis mesurer sur mini-lab (hors scope moteur ici).
3. **Alignement spec** : ticket dédié **YAML `spike_extreme` + padding** ↔ implémentation dans **`_calculate_price_levels`** (sans refactor global, playbook par playbook si besoin).

---

*Commande de reproduction (depuis `backend/`, avec les mêmes imports que les scripts lab) : charger les 4 parquets NF, reconstruire `risk_pts`, filtrer `risk_pts > 1e-9`, recalculer MFE/MAE sur OHLC 1m comme pour `AUDIT_NEWS_FADE_INTRABAR.md`.*
