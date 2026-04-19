# ENGINE_GAPS — Lacunes moteur pour stratégies fidèles

> Compilé depuis les truth packs V065, V054, V048, V066, V010, V022 + V064/V068, V055, V004 (P2 en cours).
> Date : 2026-04-18

---

## Vue d'ensemble

| ID | Gap | Stratégies impactées | Complexité | Priorité |
|----|-----|---------------------|------------|----------|
| **G01** | Opening Range Tracker | S1a (V065), S1b (V054), S6 (V048) | Moyenne (~100 lignes) | **P0** |
| **G02** | Marubozu unilatéral (no-wick unilateral) | S6 (V048) | Faible (~20 lignes) | **P0** |
| **G03** | Retest + Engulfing séquentiel | S1b (V054) | Moyenne (~80 lignes) | **P0** |
| **G04** | Market order at candle close | S1b (V054), S3 (V066), S4 (V010) | Faible (~20 lignes) | **P0** |
| **G05** | FVG "hors range" gate (position relative) | S1a (V065), S1b (V054) | Faible (~30 lignes) | **P0** |
| **G06** | Session highs/lows consommés | S3 (V066) | Moyenne (~60 lignes) | **P1** |
| **G07** | TP dynamique sur session levels | S3 (V066) | Moyenne (~50 lignes) | **P1** |
| **G08** | Sweep spatial INTO FVG | S4 (V010) | Moyenne (~50 lignes) | **P1** |
| **G09** | IFVG récence élargie (5 → 200+ candles) | S4 (V010) | Faible (~5 lignes) | **P0** |
| **G10** | EventChainTracker (séquentiel) | S2 (V022) | Haute (~200 lignes) | **P2** |
| **G11** | required_signals → candlestick patterns | S6 (V048), tous | Moyenne (~40 lignes) | **P1** |
| **G12** | Trailing stop candle-by-candle | S1b (V054 Model 2) | Moyenne (~50 lignes) | **P2** |
| **G13** | Discount/Premium filter (50% range) | S4 (V010) | Faible (~20 lignes) | **P1** |
| **G14** | Break momentum detector | S6 (V048) | Moyenne (~40 lignes) | **P2** |
| **G15** | ATR daily trend (expanding market) | S1b (V054 Model 2) | Faible (~20 lignes) | **P3** |
| **G16** | Session transition tracking | S3 (V066) | Moyenne (~40 lignes) | **P1** |

---

## Détails par gap

### G01 — Opening Range Tracker

**Impact :** S1a (V065), S1b (V054), S6 (V048)

**Problème :** Le moteur ne définit pas de zone "opening range" basée sur le(s) premier(s) candle(s) d'ouverture. Il n'existe pas de concept `opening_range_high` / `opening_range_low` dans les engines.

**Ce qui existe :** `stop_loss_logic.distance: "opening_range"` est référencé dans Session_Open_Scalp mais le calcul réel n'est pas tracé.

**Ce qu'il faut :**
```python
# backend/engines/opening_range.py (~100 lignes)
class OpeningRangeTracker:
    def __init__(self, range_tf: str, range_duration_minutes: int, session_start: str):
        # range_tf: "5m" ou "15m"
        # range_duration_minutes: 5 (V054), 15 (V065/V048)
        # session_start: "09:30"
        pass
    
    def update(self, candle) -> None:
        """Accumule les candles du range."""
        
    @property
    def is_formed(self) -> bool: ...
    
    @property
    def range_high(self) -> float: ...
    
    @property
    def range_low(self) -> float: ...
    
    @property
    def midline(self) -> float:
        return (self.range_high + self.range_low) / 2
```

**Variantes par stratégie :**
| Stratégie | TF Range | Durée | Candles |
|-----------|----------|-------|---------|
| V065 (S1a) | 15m | 15 min (9:30-9:45) | 1 candle 15m |
| V054 (S1b) | 5m | 5 min (9:30-9:35) | 1 candle 5m |
| V048 (S6) | 5m | 15 min (9:30-9:45) | 3 candles 5m |

**Fichiers à modifier :**
- CRÉER : `backend/engines/opening_range.py`
- MODIFIER : `backend/backtest/engine.py` — wirer dans `_process_minute()` ou `_process_candle()`
- MODIFIER : `backend/engines/playbook_loader.py` — nouveau champ `opening_range` dans PlaybookDefinition

---

### G02 — Marubozu unilatéral

**Impact :** S6 (V048)

**Problème :** `candlesticks.py` L216-226 : `_is_bullish_marubozu` et `_is_bearish_marubozu` exigent les DEUX wicks ≤ 5% du body (bilatéral). V048 ne requiert qu'UN seul côté : bullish = no bottom wick, bearish = no top wick.

**Ce qu'il faut :**
```python
# Ajouter dans candlesticks.py :
def _is_bullish_no_bottom_wick(self, candle, threshold=0.02):
    """V048: bullish candle with no bottom wick (low ≈ open)."""
    if candle.close <= candle.open:
        return False
    body = abs(candle.close - candle.open)
    if body == 0:
        return False
    lower_wick = candle.open - candle.low
    return lower_wick <= threshold * body

def _is_bearish_no_top_wick(self, candle, threshold=0.02):
    """V048: bearish candle with no top wick (high ≈ open)."""
    if candle.close >= candle.open:
        return False
    body = abs(candle.open - candle.close)
    if body == 0:
        return False
    upper_wick = candle.high - candle.open
    return upper_wick <= threshold * body
```

