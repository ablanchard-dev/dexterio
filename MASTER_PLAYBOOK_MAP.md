# MASTER → Playbook Map

> Mapping entre le savoir du MASTER (transcripts YouTube ICT/smart money)
> et l'état des playbooks dans le repo.
> Dernière mise à jour : 2026-04-14

---

## Vérité timeframe MASTER

Le MASTER n'est **pas** une collection de stratégies 1m natives.

Le framework dominant dans **toutes** les sources ICT du MASTER est :

```
D / 4H  →  biais directionnel (draw on liquidity)
    ↓
15m / 5m  →  sweep de liquidité + confirmation structure (BOS / IFVG)
    ↓
5m / 1m  →  zone d'entrée (OB / FVG / Breaker / EQ)
    ↓
1m  →  exécution / confirmation de bougie
```

Le moteur Dexterio replay sur 1m (correct pour l'exécution). Mais les setups sont **conceptuellement 5m ou 15m** — compresser en 1m natif génère bruit et fréquence excessive.

---

## Familles de setups identifiées dans le MASTER

### Famille A — Sweep + IFVG (la plus représentée)

**Concept** : Price sweeps un niveau de liquidité clé (session high/low, premarket, overnight) → FVG existant se fait invalider → IFVG formé → entrée dans la zone d'inversion.

**Timeframes** :
- Context : 1H / 4H
- Setup : 5m (sweep visible + IFVG identifiable)
- Entry : 1m (confirmation dans la zone)

**Sources MASTER** : VIDEO 010 (Five A+ iFVG Setups), VIDEO 064 (1 Hour Strategy)

**Repo** :
- `playbooks_Aplus_from_transcripts.yaml` → `Aplus_01_MarketOpen_Sweep_IFVG_Breaker` — **research_only, non chargé**
- `engines/patterns/ifvg.py` — code présent, non utilisé en playbook actif
- `NY_Open_Reversal` — concept partiellement aligné, mais codé en 1m sans séquence IFVG propre

**Gap** : IFVG 5m propre non instancié. Code disponible mais playbook manquant.

---

### Famille B — HTF Bias + 15m BOS + Entry confluence

**Concept** : Bias D/4H → identifier 15m sweep aligné avec la narrative → 15m BOS après le sweep → entrée sur confluence (OB / FVG / EQ / Breaker).

**Timeframes** :
- Context : D / 4H
- Setup : 15m (sweep + BOS)
- Entry : 5m / 1m (confirmation dans la confluence)

**Sources MASTER** : VIDEO 022 (9h beginner course), VIDEO 016 (Daily Bias), VIDEO 057 (Top Down Analysis)

**Repo** :
- `playbooks_Aplus_from_transcripts.yaml` → `Aplus_04_HTF_Bias_15m_Sweep_BOS_EntryConfluence` — **research_only, non chargé**
- Pas de playbook actif implémentant cette logique 15m

**Gap** : playbook entièrement manquant dans le moteur actif. Concept non testé.

---

### Famille C — FVG Fill (5m limit order)

**Concept** : Move de breakout crée un FVG 5m net → limit order au milieu du FVG (50%) → TP = prochain draw on liquidity.

**Timeframes** :
- Context : 5m (tendance claire)
- Setup : 5m (FVG créé par le breakout)
- Entry : 5m (limit order) ou 1m (confirmation)

**Sources MASTER** : VIDEO 065 (3 Step A+), VIDEO 009 (Fair Value Gaps), VIDEO 054 (3 Step A+ Scalping)

**Repo** :
- `FVG_Fill_Scalp` — **branché mais en 1m, pas en 5m**
- `playbooks_Aplus_from_transcripts.yaml` → `Aplus_03_IFVG_Flip_from_FVG_Invalidation` — **research_only**

**Gap** : FVG_Fill_Scalp existe mais timeframe mal aligné (1m natif au lieu de 5m). E[R] négatif en OOS core-3. Besoin lab dédié ou refonte YAML 5m.

---

### Famille D — Opening Range Breakout (ORB)

**Concept** : Range des 3 premières bougies 9h30–9h45 → break + Marubozu sur 5m ou 1m → retest du niveau break → limit entry.

**Timeframes** :
- Context : 5m (tendance + range visuel)
- Entry : 1m (marubozu / confirmation)

**Sources MASTER** : VIDEO 048 (1 Minute Scalping — qui est en réalité 5m context + 1m entry), VIDEO 065

**Repo** :
- `Session_Open_Scalp` — branché, mais **LAB ONLY / bloqué runtime edge** (2026-04-09)

**Gap** : playbook existe mais bloqué. Logique partiellement correcte. Libération runtime conditionnelle à levée blocage explicite.

---

### Famille E — News/Event Spike Fade

**Concept** : Spike post-news (CPI, FOMC) → rejection contrarian → fade avec stop au-delà du spike extreme.

**Timeframes** :
- 1m natif réel (spike très court, quelques minutes)

**Sources MASTER** : VIDEO 012 (FOMC $427k), VIDEO 041 (FOMC fullport)

**Repo** :
- `News_Fade` — branché, ALLOWLIST, **gate REOPEN_1R_VS_1P5R ouvert**

**Gap** : gate tp1 non tranché depuis des mois. Sweep 1.0R vs 1.5R sur 12 fenêtres `nf1r_confirm_*` requis avant promotion.

---

### Famille F — Premarket Sweep + 5m Confirm + 5m Continuation

**Concept** : Sweep en premarket → attendre 5m confirmation (BOS / IFVG / 79% extension / SMT) → 5m continuation → entrée sur confluence (OB / Breaker / FVG / EQ).

**Timeframes** :
- Context : D / 4H
- Setup : 5m (confirmation + continuation)
- Entry : 5m / 1m

**Sources MASTER** : VIDEO 022 (checklist 10 étapes)

**Repo** :
- `playbooks_Aplus_from_transcripts.yaml` → `Aplus_02_PremarketSweep_5mConfirm_5mContinuation` — **research_only, non chargé**

**Gap** : entièrement absent du moteur actif. Le moteur ne gère pas les événements premarket dans le pipeline actuel.

---

## Matrice de statut

| Famille | Code moteur | YAML chargé | Campagne | Verdict |
|---------|-------------|-------------|----------|---------|
| A — Sweep + IFVG 5m | `ifvg.py` présent | **Non** | Jamais | **research_only → P2 explorer** |
| B — HTF + 15m BOS | Partiel (MarketState HTF) | **Non** | Jamais | **research_only** |
| C — FVG Fill 5m | `FVG_Fill_Scalp` en 1m | Oui (1m) | E[R] négatif OOS | **mal calibré → lab dédié** |
| D — ORB | `Session_Open_Scalp` | Oui | LAB ONLY | **bloqué runtime** |
| E — News Fade | `News_Fade` | Oui | Gate tp1 ouvert | **P0 clore gate** |
| F — Premarket Sweep 5m | Absent | **Non** | Jamais | **hors scope immédiat** |

---

## Ce que le MASTER ne contient pas

- Stratégies purement 1m natives (le 1m scalping VIDEO 048 utilise quand même 5m en context)
- Stratégies haute fréquence / momentum pur sans contexte HTF
- Validations quantitatives / backtests (c'est du contenu éducatif, pas de la recherche quant)
- Toute logique de gestion de risque adaptée à un moteur algo — le sizing, les guardrails, les caps viennent du repo

---

## Playbooks du MASTER prêts à être instanciés (si moteur peut supporter 5m setup)

Par ordre de priorité :

1. **Aplus_01** — Sweep + IFVG 5m + Breaker/OB/FVG entry 1m
   - Code : `ifvg.py` + `order_block.py` + `breaker_block.py` disponibles
   - Bloquer sur : est-ce que SetupEngineV2 peut détecter un IFVG formé sur une bougie 5m ?

2. **Aplus_03** — IFVG Flip (FVG invalidé → trade dans le sens du flip)
   - Plus simple : juste la logique d'invalidation d'un FVG existant
   - Potentiellement implémentable comme variante de `FVG_Fill_Scalp` avec `confirmation_tf: "5m"`

3. **Aplus_04** — HTF Bias + 15m BOS + confluence
   - Plus complexe : nécessite detection BOS sur 15m
   - Bloquer sur : `setup_engine_v2.py` gère-t-il les BOS multi-tf ?
