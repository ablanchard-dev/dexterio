# Aplus_01 Family A full — dossier

> Standard industriel (plan §18). Statut, hypothèse, état décisionnel, dépendances moteur, kill rules — écrits **avant** code.

---

## Pièce A — fiche d'identité

| Champ | Valeur |
|---|---|
| Nom canonique | `Aplus_01_full_v1` |
| Version | `v1` |
| Famille | ICT-A (sweep → BOS → continuation confluence → 1m confirm) |
| Type | Stateful séquentiel (state machine per-symbol) |
| Instruments | SPY, QQQ |
| Timeframes | 1m (confirm) + 5m (sweep, BOS, confluence) + D (HTF bias proxy) |
| Direction | both (LONG après down-sweep counter-rallye, SHORT après up-sweep counter-rejet) |
| Régime visé | NY session 09:30–15:00 ET, tout day_type sauf news lock |
| Statut initial | `SPECIFIED_BLOCKED_BY_INFRA_PARTIAL` (briques manquantes — cf pièce D) |
| Auteur / origine | MASTER ICT — première instanciation fidèle Family A séquentielle |
| Dernière review | 2026-04-22 (création dossier) |

---

## Pièce B — hypothèse formelle (5 sous-blocs, non négociables)

### Thèse
Après un sweep de liquidité HTF dans une direction, le marché 5m retourne contre la direction du sweep, casse la structure (BOS), retest une zone de confluence (FVG ∪ breaker ∪ OB) opposée au sweep, et y trouve une pression 1m de confirmation. Cette séquence — **et seulement cette séquence complète** — produit un setup tradable.

### Mécanisme
Les liquidités HTF (equal highs/lows, session highs/lows, daily highs/lows) attirent le prix parce que les ordres stop sont concentrés là. Une fois ces stops déclenchés, l'absorption du flux par les institutionnels donne un retournement structurel (BOS 5m). Ce retournement crée une zone d'inefficience (FVG) ou une zone d'origine (breaker, OB) que le marché retest avant la continuation. La pression 1m sur le retest = signal d'exécution institutionnel.

### Conditions de fertilité
- Session NY (liquidité maximale, asymétrie info forte).
- HTF bias D non-conflictuel (pas de signal LONG en bear D fort confirmé).
- Volatilité raisonnable (ATR 5m ∈ [0.10, 1.00] $ pour SPY/QQQ — éviter expansion extrême).
- Day_type ∈ {trend, manipulation_reversal, range avec extrêmes claires}.

### Conditions de stérilité (ne pas trader)
- Lunch (12:00–13:00 ET) — liquidité fragmentée, faux signaux fréquents.
- News window ±5min (FOMC, CPI, NFP) — gaps imprévisibles.
- Volatilité extrême (ATR 5m > 1.20 $) — SL trop large pour 1R utile.
- HTF D bias confirmé contre la direction du setup (LONG demandé alors que D = downtrend confirmé).

### Risque principal (= falsifiabilité)
**L'hypothèse est fausse si** : sur ≥30 setups émis sur 4 semaines NY corpus, peak_R p80 < 1.0R **et** E[R] gross < 0R. Cela voudrait dire que la séquence MASTER fidèle ne capture pas un edge structurel — le bear case ICT serait fermé, et il faudrait pivoter non-ICT (stat arb, mean reversion).

**L'hypothèse est aussi fausse si** : 0 setup émis sur nov_w4 (fenêtres state-machine trop serrées ou détecteurs cassés — cas A/D §20 plutôt que cas C).

---

## Pièce C — spécification d'état décisionnel

State machine per-symbol, reset par trading_date (rollover 18:00 ET via `SessionRangeTracker` pattern).

### États

```
IDLE
  ↓ event: sweep_5m détecté (signal SWEEP@5m, fallback v1 du HTF sweep)
ARMED_AFTER_SWEEP
  - timeout: 20 bars 5m (=100 min) → IDLE
  - direction armed = OPPOSÉE à la direction du sweep
  ↓ event: BOS_5m dans direction armed
BOS_CONFIRMED
  - timeout: 6 bars 5m (=30 min) → IDLE
  ↓ event: zone touch (FVG ∪ breaker ∪ OB compatible direction armed)
CONFLUENCE_TOUCHED
  - timeout: 8 bars 5m (=40 min) → IDLE
  - zone_id mémorisé
  ↓ event: 1m pressure confirm (BOS 1m OU engulfing 1m direction armed) dans 12 bars 1m
EMIT_SETUP
  - retour IDLE après émission
```

