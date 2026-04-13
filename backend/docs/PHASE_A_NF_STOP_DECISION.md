# PHASE A — Décision stop **News_Fade** (OPTION A vs OPTION B)

**Statut :** analyse **repo-driven** uniquement — **aucun patch** YAML ni moteur dans ce livrable.  
**Gate PHASE A :** recommandation ferme **OPTION A** (voir § DÉCISION).

**Prérequis :** parquets post-`initial_stop_loss` (révalidation nov2025) — ne pas réutiliser les conclusions « dégénérées » d’avant correctif.

---

## 1. PREUVE CODE

### 1.1 YAML — après OPTION A appliquée (`entry_percent_0.5`)

```yaml
  stop_loss_logic:
    type: "FIXED"
    distance: "entry_percent_0.5"
    padding_ticks: 5   # réservé futur spike_extreme ; non lu par le moteur pour le stop
```

*(Voir fichier réel `backend/knowledge/playbooks.yml` bloc News_Fade pour les commentaires complets.)*

Le loader expose `sl_type`, `sl_distance` mais **ne charge pas** `padding_ticks` dans `PlaybookDefinition` :

```91:99:backend/engines/playbook_loader.py
        # Entry/SL/TP logic
        self.entry_type = data['entry_logic']['type']
        self.entry_zone = data['entry_logic']['zone']
        self.sl_type = data['stop_loss_logic']['type']
        self.sl_distance = data['stop_loss_logic']['distance']
        self.min_rr = data['take_profit_logic']['min_rr']
```

### 1.2 Moteur — calcul réel des niveaux (**tous** les playbooks via ce chemin)

`_create_setup_from_playbook_match` appelle `_calculate_price_levels` **sans** transmettre `playbook_name` ni `sl_distance` YAML :

```147:158:backend/engines/setup_engine_v2.py
            entry_price, stop_loss, tp1, tp2 = self._calculate_price_levels(
                symbol=symbol,
                direction=direction,
                candle_patterns=candle_patterns,
                ict_patterns=ict_patterns,
                liquidity_levels=liquidity_levels,
                min_rr=match['min_rr'],
                tp1_rr=match['tp1_rr'],
                tp2_rr=match.get('tp2_rr'),
                last_price=last_price,
            )
```

`_calculate_price_levels` applique **la même** approximation **±0,5 %** pour **LONG** / **SHORT**, indépendamment du playbook :

```340:357:backend/engines/setup_engine_v2.py
        # Prix d'entrée: utiliser le dernier close réel (obligatoire)
        entry_price = float(last_price)

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

**Conséquence :** **NY_Open_Reversal**, **News_Fade**, **Liquidity_Sweep_Scalp**, etc. partagent cette géométrie côté `_calculate_price_levels` tant qu’ils passent par `SetupEngineV2` sans branche spécifique.

### 1.3 Modèle pattern — pas de high/low de « spike »

`CandlestickPattern` ne porte **pas** les prix extrêmes de la bougie ; seulement famille, direction, force, etc. :

```54:72:backend/models/setup.py
class CandlestickPattern(BaseModel):
    """Pattern Chandelle détecté (Engulfing, Pin Bar, etc.)"""
    ...
    family: str
    name: str
    direction: str
    ...
    at_level: bool = False
    after_sweep: bool = False
```

Implémenter **spike_extreme** au sens ICT (stop au-delà du plus haut / plus bas du spike) impose **un flux de données supplémentaire** (OHLC du spike, ou niveau ICT), **non présent** aujourd’hui dans les arguments de `_calculate_price_levels`.

### 1.4 Export runs — niveaux dans les parquets

Les trades sauvegardés utilisent les niveaux du `Setup` / `Trade` ; le stop **risque initial** exporté repose sur `initial_stop_loss` → cohérent avec le stop calculé au setup :

```2345:2351:backend/backtest/engine.py
                stop_loss=(
                    trade.initial_stop_loss
                    if getattr(trade, "initial_stop_loss", None) is not None
                    else trade.stop_loss
                ),
```

---

## 2. PREUVE RUN

**Constat quantitatif sur parquets post-fix** (mini-lab nov2025 régénéré, **27** trades NF) : pour chaque ligne, le rapport `|entry - stop_loss| / entry` est **exactement 0,5 %** (SHORT : stop au-dessus ; LONG : stop en dessous). Cela **colle** au code `entry * 1.005` / `entry * 0.995`, **pas** à une distance variable « spike ».

**Reproduction** (depuis `backend/`, avec les parquets actuels) :

```bash
.venv/bin/python -c "
import pyarrow.parquet as pq
from pathlib import Path
base = Path('results/labs/mini_week')
for w in ['202511_w01','202511_w02','202511_w03','202511_w04']:
    df = pq.read_table(base/w/f'trades_miniweek_{w}_AGGRESSIVE_DAILY_SCALP.parquet').to_pandas()
    nf = df[df.playbook=='News_Fade']
    for _, r in nf.iterrows():
        ep, sl = float(r.entry_price), float(r.stop_loss)
        pct = abs(ep-sl)/ep*100
        assert abs(pct - 0.5) < 1e-9, (w, pct)
