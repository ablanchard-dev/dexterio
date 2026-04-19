# Source Truth Pack — VIDEO 048 "My 1 Minute Scalping Strategy (Complete Course)"

**Video file**: `VIDEO 048 — My 1 Minute Scalping Strategy (Complete Course)-B_dVwXYQ-oc`
**Transcript**: `MASTER_FINAL.txt` L25567-25862
**Quality**: MOYENNE-HAUTE (75% codable) — mécanique claire mais plusieurs règles discrétionnaires non quantifiées
**Role in roadmap**: Noyau candidat pour `Session_Open_Scalp` — 1m entry via Marubozu + ORB 5m

---

## 1. Règles mécaniques extraites

### RÈGLE 1 — Opening Range (Step 1 — TF 5m)
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L25585-25601
- **Verbatim**: "come to the five-minute time frame [...] opening range with breakouts [...] custom range, 930 to 945, UTC minus four [...] Those candles are moving, and that is setting up your range [...] that is your range high and your range low"
- **Formulation normalisée**: Sur le TF 5m, marquer le high et le low des 3 premiers candles (9:30-9:45 ET). Ce range = Opening Range (OR). Outil TradingView "Opening Range Breakout" avec paramètre `custom range 9:30-9:45 UTC-4`, période 15 min.
- **Différence vs V065**: V065 utilise le 1er candle 15m (un seul candle, 9:30-9:45). V048 utilise les 3 candles 5m couvrant la même fenêtre de 15 min — mathématiquement identique en termes de high/low du range, mais le TF de travail est 5m ici contre 15m dans V065.

### RÈGLE 2 — Confirmation de tendance (TF 5m — avant et pendant le range)
- **Classification**: HEURISTIQUE À VALIDER
- **Source TXT**: L25603-25605, L25656-25665, L25700-25710, L25736-25748, L25798-25811
- **Verbatim (Day 1)**: "we are clearly in an uptrend, respecting our trend line right here"
- **Verbatim (Day 2)**: "we've got a trend line right there, multiple touches on the trend line [...] we got a break of the trend line finally and a break of the range, which tells us what? It tells us we are now bullish."
- **Verbatim (Day 4)**: "price is in a downtrend [...] price just respected the trend line right there, broke out the bottom right there, so that's telling us what that we want to sell"
- **Verbatim (Day 5)**: "we've got a trend line right here [...] two, three touches right there [...] that is holding the price down [...] we get the break [...] also the break of our trend line. That's two reasons for us to buy."
- **Formulation normalisée**: Tracer une trend line sur le TF 5m (au moins 2-3 touches requises). Le break du range ET de la trend line = signal directionnel fort. Break range seul = signal valide mais moins fort. Direction = sens du break.
- **Problème de codabilité**: "trend line" est dessinée manuellement par le trader. Pas de règle algorithmique précise sur le nombre de touches minimum, l'angle ou la durée. Seulement 2-3 exemples visuels montrés.