### Points formels

| Point | Évènement |
|---|---|
| Armement | `sweep_5m` détecté (signal pattern existant) |
| Confirmation 1 | `BOS_5m` dans direction armed (counter-sweep) |
| Confirmation 2 | Pullback 5m touche zone confluence (FVG ∪ breaker ∪ OB) compatible armed_direction |
| Émission setup | Pression 1m confirme (BOS 1m OU engulfing 1m) dans armed_direction |
| Invalidation | Tout timeout d'état OU prix casse au-delà de la zone confluence dans la direction du sweep original |

### Rationale timeouts
- **sweep_timeout=20×5m (100min)** : un sweep HTF a typiquement un effet d'attraction sur 1–2 heures. Au-delà, le contexte HTF a évolué, le sweep n'est plus un trigger valide.
- **bos_timeout=6×5m (30min)** : si BOS ne survient pas dans les 30 min post-sweep, l'absorption a échoué — pas de retournement structurel.
- **touch_timeout=8×5m (40min)** : pullback institutionnel typique 15–40 min après BOS. Au-delà, momentum perdu.
- **confirm_timeout=12×1m (12min)** : pression 1m doit être réactive après touch. Au-delà, pas d'engagement institutionnel sur la zone.

Tous timeouts paramétrables via YAML (pièce E) pour itération budget §19.3.

---

## Pièce D — dépendances moteur + audit infra

### Détecteurs requis
| Détecteur | Statut | Localisation |
|---|---|---|
| `SWEEP@5m` | **EXISTE** | [backend/engines/patterns/](../patterns/) (signal `sweep` validé engine_sanity_v2) |
| `BOS@5m` | **EXISTE** | [backend/engines/patterns/](../patterns/) (signal `bos` validé engine_sanity_v2) |
| `FVG@5m` | **EXISTE** | [backend/engines/patterns/fvg.py](../patterns/fvg.py) (validé engine_sanity v1+v2) |
| `BREAKER@5m` | **EXISTE** | [backend/engines/patterns/breaker_block.py](../patterns/breaker_block.py) |
| `OB@5m` | **EXISTE** (post-fix v2) | [backend/engines/patterns/order_block.py](../patterns/order_block.py) |
| `BOS@1m` + `engulfing@1m` | **EXISTE** | détecteurs natifs |
| HTF sweep 1h/4h | **MANQUANT** | v1 = fallback `SWEEP@5m`, HTF sweep différé Sprint ultérieur |

### Trackers requis
| Tracker | Statut | Localisation |
|---|---|---|
| `Aplus01Tracker` (state machine per-symbol) | **À CRÉER** | `backend/engines/features/aplus01_tracker.py` (S1.2.2) |

### Helpers géométriques
| Helper | Statut | Localisation |
|---|---|---|
| `confluence_zone.is_zone_touched(zones, bar)` | **À CRÉER** | `backend/engines/features/confluence_zone.py` (S1.2.1) |
| `pressure_confirm.has_1m_pressure(bars_1m, dir, window)` | **À CRÉER** | `backend/engines/features/pressure_confirm.py` (S1.2.1) |

### Logique de session requise
- NY session 09:30–15:00 ET — **EXISTE** (`playbook_loader.py` time_windows ET-aware, validé S1.1).

### SL logic requise
- `swing_structure` k3 (pivot 5m récent ± 3 ticks padding) — **EXISTE** (`tp_resolver.py` directional_change k3 LRU cached).

### TP logic requise
- `liquidity_draw swing_k3 significant` + ceiling 3.0 + reject_on_fallback — **EXISTE** (briques α'' validées 32/32 tests).

### Risk hooks particuliers
- Standard ALLOWLIST/DENYLIST + caps session + cooldown 5min — **EXISTE** ([risk_engine.py](../risk_engine.py)).
- `max_setups_per_session: 3` (Aplus_01 séquentiel = signal rare, cap raisonnable).

### Champs runtime journal requis
| Champ | Présent ? | Action |
|---|---|---|
| `tp_reason` | OUI | déjà persisté |
| `structure_alignment_counter` | OUI | déjà persisté |
| `state_machine_trace` | **NON** | à ajouter dans S1.2.3 (timestamps des transitions IDLE→ARMED→BOS→TOUCH→EMIT) |