**Fichiers à modifier :**
- `backend/engines/patterns/candlesticks.py` — ajouter 2 méthodes

---

### G03 — Retest + Engulfing séquentiel

**Impact :** S1b (V054)

**Problème :** V054 requiert une séquence de 2 candles distinctes : (1) "retest candle" qui revient dans le FVG, (2) candle engulfant le body du retest. Le moteur détecte des patterns chandelier isolés, pas des séquences.

**Ce qu'il faut :**
```python
# Dans signal_detector.py ou nouveau module :
def detect_retest_engulfing(candles, fvg_zone_low, fvg_zone_high, direction):
    """
    Pour LONG :
    1. retest_candle : candle dont le low <= fvg_zone_high (revient dans FVG)
    2. engulfing_candle : candle suivante dont le body englobe le body du retest
       ET close > retest.close
    Retourne (retest_idx, engulfing_idx) ou None.
    """
```

**Fichiers à modifier :**
- `backend/engines/signal_detector.py` ou CRÉER `backend/engines/patterns/retest_engulfing.py`
- `backend/engines/playbook_loader.py` — nouveau champ `confirmation_pattern: "retest_engulfing"`

---

### G04 — Market order at candle close

**Impact :** S1b (V054), S3 (V066), S4 (V010)

**Problème :** Le moteur utilise des limit orders (`type: "LIMIT"`). V054, V066, V010 entrent en MARKET au moment du BOS/engulfing/inversion. En backtest, un market order au close = entrée au open du candle suivant.

**Ce qu'il faut :** Vérifier si `type: "MARKET"` dans le YAML fonctionne déjà correctement. Si oui, le gap est cosmétique (juste changer les YAMLs). Si non, ajouter le support dans `execution_engine.py`.

**Fichiers à vérifier :**
- `backend/engines/execution_engine.py` — vérifier le handling de `type: "MARKET"`

---

### G05 — FVG "hors range" gate

**Impact :** S1a (V065), S1b (V054)

**Problème :** V065/V054 exigent que le FVG ait au moins 1 candle fermant AU-DELÀ du opening range (high ou low). Le détecteur FVG actuel est géométrique (gap entre candles) sans vérification de position relative à un range externe.

**Ce qu'il faut :**
```python
def fvg_breaks_range(fvg_candles, range_high, range_low, direction):
    """Gate binaire : au moins 1 des 3 candles du FVG ferme hors range."""
    for c in fvg_candles:
        if direction == "long" and c.close > range_high:
            return True
        if direction == "short" and c.close < range_low:
            return True
    return False
```

**Fichiers à modifier :**
- `backend/engines/signal_detector.py` — enrichir la détection FVG avec un paramètre `reference_range`

---

### G06 — Session highs/lows consommés

**Impact :** S3 (V066)

**Problème :** V066 retire les session levels déjà atteints. Le moteur n'a pas d'état "consumed" pour les niveaux.

**Ce qu'il faut :** Tracker dans `market_state` un set `consumed_levels` mis à jour quand le prix touche un session high/low.

**Fichiers à modifier :**
- `backend/engines/market_state.py` — ajouter `consumed_session_levels: Set[str]`
- `backend/engines/liquidity.py` — vérifier consumed avant de retourner un niveau

---

### G07 — TP dynamique sur session levels

**Impact :** S3 (V066)

**Problème :** V066 place le TP sur le prochain session low/high intact (pas un RR fixe). Le YAML ne supporte que `tp1_rr: X.X`.

**Ce qu'il faut :** Nouveau type de TP : `type: "SESSION_LEVEL"` qui prend le prochain session low (SHORT) ou high (LONG) non consommé.

**Fichiers à modifier :**
- `backend/engines/playbook_loader.py` — nouveau type TP
- `backend/engines/risk_engine.py` — calculer le TP dynamique à l'ouverture du trade

---

### G08 — Sweep spatial INTO FVG

**Impact :** S4 (V010)

**Problème :** `ifvg.py` ne vérifie pas si le prix a pénétré dans la zone du FVG avant l'inversion. V010 exige : `sweep_low <= fvg_zone_high` (le wick entre dans le FVG).

**Ce qu'il faut :**
```python
# Dans ifvg.py, avant de déclarer une inversion :
wick_penetrated = any(c.low <= fvg.zone_high for c in candles[fvg.end_idx+1:inversion_idx])
if not wick_penetrated:
    continue  # pas un vrai IFVG V010
```

**Fichiers à modifier :**
- `backend/engines/ict/ifvg.py`

---

### G09 — IFVG récence élargie

**Impact :** S4 (V010)

**Problème :** `ifvg.py` : `if idx_end < n - 5: continue` — seuls les FVGs des 5 derniers candles sont considérés. V010 montre des FVGs "way to the left" sur 1H (centaines de candles).

