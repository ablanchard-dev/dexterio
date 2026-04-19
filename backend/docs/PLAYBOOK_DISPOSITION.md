# PLAYBOOK_DISPOSITION — Décision par playbook actuel

> Phase 3 du roadmap MASTER → Stratégies Fidèles.
> Date : 2026-04-18

---

## Résumé

| Action | Count | Playbooks |
|--------|-------|-----------|
| **RÉÉCRIRE** | 4 | NY_Open_Reversal, FVG_Fill_Scalp, Session_Open_Scalp, IFVG_5m_Sweep |
| **REMPLACER** (nouveau YAML campaign) | 1 | HTF_Bias_15m_BOS → campaign S2 |
| **SUPPRIMER** | 7 | London_Sweep, Trend_Cont, BOS_Momentum, Power_Hour, Lunch_Range, Morning_Trap, Liquidity_Sweep |
| **GARDER** | 1 | News_Fade (source = user invention, pas MASTER) |

---

## Disposition détaillée

### 1. NY_Open_Reversal → RÉÉCRIRE (fidèle V066 / S3)

**Source vidéo :** V066 "This Simple Strategy Made Me My First $100k"
**Stratégie mappée :** S3 — London Fakeout

**Écarts critiques (truth pack V066) :**
- `require_bos: false` → V066 exige BOS 5m candle close (gate binaire)
- Entry LIMIT → V066 est MARKET au BOS
- TP `tp1_rr: 3.0` fixe → V066 cible session lows dynamiques (1:3 à 1:5.6)
- Candlestick patterns requis (engulfing, pin_bar) → V066 n'en requiert aucun
- Manque la logique de niveaux "consommés"

**Campaign fidèle :** `campaign_london_fakeout_v066.yml`
```yaml
playbook_name: "London_Fakeout_V066"
setup_tf: "5m"
entry_logic:
  type: "MARKET"
  trigger: "bos_candle_close"
ict_confluences:
  require_sweep: true  # fakeout = sweep session H/L
  require_bos: true     # gate binaire
stop_loss_logic:
  type: "FIXED"
  distance: "fakeout_extreme"  # au-dessus du high du fakeout
take_profit_logic:
  type: "SESSION_LEVEL"  # prochain session low/high intact
  min_rr: 3.0
```
**Engine gaps requis :** G06, G07, G16

---

### 2. FVG_Fill_Scalp → RÉÉCRIRE en 2 campaigns (fidèle V065 S1a + V054 S1b)

**Sources vidéo :** V065 + V054
**Stratégies mappées :** S1a (V065) + S1b (V054)

**V065 (campaign existant campaign_range_fvg_v065.yml) :**
- Range 15m (9:30-9:45) → FVG 5m hors range → limit 50% FVG → 2:1 RR
- Gate binaire : FVG hors range obligatoire (pas scoring)
- Set-and-forget (pas de BE, pas de trailing)
- **Engine gaps :** G01, G05

**V054 (nouveau campaign) :**
- Range 5m (9:30-9:35) → FVG 1m hors range → retest + engulfing → market → 3:1 RR
- Model 2 : trailing après 3:1 si expanding market (P2)
- **Engine gaps :** G01, G03, G04, G05

**Note :** V065 et V054 sont 2 stratégies DISTINCTES du même auteur — TF range, TF entry, type d'ordre, RR, et confirmation sont tous différents.

---

### 3. Session_Open_Scalp → RÉÉCRIRE (fidèle V048 / S6)

**Source vidéo :** V048 "My 1 Minute Scalping Strategy"
**Stratégie mappée :** S6 — Marubozu Scalp

**Écarts critiques (truth pack V048) :**
- `time_range: ["03:00","03:15","09:30","09:45"]` → V048 = 9:30-11:30 (2h, pas 15min)
- `max_duration_minutes: 15` → V048 attend le retracement (peut prendre 1h+)
- Entry MARKET → V048 est LIMIT au niveau du Marubozu (retracement passif)
- Marubozu bilatéral dans engine → V048 = unilatéral (no bottom wick seulement)
- `required_families: [marubozu, engulfing, hammer, shooting_star]` → V048 = marubozu SEUL
- Scoring composite → V048 = gate binaire (Marubozu + break range)

**Campaign fidèle :** `campaign_marubozu_scalp_v048.yml`
```yaml
playbook_name: "Marubozu_Scalp_V048"
setup_tf: "5m"        # range
confirmation_tf: "1m"  # Marubozu + entry
opening_range:
  tf: "5m"
  duration_minutes: 15  # 9:30-9:45 (3 candles 5m)
entry_logic:
  type: "LIMIT"
  zone: "marubozu_level"  # limit au low/high du Marubozu
time_windows:
  - ["09:30", "11:30"]
max_duration_minutes: 120
```
**Engine gaps requis :** G01, G02, G11

---

### 4. IFVG_5m_Sweep → RÉÉCRIRE (fidèle V010 / S4)

**Source vidéo :** V010 "Five A+ iFVG Setups"
**Stratégie mappée :** S4 — iFVG Setups

**Écarts critiques (truth pack V010) :**
- `require_sweep: false` → V010 exige sweep INTO le FVG (gate binaire)
- Fenêtre IFVG = 5 candles → V010 montre FVGs "way to the left" (200+ candles)
- Pas de FVG HTF requis → V010 exige FVG HTF à gauche obligatoire
- SL `recent_swing` → V010 = close sous le FVG (plus étroit)
- TP `tp1_rr: 3.0` → V010 = 2R suffisant
- Pas de filtre discount/premium → V010 l'exige