print('OK: all NF trades 0.5% risk vs entry')
"
```

Ce run attache la **vérité empirique du repo** (nov2025 post-fix) à la **vérité du code** (0,5 % fixe).

*(Les grilles MFE / « 3R trop loin » après correction d’export sont dans `AUDIT_NEWS_FADE_GEOMETRY_REVALIDATION_NOV2025.md` — elles ne sont pas réécrites ici mais restent le contexte métier pour la suite.)*

---

## 3. PREUVE TEST

- **Aucun** test automatisé actuel n’asserte que `sl_distance == spike_extreme` YAML → niveau moteur ; `tests/test_phase3b_execution.py` valide l’**exécution** (BE, session_end, `initial_stop_loss`), pas la sémantique YAML du stop NF.
- `test_playbooks.py` / `test_setup_engine_v2` **affichent** entry/SL mais ne **verrouillent** pas `spike_extreme`.
- **Conclusion test :** absence de garde-fou sur l’alignement YAML ↔ moteur pour le stop — d’où l’intérêt d’une **décision documentée** puis, en PHASE B, de tests ciblés **après** changement volontaire.

---

## 4. ANALYSE — OPTION A vs OPTION B

| Critère | **OPTION A** — YAML aligné sur **0,5 %** effectif | **OPTION B** — **`spike_extreme` + `padding_ticks`** réels, **NF only** |
|--------|-----------------------------------------------------|------------------------------------------------------------------------|
| **Complexité patch** | **Faible** : éditer `playbooks.yml` (et éventuellement un commentaire / clé explicite `percent_entry: 0.5`) ; pas de logique nouveau calcul. | **Élevée** : branche `playbook_name == "News_Fade"` (ou lecture `sl_distance`) ; **fournir** high/low du spike (étendre patterns, passer la bougie 1m, ou niveau sweep) ; interpréter `padding_ticks` en prix ; gérer absences / multi-patterns. |
| **Blast radius** | **Minimal** si **seulement** YAML + doc : **aucun** changement de PnL. Si on modifiait le moteur pour lire un nouveau champ global, risque — **recommandé : YAML seul** pour A. | **Contrôlé** si garde **stricte** `News_Fade` uniquement ; toutefois **nouveaux paramètres** (volatilité des stops) **invalident** la continuité avec l’historique **0,5 %**. |
| **Cohérence métier** | Honnêteté **repo-first** : le fade est déjà modélisé avec un **buffer fixe** en % — acceptable si accepté comme **proxy** du spike. | **Alignement** sémantique YAML / ICT **meilleur** **si** la donnée « extrême du spike » est **correcte** ; sinon risque de stops **trop serrés** ou **trop larges** vs l’intuition. |
| **Cohérence nov2025** | **Totale** : les runs et ré-audits sont **déjà** en 0,5 %. | **Rupture** : nouveaux stops → **nouveau** funnel, ΣR, MFE — **non comparables** aux chiffres nov2025 sans **re-baseline** explicite. |
| **Facilité de test** | **Élevée** : snapshot YAML + test optionnel « NF stop = 0,5 % entry ». | **Moyenne à faible** : jeux de cas OHLC + edge cases ; mocks bougie spike. |
| **Risque NY** | **Nul** si **aucun** changement moteur (YAML NF seul). | **Nul** si branche **strictement** limitée à `News_Fade` et **aucune** modification du chemin NY — mais **review** obligatoire sur signatures `_calculate_price_levels`. |
| **Comparaisons historiques** | **Préservées** (même moteur). | **Cassées** pour NF tant qu’on n’a pas re-taggué / re-run une baseline. |

---

## 5. DÉCISION (GATE PHASE A)

### Recommandation ferme : **OPTION A**

**Motifs repo-driven :**

1. **Le moteur ne lit pas** `spike_extreme` ni `padding_ticks` pour le stop ; la **seule** implémentation en production du chemin `SetupEngineV2` est **±0,5 %**.
2. Les **données pattern** actuelles **ne portent pas** les extrêmes de spike nécessaires à une OPTION B **fidèle** sans chantier **plus large** que « patch minimal NF ».
3. Les **preuves run** nov2025 post-fix montrent **exactement** ce comportement 0,5 % — toute OPTION B **recommencerait** la mesure NF.
4. OPTION A **maximise** la **réversibilité** et **zéro risque** pour **NY** et **LSS** si l’on se limite à **documenter / YAML NF** sans toucher `_calculate_price_levels`.

**OPTION B** reste **valable comme chantier futur** explicite (« spike OHLC + loader padding + tests »), **pas** comme prochaine étape minimale avant un sweep `tp1_rr`.

---

## 6. OPTION A — **APPLIQUÉE** (lot traçable)

**Date / périmètre :** alignement **uniquement** `News_Fade` dans `backend/knowledge/playbooks.yml` :

- `distance` : **`entry_percent_0.5`** (documente le comportement réel **±0,5 %** depuis le close d’entrée).
- **`padding_ticks`** : **conservé** avec commentaire — **non utilisé** par le moteur pour le stop aujourd’hui ; réservé au **chantier ultérieur** OPTION B (`spike_extreme` + padding).
- **`_calculate_price_levels`** : **inchangé** (NY / LSS inchangés).

**Baseline métier pour PHASE B :** le sweep **`tp1_rr`** NF-only part de cette vérité **stop = 0,5 % fixe** ; toute comparaison avant/après sweep doit **réutiliser** ce stop sauf décision explicite de rouvrir OPTION B.

**Chantier distinct (non lancé) :** implémentation **spike_extreme + padding** pour NF seul, avec OHLC spike et extension loader — **hors** ce lot.

---

## 7. NEXT STEP

1. **PHASE B** : sweep **`tp1_rr`** NF-only (**1,0 / 1,25 / 1,5 / 2,0**), mini-lab nov2025, métriques demandées (trades, winrate, ΣR, `exit_reason`, parts session_end / TP / SL, durée médiane, etc.) — **sans** toucher NY.
2. **PHASE C** : recommandation métier finale (hors scope immédiat).

---

*PHASE A close ; YAML aligné ; tests `test_phase2_news_fade_context` (stop NF / moteur).*