### RÈGLE 3 — Break du range : condition d'activation
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L25606-25627, L25668-25673, L25707-25710, L25743-25749, L25806-25810
- **Verbatim (Day 1)**: "we got a break out the top of the range right here, but it wasn't a good break. You want a more significant break [...] We finally get that break out [...] One, two, three, four, five, six, seven green candles in a row, right? Absolutely awesome."
- **Verbatim (Day 2)**: "We just broke out. Oh, man. We broke out of our range high, and now we are looking to buy."
- **Formulation normalisée**: Sur le TF 1m, attendre un break du range (close au-delà du range high ou low). Un break hésitant ("too soft", peu de momentum) est ignoré. Un bon break = plusieurs candles dans le même sens, momentum fort. La direction du break détermine la direction du trade.
- **Ambiguïté**: La définition de "bon break" vs "trop soft" est visuelle, non quantifiée. Le trader rejette deux breaks consécutifs dans Day 1 avant de prendre le troisième. Nombre de candles de confirmation non fixé explicitement (il en cite 7 pour Day 1 mais n'en fait pas une règle générale).

### RÈGLE 4 — Définition exacte du candle "no-wick" / Marubozu (entrée)
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L25591-25598, L25629-25633, L25677-25678, L25693-25695, L25711-25712, L25820-25824
- **Verbatim**: "the no-wick candlestick identifier [...] Bearish, no top wick. Bullish, no bottom wick. [...] These are just going to show us these Meru Botsu candles [...] This is a candle with no bottom wick, and it is a strong level to buy from, very similar to a demand zone."
- **Verbatim (Day 2)**: "We have our no-wick candle right there acting as our demand zone"
- **Verbatim (Day 5)**: "We're looking for that Marubatsu candle, right? A candle with no bottom wick."
- **Définition exacte**:
  - Pour LONG → chercher un candle **bullish** avec **no bottom wick** (le low = l'open du candle)
  - Pour SHORT → chercher un candle **bearish** avec **no top wick** (le high = l'open du candle)
  - Outil utilisé: indicateur TradingView "no-wick candlestick identifier" — paramètre "Bullish: no bottom wick", "Bearish: no top wick", tout le reste désactivé
- **Équivalence engine**: `_is_bullish_marubozu` et `_is_bearish_marubozu` dans `candlesticks.py` utilisent `upper_wick ≤ 0.05×body AND lower_wick ≤ 0.05×body`. **ÉCART CRITIQUE**: V048 requiert seulement l'absence d'UN SEUL wick (le wick côté ouverture), pas des deux. Un candle bullish avec un long upper_wick et zero lower_wick = valide pour V048 mais REJETÉ par l'engine actuel.
- **TF du Marubozu**: Explicitement TF 1m (on switche sur M1 pour chercher le Marubozu)

### RÈGLE 5 — Entrée : attendre le retracement vers le Marubozu
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L25633-25641, L25685-25697, L25713-25716, L25762-25770, L25832-25847
- **Verbatim (Day 1)**: "we're just waiting for the price to come back to that level slowly but surely, and that's where we're going to enter our trading position. Here it comes. One candle at a time all the way down, and then right there, we enter the trading position"
- **Verbatim (Day 2)**: "let this continue to play out as we wait for those candles to cascade to our entry right there"
- **Formulation normalisée**: Après identification du Marubozu 1m, placer un limit order au niveau du Marubozu (le low du candle pour un bullish, le high pour un bearish). Attendre que le prix revienne toucher ce niveau. L'entrée est passive (limit order), pas active (market order). Le Marubozu agit comme zone de demande/offre.
- **Confluence recommandée**: Le Marubozu préféré est celui qui coïncide aussi avec une zone de demande/offre (ex: Day 2: "I like this one better. Why? Because we also have the demand overlap"). Plusieurs Marubozu peuvent apparaître — le trader choisit celui avec le plus de confluences.

### RÈGLE 6 — Stop Loss
- **Classification**: HEURISTIQUE À VALIDER
- **Source TXT**: L25643-25644, L25687-25688, L25716-25717, L25763-25765, L25837-25839
- **Verbatim (Day 1)**: "for my stop loss, I had it below that mid-range line right there"
- **Verbatim (Day 2)**: "I'm going to set my stop loss this time just below our range right there, not all the way down here because I want better risk-reward"
- **Verbatim (Day 3)**: "Have the stop loss below the range midline, something like that"
- **Verbatim (Day 4)**: "Stop loss can be above the range"
- **Verbatim (Day 5)**: "Let's have the stop loss below the range midline"
- **Formulation normalisée**: Deux niveaux de SL utilisés selon le contexte:
  1. **SL midrange** (Day 1, 3, 5): SL sous/sur la ligne médiane du OR (= mid entre range high et range low). Favorisé pour meilleur RR.
  2. **SL range complet** (Day 2, 4): SL sous/sur l'extrémité entière du OR. Utilisé quand l'entrée est proche du range.
- **Priorité implicite**: Le trader préfère le SL midrange pour avoir un meilleur RR mais accepte le SL range complet si l'entrée est déjà proche du midpoint.
- **Non quantifié**: "mid-range line" = (range_high + range_low) / 2 semble implicite mais jamais énoncé explicitement.

### RÈGLE 7 — Take Profit
- **Classification**: HEURISTIQUE À VALIDER
- **Source TXT**: L25644-25646, L25836-25837
- **Verbatim (Day 1)**: "for my take profit, I was just taking profit right here at recent consolidation at this recent level of resistance right there"
- **Verbatim (Day 5)**: "Let's put the take profit at resistance"
- **Formulation normalisée**: TP = prochain niveau de résistance/support récent (pour LONG = résistance, pour SHORT = support). Pas de RR fixe mentionné — contraste avec V065 qui impose 2:1 fixe.
- **Note Day 4**: Le trader mentionne "at this level right here, if I was on stream, I'd probably take a take partial one" → partial TP discretionnaire en live, mais ne définit pas de règle précise. En backtest, il laisse aller jusqu'au TP principal.
- **ÉCART vs V065**: V065 impose 2:1 RR fixe. V048 impose TP au niveau de R/S récent, ce qui peut donner un RR variable (parfois < 1:1, parfois >> 2:1).
- **ÉCART vs Session_Open_Scalp playbook**: Le playbook actuel définit `tp1_rr: 1.5` et `tp2_rr: 2.0` avec `breakeven_at_rr: 1.0`. V048 ne mentionne pas de breakeven et utilise un seul TP cible.

### RÈGLE 8 — Session / Fenêtre de trading
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L25570-25578, L25587-25590
- **Verbatim**: "I trade for just two hours [...] one trade per day, five days, and two hours of trading [...] 930 to 945, UTC minus four [...] 9.30 a.m., the New York Stock Exchange open"
- **Formulation normalisée**: Fenêtre = 9:30-11:30 ET (deux heures post-open NYSE). La fenêtre exacte de fermeture n'est pas énoncée explicitement comme 11:30 — seulement "two hours". La setup commence à 9:30 (range formation), le trade peut s'exécuter pendant cette fenêtre.
- **ÉCART vs Session_Open_Scalp**: Le playbook définit `time_range: ["03:00", "03:15", "09:30", "09:45"]` — fenêtre très étroite (15 minutes) qui couvre seulement la formation du range, pas la phase d'attente du retracement. La fenêtre V048 est ~2h.

### RÈGLE 9 — Conditions de non-trade
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L25607-25621, L25718-25734
- **Verbatim (Day 1, soft break rejeté)**: "it wasn't a good break. You want a more significant break [...] Not a great break out, right? A little too soft. We want to see something with more momentum. We want to see a big, big push."
- **Verbatim (Day 3, trade manqué)**: "we seem to be missing the trading opportunity here. It doesn't look like it's going to come our way [...] it shot up, so we missed the move today"
- **Verbatim (Day 4, stop loss touché)**: "the strategy isn't going to work every single time"
- **Formulation normalisée**:
  1. Pas de trade si le break manque de momentum (trop soft, pas de candles consécutifs)
  2. Pas de trade si le prix ne revient pas au niveau du Marubozu (le retracement ne se produit pas)
  3. Un stop loss = résultat normal, pas de condition d'arrêt supplémentaire
- **Non mentionné**: Pas de filtre "no news", pas de filtre de volatilité, pas de filtre de session London.

---

## 2. Éléments HEURISTIQUES (à valider)

### HEURISTIQUE 1 — Confluence Marubozu + zone de demande/offre
- **Classification**: HEURISTIQUE À VALIDER
- **Source TXT**: L25630-25634, L25683-25686, L25711-25712, L25756-25762, L25827-25835
- **Verbatim**: "we also actually have a demand zone at that level, so it's a good overlap" / "I like this one better. Why? Because we also have the demand overlap." / "You want to have confluences that add up."
- **Problème**: Le trader préfère les Marubozu qui coïncident avec une zone de demande/offre mais prend aussi des trades sans cette confluence (Day 3, Day 4). La confluence augmente la conviction mais n'est pas un gate binaire.
- **Seuil de calibration**: Non défini. "Demand zone" vient d'un indicateur séparé ou de l'analyse visuelle des bougies précédentes ("four green candles in a row").

### HEURISTIQUE 2 — Qualité du break (momentum)
- **Classification**: HEURISTIQUE À VALIDER
- **Source TXT**: L25607-25626
- **Verbatim**: "not a great break out, right? A little too soft. We want to see something with more momentum. We want to see a big, big push. [...] One, two, three, four, five, six, seven green candles in a row, right? Absolutely awesome."
- **Problème**: "Bon break" = visuellement identifié, sans seuil quantitatif précis. Critères possibles à valider: nombre de candles consécutifs (≥3? ≥5?), taille relative des candles, absence de mèches longues sur les candles de break.

### HEURISTIQUE 3 — Sélection du meilleur Marubozu quand plusieurs sont présents
- **Classification**: HEURISTIQUE À VALIDER
- **Source TXT**: L25675-25685, L25755-25762, L25826-25832
- **Verbatim (Day 2)**: "I see a level right here [...] Now, we have another one right here, too [...] I like this one better. Why? Because we also have the demand overlap."
- **Verbatim (Day 4)**: "We've got a Marubatsu candle there, Marubatsu candle there, Marubatsu candle right there [...] Which one do I like? I like this one right here. Why? Because it's a supply, right? That's the beginning of the down move."
- **Règle implicite**: Priorité = Marubozu le plus proche du début du mouvement (le premier de la séquence de break) ET celui qui coïncide avec une zone S/R existante. Non codable sans quantification.

---

## 3. Contexte discrétionnaire (non codable)

- **Contexte Day 4**: "if I was on stream, I'd probably take a take partial one. Definitely watch my streams to see how I trade live with discretion." — La gestion live diffère du backtest présenté. Partial TP, trail, etc.
- **Pairs tradées**: Plusieurs paires Forex mentionnées ("these are all the pairs I trade here in my market watch") — la vidéo est orientée Forex, pas actions US. SPY/QQQ sont une adaptation.
- **Résultat backtest affiché**: 4 jours sur 5 = wins. Day 3 = miss (prix n'est pas revenu). Day 4 = stop loss. Pas de statistiques formelles présentées.
- **Fréquence**: "one trade per day, five days" → max 1 trade/jour, fenêtre de 2h.

---

## 4. Bruit / marketing (ignoré)

- L25570-25576: Introduction / hook marketing
- L25583: "come to freetradingview.com" — placement produit
- L25652-25654: Broker Triple AFX mention anticipée
- L25785-25793: "I'm trading with the Triple AFX. This is a broker. [...] click the link in the description." — pub broker
- L25852-25858: "consider joining my VIP trading room. We've got an undefeated week going right now."

---

## 5. Résumé stratégie V048 (implémentable)

```
TIMEFRAME: 5m (range + tendance) → 1m (break + Marubozu + entrée)
SESSION: 9:30-11:30 ET (2 heures post-open NYSE)
MAX TRADES: 1 par jour

STEP 1 — RANGE (9:30-9:45 ET, TF 5m):
  - Marquer high et low des 3 premiers candles 5m
  - = Opening Range (OR) du jour

STEP 2 — TENDANCE (TF 5m):
  - Tracer trend line (≥2 touches)
  - Identifier direction dominante (uptrend / downtrend)
  - Confirme la direction attendue du trade

STEP 3 — BREAK DU RANGE (TF 1m):
  - Attendre break avec momentum (plusieurs candles consécutifs)
  - Break "soft" ignoré — attendre un break fort
  - Break haussier → LONG. Break baissier → SHORT.
  - Confluence forte si break coïncide avec break de trend line 5m

STEP 4 — MARUBOZU 1m (trigger d'entrée):
  - Sur TF 1m: identifier candle "no-wick" unilatéral
    * LONG: candle bullish sans bottom wick (low = open)
    * SHORT: candle bearish sans top wick (high = open)
  - Choisir le Marubozu avec le plus de confluences (demand/supply zone)
  - Placer limit order au niveau du Marubozu

STEP 5 — ENTRÉE (passive):
  - Attendre retracement vers le niveau du Marubozu
  - Si prix ne revient pas → pas de trade (miss acceptable)

STEP 6 — STOP LOSS:
  Option A (préférée): SL sous/sur la midline du OR = (OR_high + OR_low) / 2
  Option B (fallback): SL sous/sur l'extrémité entière du OR

STEP 7 — TAKE PROFIT:
  - TP = prochain niveau de résistance/support récent
  - Pas de RR fixe imposé (variable selon le niveau R/S)

FILTERS:
  - Break fort obligatoire (gate qualitatif)
  - Si retracement ne se produit pas → pas de trade
  - Max 1 trade/jour
```

---

## 6. Comparaison avec VIDEO 065

| Dimension | V048 (1m Scalping) | V065 (3-Step A+) |
|-----------|-------------------|------------------|
| TF range | 5m (3 candles, 9:30-9:45) | 15m (1 candle, 9:30-9:45) |
| TF setup | 5m (tendance + break) | 5m (break + FVG) |
| TF entrée | 1m (Marubozu) | 5m (FVG limit order) |
| Trigger d'entrée | Marubozu 1m unilatéral + retracement | FVG 5m, limit order à 50% |
| Tendance | Trend line 5m explicite (2-3 touches) | Implicite dans le sens du break |
| Validation du break | Momentum fort (subjectif) | FVG obligatoire (gate binaire) |
| Stop Loss | Midrange OR ou OR complet | Low/high du candle 1 du FVG |
| Take Profit | Niveau R/S récent (variable) | 2:1 RR fixe |
| Session | 9:30-11:30 ET (2h) | 9:45-12:00 ET (2h15) |
| Max trades/jour | 1 | 1 (implicite) |
| Codabilité | 75% | 90% |

**Différence fondamentale**: V065 est entièrement piloté par les FVG (structure de marché formelle ICT) et use un RR fixe. V048 est piloté par la lecture de momentum visuel (Marubozu + trend line) avec TP discrétionnaire. V048 est plus difficile à mécaniser fidèlement.

---

## 7. Comparaison avec `Session_Open_Scalp` playbook actuel

Fichier: `/home/dexter/dexterio1-main/backend/knowledge/playbooks.yml` L630-696

| Paramètre | Session_Open_Scalp (actuel) | V048 (vérité source) | Écart |
|-----------|----------------------------|---------------------|-------|
| `time_range` | `["03:00", "03:15", "09:30", "09:45"]` | 9:30-11:30 ET | **ÉCART MAJEUR**: fenêtre actuelle = 15 min, V048 = 2h. Le playbook ferme la fenêtre au moment où le range vient juste de se former. |
| `session` | `ANY` | NY uniquement (9:30 ET) | Écart mineur — le filtre session ANY sans filtre horaire laisse passer London (03:00-03:15), ce qui n'existe pas dans V048. |
| `setup_tf` | `5m` | 5m | OK |
| `confirmation_tf` | `1m` | 1m | OK |
| `entry_logic.type` | `MARKET` | `LIMIT` (retracement vers Marubozu) | **ÉCART**: Market order = entrée immédiate. V048 = limit order passif qui attend le retracement. |
| `entry_logic.zone` | `range_break` | range_break + Marubozu retest | Partiel — le range_break est correct mais le retest Marubozu n't est pas modélisé. |
| `candlestick_patterns` | `required_families: [marubozu, engulfing, hammer, shooting_star]` | marubozu unilatéral uniquement | **ÉCART**: Le playbook accepte 4 familles. V048 n'utilise QUE le Marubozu unilatéral. Engulfing/hammer/shooting_star sont hors scope V048. |
| `stop_loss_logic.type` | `FIXED` | midrange ou range complet | Partiellement aligné — "FIXED distance: opening_range" mais V048 préfère midrange. |
| `take_profit_logic` | `tp1_rr: 1.5, tp2_rr: 2.0, breakeven_at_rr: 1.0` | TP au niveau R/S récent (variable) | **ÉCART**: RR fixe vs TP discrétionnaire. breakeven_at_rr n'existe pas dans V048. |
| `max_duration_minutes` | `15` | ~2h (120 min) | **ÉCART MAJEUR**: 15 min ne permet pas d'attendre le retracement vers le Marubozu. |
| `scoring.weights` | `range_quality: 0.40, pattern_quality: 0.35, volume: 0.25` | Pas de scoring — gate binaire + confluence qualitative | Scoring artificiel sans fondement dans la source. |

**Synthèse écarts playbook**: Le playbook actuel `Session_Open_Scalp` capture l'intention générale (range open + candle pattern) mais implémente incorrectement presque tous les paramètres de timing et d'exécution. Il s'agit d'une approximation construite sans référence directe à la source V048.

---

## 8. Gaps engine

### GAP 1 — Marubozu unilatéral non implémenté (CRITIQUE)
- **Fichier**: `/home/dexter/dexterio1-main/backend/engines/patterns/candlesticks.py` L216-226
- **Problème**: `_is_bullish_marubozu` requiert `upper_wick ≤ 0.05×body AND lower_wick ≤ 0.05×body` (bilatéral). V048 requiert seulement l'absence du wick du côté de l'ouverture (unilatéral): bullish = `lower_wick ≤ X×body` (sans contrainte sur upper_wick). Un bullish Marubozu V048 avec un long upper_wick est REJETÉ par l'engine actuel.
- **Impact**: L'engine ne peut pas détecter correctement les candles "no bottom wick" (bullish) ou "no top wick" (bearish) au sens V048.
- **Correction nécessaire**: Ajouter `_is_bullish_no_bottom_wick` et `_is_bearish_no_top_wick` avec seuil configurable (ex: `lower_wick ≤ 0.02×body` pour bullish).

### GAP 2 — required_signals gate non branché aux candlestick patterns
- **Fichier**: `/home/dexter/dexterio1-main/backend/engines/playbook_loader.py` L735-777
- **Problème**: `required_signals` gate cherche dans `ict_patterns` (IFVG, OB, EQ, BRKR) via `type_map`. Le mot clé `marubozu` n'est pas dans le `type_map` et le système ne connecte pas `CandlestickPatternEngine` à ce gate. On ne peut pas écrire `required_signals: ["marubozu_bullish@1m"]` et obtenir un vrai gate.
- **Impact**: Le champ `candlestick_patterns.required_families` dans le playbook est une déclaration non contraignante — non vérifiée dans le gate d'activation du playbook. Le gate est cosmétique.
- **Correction nécessaire**: Étendre `required_signals` pour inclure les patterns candlestick dans la recherche, OU ajouter un gate dédié `required_candlestick_patterns` qui vérifie `CandlestickPatternEngine` output.

### GAP 3 — Opening Range tracking non implémenté comme structure persistante
- **Classification**: HEURISTIQUE À VALIDER (si critère midrange requis)
- **Problème**: L'engine calcule des niveaux de range pour le SL (`distance: "opening_range"`) mais il n'est pas clair que la midline du range soit calculée et disponible comme niveau de SL distinct. V048 préfère le SL à la midrange plutôt qu'au range complet.
- **Impact**: Le SL risque d'être systématiquement trop large (range complet) au lieu d'être à la midline, dégradant le RR.
- **Vérification requise**: Inspecter comment `opening_range` est calculé dans le moteur de risk (non vérifié dans cette session).

### GAP 4 — Momentum du break non codé
- **Problème**: Il n'existe pas de détecteur de "qualité du break" (nombre de candles consécutifs, absence de mèches) dans le moteur actuel. V048 filtre visuellement les breaks "soft".
- **Impact**: L'engine pourrait déclencher sur des breaks faibles que V048 ignorerait.
- **Correction possible**: Ajouter un compteur de candles consécutifs dans le même sens lors du break (≥ N candles sans wick supérieur/inférieur significatif).

---

## 9. Vérifications vidéo requises

| # | Point à vérifier | Ligne TXT | Bloquant? |
|---|------------------|-----------|-----------|
| 1 | Seuil exact "no bottom wick" — % du body ou absolu zéro? | L25592-25597 | **OUI** — impacte l'implémentation du détecteur Marubozu |
| 2 | Fenêtre exacte de fin: "two hours" = 11:30 ET ou variable? | L25577 | OUI — impacte time_range |
| 3 | Règle de momentum du break: ≥N candles ou qualitatif? | L25618-25626 | OUI — détermine si c'est codable |
| 4 | Midrange SL: formule (high+low)/2 ou visuelle? | L25643-25644 | Moyen — probable mais non confirmé |
| 5 | TP: niveau R/S récent = dernier swing high/low ou indicateur? | L25644-25646 | Moyen — impact RR |
| 6 | Confluence demande/offre = obligatoire ou préférée? | L25683-25686 | Moyen — gate vs bonus |
| 7 | Trend line: minimum de touches requis (2? 3?) | L25656-25657 | Moyen — impact filtre tendance |
| 8 | Day 5: "a level that was used as resistance [...] as support, as support again" — cette confluence triple est-elle requise ou exemple? | L25831-25834 | Non — informatif |

**Verdict**: 3 points critiques (GAP 1 Marubozu unilatéral, fenêtre 2h, momentum break) doivent être résolus avant implémentation fidèle. Le noyau est codable à ~75% avec les informations du TXT seul.