**Campaign fidèle :** `campaign_ifvg_v010.yml`
```yaml
playbook_name: "IFVG_V010"
setup_tf: "5m"
required_signals: ["IFVG@5m"]
ict_confluences:
  require_sweep: true       # sweep INTO le FVG
  require_htf_fvg: true     # FVG HTF à gauche
  htf_fvg_max_age: 200      # candles
entry_logic:
  type: "MARKET"
  trigger: "ifvg_inversion_close"
stop_loss_logic:
  type: "FIXED"
  distance: "fvg_zone"  # close sous le FVG d'inversion
take_profit_logic:
  tp1_rr: 2.0
  min_rr: 2.0
filters:
  discount_premium: true  # LONG en discount, SHORT en premium
```
**Engine gaps requis :** G08, G09, G13

---

### 5. HTF_Bias_15m_BOS → REMPLACER par campaign S2 (V022)

**Source vidéo :** V022 "10h Course" (checklist séquentielle)
**Stratégie mappée :** S2 — Full Checklist ICT

**Pourquoi REMPLACER (pas réécrire) :** La stratégie V022 est séquentielle (sweep → BOS → confluence → trigger) et nécessite l'EventChainTracker (G10). Le playbook actuel ne capture pas du tout cette séquentialité.

**Campaign fidèle :** `campaign_checklist_v022.yml` (Phase 5b)
**Engine gaps requis :** G10 (bloquant — EventChainTracker)

**Décision :** Différer à Phase 5b. Le playbook actuel est désactivé (E[R] négatif sur tous les folds).

---

### 6. News_Fade → GARDER tel quel

**Source :** Invention utilisateur, pas de vidéo MASTER.
**Verdict :** Gate REOPEN_1R_VS_1P5R clos UNRESOLVED. E[R]≈-0.05. Garder en ALLOWLIST pour observation mais pas prioritaire.

---

### 7-13. SUPPRIMER (7 playbooks)

| Playbook | Raison de suppression | Source vidéo |
|----------|----------------------|-------------|
| **London_Sweep_NY_Continuation** | -326R. Direction OPPOSÉE à V066 (continuation vs reversal). | Aucune source fidèle |
| **Trend_Continuation_FVG_Retest** | -22R. Sous-cas absorbé par S1a/S1b (FVG retest). | Aucune source distincte |
| **BOS_Momentum_Scalp** | -142R. Pas de source MASTER. | Invention sans source |
| **Power_Hour_Expansion** | -31R. Pas de source MASTER. | Invention sans source |
| **Lunch_Range_Scalp** | DISABLED, toxique. Pas de source MASTER. | Invention sans source |
| **Morning_Trap_Reversal** | -12R quarantine. Partiellement V066 mais mal implémenté — absorbé par S3. | Absorbé dans V066/S3 |
| **Liquidity_Sweep_Scalp** | -9.8R quarantine. "Sweep" est une condition, pas une stratégie. | Condition ≠ stratégie |

**Note :** Les fichiers YAML ne sont pas supprimés physiquement. Ils sont déplacés hors de `playbooks.yml` principal. Les campaigns fidèles les remplacent.

---

## Résultat final : portefeuille cible

| # | Campaign YAML | Stratégie | Source | Statut |
|---|--------------|-----------|--------|--------|
| 1 | `campaign_range_fvg_v065.yml` | S1a | V065 | EXISTS — à valider |
| 2 | `campaign_range_fvg_v054.yml` | S1b | V054 | NEW |
| 3 | `campaign_marubozu_scalp_v048.yml` | S6 | V048 | NEW |
| 4 | `campaign_london_fakeout_v066.yml` | S3 | V066 | NEW |
| 5 | `campaign_ifvg_v010.yml` | S4 | V010 | NEW |
| 6 | `campaign_checklist_v022.yml` | S2 | V022 | NEW (Phase 5b) |
| 7 | `campaign_htf_aoi_v064.yml` | S10 | V064+V068 | NEW (P2 truth pack en cours) |
| 8 | `campaign_supply_demand_v055.yml` | S7 | V055 | NEW (P2 truth pack en cours) |
| 9 | `campaign_ob_retest_v004.yml` | S9 | V004 | NEW (P2 truth pack en cours) |
| 10 | `News_Fade` (tel quel) | — | User | EXISTS |

**Playbooks P3 (si P2 truth packs confirment) :**
| # | Campaign YAML | Stratégie | Source |
|---|--------------|-----------|--------|
| 11 | `campaign_asia_sweep_v051.yml` | S11 | V051 |
| 12 | `campaign_nq_rebalance_v071.yml` | S8 | V071 |
| 13 | `campaign_multi_confluence_v024.yml` | S12 | V024 |

---

## Dépendances engine gaps → campaigns

```
Sprint 1 (G01, G02, G04, G05, G09)
  └─ Débloque : S1a, S1b (Model 1), S6 (partiel), S4 (partiel)

Sprint 2 (G03, G11, G13)
  └─ Débloque : S1b (complet), S4 (complet), S6 (complet)

Sprint 3 (G06, G07, G08, G16)
  └─ Débloque : S3 (V066)

Sprint 4 (G10)
  └─ Débloque : S2 (V022)
```