**Ce qu'il faut :** Paramétrer `max_fvg_age_candles` (défaut: 200) au lieu de 5.

**Fichiers à modifier :**
- `backend/engines/ict/ifvg.py` — changer le seuil hardcodé

---

### G10 — EventChainTracker

**Impact :** S2 (V022)

**Problème :** V022 est une stratégie séquentielle : sweep → BOS → confluence → trigger. Chaque étape dépend de la précédente avec des timeouts. Le moteur actuel évalue chaque candle indépendamment.

**Ce qu'il faut :**
```python
# backend/engines/event_chain.py (~200 lignes)
class EventChainTracker:
    def __init__(self, chain_definition: List[ChainStep]):
        self.steps = chain_definition
        self.current_step = 0
        self.step_data = {}
        
    def update(self, candle, signals) -> Optional[str]:
        """Avance la chaîne si la condition du step courant est remplie.
        Retourne 'ENTRY' si la chaîne est complète, None sinon.
        Reset si timeout dépassé."""
```

**Fichiers à modifier :**
- CRÉER : `backend/engines/event_chain.py`
- MODIFIER : `backend/backtest/engine.py` — wirer le tracker
- MODIFIER : `backend/engines/playbook_loader.py` — champ `event_chain` dans PlaybookDefinition

---

### G11 — required_signals → candlestick patterns

**Impact :** S6 (V048), potentiellement tous

**Problème :** `required_signals` gate (playbook_loader.py L735-777) cherche dans `ict_patterns` via `type_map`. Les candlestick patterns (marubozu, engulfing, etc.) ne sont pas dans ce mapping. On ne peut pas écrire `required_signals: ["MARUBOZU@1m"]`.

**Ce qu'il faut :** Étendre `type_map` pour inclure les patterns candlestick, ou ajouter un gate dédié.

**Fichiers à modifier :**
- `backend/engines/playbook_loader.py` — étendre `type_map` ou ajouter gate candlestick

---

### G12 — Trailing stop candle-by-candle

**Impact :** S1b (V054 Model 2)

**Problème :** V054 Model 2 : une fois le niveau 3:1 dépassé, le SL suit le low (LONG) ou high (SHORT) de chaque nouveau candle 1m. Pas de trailing stop dans le moteur actuel.

**Priorité :** P2 — Model 2 est secondaire, Model 1 suffit pour le MVP.

---

### G13 — Discount/Premium filter

**Impact :** S4 (V010)

**Problème :** V010 filtre : LONG si prix < 50% du range du jour (discount), SHORT si prix > 50% (premium). Non implémenté dans les playbooks.

**Ce qu'il faut :** Calculer `equilibrium = (day_high + day_low) / 2` et filtrer en pre-entry.

**Fichiers à modifier :**
- `backend/engines/equilibrium.py` existe déjà — vérifier et exposer comme gate

---

### G14 — Break momentum detector

**Impact :** S6 (V048)

**Problème :** V048 rejette les breaks "soft" visuellement. Pas de détecteur de qualité de break.

**Priorité :** P2 — heuristique, pas un gate binaire dans la vidéo.

---

### G15 — ATR daily trend (expanding market)

**Impact :** S1b (V054 Model 2)

**Priorité :** P3 — Model 2 uniquement.

---

### G16 — Session transition tracking

**Impact :** S3 (V066)

**Problème :** Le moteur n'a pas de logique "London a fait un fakeout → activer le trade NY". Pas de concept de transition inter-session.

**Ce qu'il faut :** État booléen `fakeout_occurred` par session, mis à jour quand le prix dépasse un session high/low.

**Fichiers à modifier :**
- `backend/engines/market_state.py` — ajouter tracking fakeout
- Peut être combiné avec G06 (consumed levels)

---

## Ordre d'implémentation recommandé

### Sprint 1 — Fondations (G01, G02, G04, G05, G09)
Débloque : S1a (V065 fidèle), S1b (V054 Model 1), S6 (V048 partiel)

### Sprint 2 — Entrées avancées (G03, G11, G13)
Débloque : S1b (V054 complet), S4 (V010 partiel), S6 (V048 complet)

### Sprint 3 — Sessions (G06, G07, G08, G16)
Débloque : S3 (V066), S4 (V010 complet)

### Sprint 4 — Séquentiel + avancé (G10, G12, G14, G15)
Débloque : S2 (V022), Model 2 (V054)

---

## Détecteurs existants réutilisables

| Module | Ce qu'il fournit | Stratégies servies |
|--------|-----------------|-------------------|
| `ict.py` | BOS, FVG, liquidity_sweep, OB, SMT, CHOCH | S1, S2, S3, S4, S9 |
| `ifvg.py` | IFVG flip (avec corrections G08/G09) | S4 |
| `order_block.py` | OB zones | S9, S7 |
| `equilibrium.py` | 50% equilibrium | S8, S4 (G13) |
| `candlesticks.py` | marubozu (avec correction G02), engulfing | S6, S1b |
| `liquidity.py` | session highs/lows, sweep detection | S3, S2 |
