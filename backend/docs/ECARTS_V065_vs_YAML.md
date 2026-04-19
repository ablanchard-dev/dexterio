# Écarts VIDEO 065 → YAML FVG_Fill_Scalp

**Source**: `SOURCE_V065_TRUTH_PACK.md`
**YAML**: `backend/knowledge/playbooks.yml` L494-561

---

## Écarts CRITIQUES (changent le comportement)

### ÉCART 1 — Range 15m absent (CRITIQUE)

| VIDEO 065 | YAML actuel | Impact |
|-----------|-------------|--------|
| "start on your 15 minute chart [...] mark the high and the low of this first 15 minute candle" (L44699-44707) | Pas de `range_tf: "15m"`, pas de bornes range, `session: "ANY"` | **Step 1 complètement absente.** Le playbook ne filtre pas par rapport au range 15m. N'importe quel FVG 5m peut trigger un trade, même sans break hors du range du jour. |

**Fix requis**: Ajouter une condition `range_15m` qui calcule high/low du 1er candle 15m (9:30-9:45) et exige un break hors de ce range avant de chercher un FVG.

### ÉCART 2 — Scoring composite au lieu de gate binaire FVG (CRITIQUE)

| VIDEO 065 | YAML actuel | Impact |
|-----------|-------------|--------|
| "no fair value gap so there is no trade" (L44759) — gate binaire | `scoring: { weights: { fvg_quality: 0.45, pattern_quality: 0.30, trend_alignment: 0.25 } }` (L552-556) | **Le FVG est optionnel.** Un trade peut passer avec un score faible en fvg_quality compensé par pattern_quality et trend_alignment. Résultat: 47% de trades grade C dans le WF Phase E. |

**Fix requis**: Remplacer le scoring par `required_signals: ["FVG_BULL@5m"]` / `["FVG_BEAR@5m"]`. Le mécanisme existe déjà dans `playbook_loader.py` L735-777 mais n'est utilisé par AUCUN playbook.

### ÉCART 3 — Session window trop large (CRITIQUE)

| VIDEO 065 | YAML actuel | Impact |
|-----------|-------------|--------|
| "getting to our desks right at 9 45 a.m" (L44694) + "as long as this happens before 12 pm" (L44775) → 9:45-12:00 ET | `time_range: ["09:30", "15:30"]` (L508) | **Fenêtre 6× trop large** (6h au lieu de 2h15). Des trades sont pris entre 12:00 et 15:30 qui n'existeraient pas dans la stratégie V065. |

**Fix requis**: `time_range: ["09:45", "12:00"]`

### ÉCART 4 — Candle patterns requis sans justification MASTER (CRITIQUE)

| VIDEO 065 | YAML actuel | Impact |
|-----------|-------------|--------|
| Le trader ne mentionne AUCUN candlestick pattern comme condition. Le seul pattern est le FVG (3-candle gap). | `required_families: ["doji", "spinning_top", "pin_bar"]`, `direction: "trend_continuation"` (L527-531) | **Filtre parasite.** Des FVG valides sont rejetés parce qu'aucun doji/spinning_top/pin_bar n'est détecté. Ce filtre n'existe PAS dans V065. |

**Fix requis**: Supprimer `candlestick_patterns.required_families` ou le rendre optionnel (bonus scoring seulement, pas gate).

---

## Écarts MOYENS (affectent les paramètres)

### ÉCART 5 — TP1 trop bas

| VIDEO 065 | YAML actuel | Impact |
|-----------|-------------|--------|
| "two to one risk to reward" (L44735) — TP unique à 2:1 | `tp1_rr: 1.5, tp2_rr: 2.0` (L546-547) | TP1 à 1.5 au lieu de 2.0. Avec partial close à TP1, le trade ne capture jamais le plein 2:1. |

**Fix requis**: `tp1_rr: 2.0` (un seul TP, pas de partial). Ou `tp1_rr: 2.0, tp2_rr: null`.

### ÉCART 6 — Breakeven at 1R non mentionné dans V065

| VIDEO 065 | YAML actuel | Impact |
|-----------|-------------|--------|
| "sit back and let the market do the heavy lifting" (L44739) — set and forget | `breakeven_at_rr: 1.0` (L548) | V065 ne mentionne AUCUN breakeven move. Le trade est set-and-forget: SL ou TP, rien entre les deux. |

**Fix requis**: `breakeven_at_rr: null` ou retirer la ligne.

### ÉCART 7 — Max duration 30 min trop court

| VIDEO 065 | YAML actuel | Impact |
|-----------|-------------|--------|
| Pas de durée max mentionnée. Le trader dit "sit back" → le trade dure jusqu'au SL ou TP. Session 9:45-12:00 → max ~2h15. | `max_duration_minutes: 30` (L550) | 30 min = trop court pour un trade 5m avec TP 2:1. Des trades légitimes sont coupés avant d'atteindre le TP. |

**Fix requis**: `max_duration_minutes: 135` (= 2h15, fin de session 12:00) ou retirer.

---

## Écarts FAIBLES (comportement similaire)

### ÉCART 8 — SL placement

| VIDEO 065 | YAML actuel | Impact |
|-----------|-------------|--------|
| "stop loss at the base of fair value gap candle one" (L44731-44734) — low/high du candle 1 du FVG pattern | `type: "FIXED", distance: "fvg_extreme", padding_ticks: 1` (L540-542) | `fvg_extreme` = extrême du FVG → probablement le même point. **À vérifier dans le code.** |

---

## Écarts NON PRÉSENTS dans V065 (ajouts du repo)

| Élément YAML | Présent dans V065? | Verdict |
|-------------|-------------------|---------|
| `london_sweep_required: false` | Non mentionné | OK (false) |
| `require_sweep: false` | Non mentionné | OK (false) |
| `require_bos: false` | Non mentionné | OK (false) |
| `smt_bonus: false` | Non mentionné | OK (false) |
| `context_requirements.day_type_allowed` | Non mentionné | **Suspect** — V065 n'a pas de filtre day_type |
| `context_requirements.structure_htf` | Non mentionné | **Suspect** — V065 n'a pas de filtre HTF structure |
| `confirmation_tf: "1m"` | Non mentionné — V065 dit "limit order on the FVG" (5m) | **À corriger** — entry sur 5m, pas 1m |

---

## Résumé des corrections nécessaires pour FVG_Fill_V065

| # | Correction | Priorité | Nouveau code? |
|---|-----------|----------|---------------|
| 1 | Ajouter range 15m (1er candle 9:30-9:45) | **CRITIQUE** | Oui — logique range à implémenter |
| 2 | Activer `required_signals: ["FVG_BULL@5m", "FVG_BEAR@5m"]` | **CRITIQUE** | Non — mécanisme existe |
| 3 | Session `["09:45", "12:00"]` | **CRITIQUE** | Non — changement YAML |
| 4 | Supprimer `required_families` candlestick | **CRITIQUE** | Non — changement YAML |
| 5 | `tp1_rr: 2.0`, supprimer tp2 | MOYEN | Non — changement YAML |
| 6 | `breakeven_at_rr: null` | MOYEN | Non — changement YAML |
| 7 | `max_duration_minutes: 135` | MOYEN | Non — changement YAML |
| 8 | `confirmation_tf: "5m"` (pas "1m") | MOYEN | Non — changement YAML |
| 9 | Supprimer scoring composite | CRITIQUE (lié à #2) | Non — YAML + loader skip scoring si required_signals |

**Sur 9 corrections, 1 seule nécessite du code nouveau** (range 15m).
Les 8 autres sont des changements YAML ou activation de mécanismes existants.