### Résultat audit infra (verdict obligatoire §18)

**`partial infra exists`** → statut `SPECIFIED_BLOCKED_BY_INFRA_PARTIAL`. Briques manquantes :

1. `confluence_zone.py` (helper géométrique pur, ~50 LOC) — S1.2.1.
2. `pressure_confirm.py` (helper 1m pur, ~40 LOC) — S1.2.1.
3. `aplus01_tracker.py` (tracker state machine, ~200 LOC) — S1.2.2.
4. `state_machine_trace` field dans journal — S1.2.3.

Briques 1 et 2 réutilisables (futurs playbooks Family A/F). Brique 3 spécifique Aplus_01 mais pattern réutilisable (template state machine pour autres séquentiels).

→ Une fois S1.2.1–S1.2.2 livrées, statut transitionne `SPECIFIED_BLOCKED_BY_INFRA_PARTIAL` → `IMPLEMENTED`.

---

## Pièce E — YAML d'exécution

Voir [v1.yml](v1.yml) (sera créé en S1.2.4, après briques + tracker, conformément à phase D §19.1 ordre strict).

Lien symbolique vers `backend/knowledge/campaigns/aplus01_full_v1.yml` (où le runner cherche les YAML par convention).

---

## Pièce F — tests

Voir [tests/](tests/) (sera créé en S1.2.5, niveau 1 unit + niveau 2 intégration).

Cibles minimum :
- 10+ tests unit `aplus01_tracker.py` : transitions, timeouts, reset trading day, multi-symbols isolation, faux positifs absents, émission unique.
- 2 tests intégration : chargement YAML + zéro régression suite existante (33+12=45 tests engine baseline + DST).

---

## Pièce G — protocole de run

Voir [protocol.md](protocol.md) (sera créé en S1.3, juste avant smoke nov_w4).

Convention initiale :
- **Smoke week** : 2025-11-17 → 2025-11-21 (nov_w4).
- **4 semaines validation** (si smoke PASS) : jun_w3 + aug_w3 + oct_w2 + nov_w4.
- **Mode obligatoire promotion** : `backtest-realistic` (ConservativeFillModel — Sprint 4 prérequis).
- **Allowlist** : `Aplus_01_full_v1` seul.
- **Caps actives, kill-switch actif** (pas de `RISK_EVAL_RELAX_CAPS`).

---

## Pièce H — kill rules pré-écrites (AVANT smoke)

Conformément à plan §10 et §19.1 phase F : **les kill rules sont fixées maintenant et ne se réinterprètent pas après lecture des résultats**.

### Smoke nov_w4

| Métrique | Seuil | Verdict |
|---|---|---|
| `n` (nombre de setups émis) | < 10 | **Cas B (sous-exercice)** — élargir corpus 1 semaine de plus avant de conclure |
| `n` | = 0 | **Cas A ou D** — re-vérifier détecteurs / state machine fenêtres avant tout autre run |
| `peak_R p80` | < 1.0R | **Cas C (edge absent)** — KILL ICT, pivot Sprint 3 (stat arb non-ICT) |
| `E[R] gross` | ≤ 0 | **Cas C** — KILL ICT, pivot Sprint 3 |
| `n ≥ 10` ET `peak_R p80 ≥ 1.0R` ET `E[R] gross > 0` | tous trois | **PASS smoke** → Sprint 2 (4 semaines + gates O5.3) |

**Aucune itération de paramètres** (timeouts, thresholds) au stade smoke. Si smoke FAIL, on classe Cas A/B/C/D **avant** toute action — pas de re-tuning silencieux. Budget itération §19.3 = max 3 post-smoke.

### Validation 4 semaines (si smoke PASS)

| Gate | Seuil promotion |
|---|---|
| E[R] net + slippage | > 0.10R |
| n total | > 30 |
| PF | > 1.2 |
| Bar permutation | p < 0.05 |
| Sharpe daily | > 1.0 sur ≥3/4 semaines |
| Martin ratio | > 1.0 |

Tous PASS → `WF_PASS` → `PRODUCT_GRADE` → 1er playbook product-grade DexterioBOT. Au moins un FAIL → `WF_FAIL`, classification cas A/B/C/D, budget itération.

---

## Suivi statut (§17)

| Date | Statut | Commit / verdict |
|---|---|---|
| 2026-04-22 | `SPECIFIED_BLOCKED_BY_INFRA_PARTIAL` | dossier créé (S1.2.0) |
