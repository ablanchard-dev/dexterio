# Source Truth Pack — VIDEO 066 "This Simple Strategy Made Me My First $100k"

**Video file**: `videos/This Simple Strategy Made Me My First $100k-CPPREA-6ubY.mp4`
**Transcript**: `MASTER_FINAL.txt` L44844-44515
**Quality**: MOYENNE-HAUTE (70% codable — stratégie nette mais démo visuelle lourde, quelques étapes implicites)
**Role in roadmap**: Noyau 2 — LONDON FAKEOUT (stratégie distincte de V065, timeframe Forex/London)

---

## 1. Règles mécaniques extraites

### RÈGLE 1 — Sessions à marquer (3 sessions obligatoires)
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L45003-45097
- **Verbatim**: "The first thing that we have to understand, the session times [...] Asian session starts [...] 1800 [...] it ends at three [...] London session [...] starts at three, and then it ends at eight [...] New York is from eight to 1600"
- **Formulation normalisée** (en New York time / UTC-4):
  - Asian session : 18:00 → 03:00 ET
  - London session : 03:00 → 08:00 ET (pre-market commence à 02:00 mais on marque à 03:00)
  - New York session : 08:00 → 16:00 ET
- **Note**: Le trader opère sur GBP/JPY et GBP/USD. Pour US indexes, NY session s'applique à la place de London — voir RÈGLE 7.
- **VIDÉO À VÉRIFIER**: [ ] Confirmer les heures exactes sur l'indicateur session montré dans la vidéo.

### RÈGLE 2 — Marquer les highs/lows de chaque session
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L45049-45097
- **Verbatim**: "once we have these session times, we're going to want to be able to mark out the highs and the lows of every single session [...] from 1800 to three, we're going to mark out the high [...] Low [...] we're going to mark out London session high and London session low [...] New York session [...] mark out the highs and lows of that as well"
- **Formulation normalisée**: Marquer HIGH et LOW de chaque session (Asian, London, New York) sur le chart. Ce sont les niveaux de liquidité cibles.
- **Règle de mise à jour des niveaux**: L45230-45237 — "if Asian session has already pushed past the New York low, we no longer care about this level. Why? Because it's already been pushed past." → Si un niveau de session précédente a déjà été atteint/cassé, on le supprime. Seuls les niveaux intacts restent actifs.
- **VIDÉO À VÉRIFIER**: [ ] Screenshot montrant les 3 sessions marquées simultanément.

### RÈGLE 3 — London Fakeout : définition exacte
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L44910-44984
- **Verbatim**: "London session would open and then it would move up drastically. And then it would just go in the opposite direction [...] I would wait for London session to open. I would wait for it to do a fantastic move [...] boom, it's going up, boom, press short [...] this is a London session fake out"
- **Formulation normalisée**:
  - London session fakeout HAUSSIER : London ouvre et monte au-dessus d'un session high précédent (Asian high ou NY high) → setup SHORT (le move sera vers le bas)
  - London session fakeout BAISSIER : London ouvre et descend en-dessous d'un session low précédent (Asian low ou NY low) → setup LONG (le move sera vers le haut)
  - **Condition nécessaire** : le move London doit **dépasser** un session high ou session low précédent. L45243-45249 : "the second that we are able to push above a session high, whether it's Asian session high or New York session high, I'm immediately going to the five minute timeframe"
- **Ce que ce n'est PAS** : un simple move directionnel sans atteindre un session high/low ne constitue pas un fakeout.

### RÈGLE 4 — BOS : définition exacte (Break of Structure)
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L45101-45214
- **Verbatim**: "A low consists of a move down than a move up and the lowest point of those two candlestick wicks. A high consists of a move up than a move down and the highest point of those two candlestick wicks. For us to break structure, we have to have a candle close underneath the low [...] we only see wicks go underneath the low [...] No, we do not. We only see wicks go underneath the low. And then we continue the uptrend"
- **Formulation normalisée** :
  - Un LOW valide = point le plus bas entre un mouvement down puis up (2 jambes). Marqué sur le wick le plus bas.
  - Un HIGH valide = point le plus haut entre un mouvement up puis down (2 jambes). Marqué sur le wick le plus haut.
  - BOS valide = CANDLE CLOSE en-dessous du low valide (pour BOS bearish) ou au-dessus du high valide (pour BOS bullish)
  - **Gate critique** : un simple wick qui transperce le niveau NE COMPTE PAS. Il faut une clôture de candle.
  - Timeframe de détection BOS : **5 minutes** (L44966 : "what if I just wait for the five minute to change its trend?", L44980 : "we wait for London session to break structure to the downside")

### RÈGLE 5 — Condition d'entrée dans le trade
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L45200-45266
- **Verbatim**: "Move down than a move up. We mark out that low. And then what do we see? A black candlestick closure underneath the low. Okay. Once we get that, that was my sign at the time to just go ahead and enter."
- **Formulation normalisée** :
  1. London session fakeout confirmé (prix dépasse un session high ou low)
  2. Sur 5m, identifier le plus récent low/high VALIDE (2 jambes)
  3. Attendre une candle close SOUS ce low (pour SHORT) ou AU-DESSUS de ce high (pour LONG)
  4. Entrée : immédiatement après la clôture de la candle BOS
  5. Mise à jour en temps réel : si un nouveau low/high se forme avant BOS, on surveille le nouveau niveau (L45250-45263 : "Do we get a break of structure here? No. Now I'm monitoring these lows because these are the new lows that got made.")
- **Note** : L'entrée est apparemment MARKET au moment du BOS (pas de limit order contrairement à V065). Le trader dit "I would press short."

### RÈGLE 6 — Stop Loss
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L44984-44986, L45264-45265
- **Verbatim**: "I would put my stop loss above the high of the London session fake out" / "my stop loss are above these highs"
- **Formulation normalisée** :
  - SL SHORT = au-dessus du HIGH du London fakeout move (le sommet atteint pendant le fakeout)
  - SL LONG = en-dessous du LOW du London fakeout move (le bas atteint pendant le fakeout)
  - Le SL se place sur l'extrême du fakeout, pas sur le swing le plus récent.

### RÈGLE 7 — Take Profit : session lows/highs précédents
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L45266-45282, L45337-45387
- **Verbatim**: "for targets, what was I doing? I was simply just targeting the previous session lows [...] I would have wanted to target that as a second take profit [...] I enter right here. My stop loss are above these highs and we can go ahead and target Asian session lows. One to three risk to reward ratio"
- **Formulation normalisée** :
  - TP1 = low/high de la session la plus proche encore intact (ex : Asian session low si trade SHORT)
  - TP2 = low/high de sessions précédentes additionnelles (ex : NY session low)
  - RR cible : **1:3 à 1:5.6** selon la distance des niveaux (L45283 : "one to three", L45380-45385 : "1 to 4 risk to reward [...] 1 to 4.4 [...] 1 to 5.4 [...] 1 to 5.63")
  - Règle de sélection des niveaux : Si le niveau de session précédente a déjà été pris pendant Asian, on retire ce niveau et on cible le suivant.
  - **Ce n'est PAS un RR fixe** — le RR dépend de la distance aux niveaux de session.

### RÈGLE 8 — Fenêtre temporelle
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L44910-44915, L44999-45003
- **Verbatim**: "I was trading London session on GBP JPY and GBP USD [...] I was in California at the time [...] end of Asian session going into London session" / "at least for the foreign exchange part"
- **Formulation normalisée** :
  - **Pour Forex** : London session = 03:00-08:00 ET. Le fakeout se produit à l'ouverture de London (03:00-05:00 ET typiquement).
  - **Pour US indexes** : Le trader mentionne vouloir montrer l'application aux indexes (L44893-44898) mais coupe la vidéo avant (L45398-45407 : "I'm going to go ahead and end the video here"). Le même schéma s'applique avec NY session ouvrant à 08:00 ET.
  - Exemple concret d'application NY donné en fin de vidéo (L45345-45395) : NY session ouvre → push sous London session lows → BOS → entrée → cible London session high.

### RÈGLE 9 — Condition NO-TRADE : niveaux déjà atteints
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L45230-45239
- **Verbatim**: "if Asian session has already pushed past the New York low, we no longer care about this level. Why? Because it's already been pushed past. So we can go ahead and get rid of this."
- **Formulation normalisée** : Si un session level a été atteint/cassé par une session précédente, ce niveau n'est plus une cible valide. Il faut retirer les niveaux "déjà consommés" et ne cibler que les niveaux intacts.

### RÈGLE 10 — SMT / Corrélation NQ-ES
- **Classification**: NON MENTIONNÉ dans cette vidéo
- **Note** : Le trader ne mentionne pas de SMT divergence (NQ/ES) dans cette vidéo. La stratégie est présentée sur Forex (GBP/JPY, GBP/USD) uniquement. L'extension US indexes est annoncée mais non livrée dans cette vidéo.

---

## 2. Éléments HEURISTIQUES (à valider)

### HEURISTIQUE 1 — Identification du "fantastic move" London
- **Classification**: HEURISTIQUE À VALIDER
- **Source TXT**: L44947-44948
- **Verbatim**: "I would wait for London session to open. I would wait for it to do a fantastic move."
- **Problème** : Le trader ne quantifie pas ce qu'est un "fantastic move". Il dit juste "it moves up drastically." Y a-t-il un seuil en pips/ticks ou en % du range Asian ?
- **Impact algo** : Sans seuil, toute transgression d'un session high compte comme fakeout déclencheur. Probablement une simple clôture de candle 5m au-dessus du session high suffit (cohérent avec la logique BOS appliquée).

### HEURISTIQUE 2 — "Minimum N candles" pour BOS
- **Classification**: HEURISTIQUE À VALIDER
- **Source TXT**: L45155-45214
- **Verbatim**: "we have to have a candle close underneath the low" — le trader parle d'UNE candle close.
- **Problème** : Le titre du task mentionne "minimum 3 bearish candles" mais cette vidéo ne mentionne PAS cette règle. UNE seule candle close sous le low suffit selon le TXT. La règle "3 candles" n'est pas de V066.
- **VIDÉO À VÉRIFIER**: [ ] Confirmer qu'une seule candle close suffit — pas de règle de 3 candles bearish ici.

### HEURISTIQUE 3 — Application aux US indexes (NY session)
- **Classification**: HEURISTIQUE À VALIDER
- **Source TXT**: L45345-45395
- **Verbatim**: "New York session opens. When do we push underneath those lows? Right here. When do we get the break of structure? Right here."
- **Problème** : L'exemple NY est bref, non commenté en détail, et le trader dit "I'm going to go ahead and end the video here because I don't want to overcomplicate you guys." La mécanique est identique mais les horaires et niveaux changent. Pour les indexes, le fakeout peut venir de NY session qui dépasse London highs/lows.
- **Impact algo** : Pour SPY/QQQ, remplacer "London session fakeout" par "NY session fakeout sur niveaux London/Asian". C'est conceptuellement le même pattern, session décalée.

---

## 3. Contexte discrétionnaire (non codable mais informatif)

- **Histoire personnelle** : Le trader décrit comment il a découvert ce pattern empiriquement en se faisant stopper out des deux côtés (L44910-44966). La stratégie est née d'une observation simple : "London session moves up, then goes down."
- **Instruments originaux** : GBP/JPY et GBP/USD pendant London session depuis la Californie (lycée). Ce ne sont PAS les instruments du repo (SPY/QQQ). L'adaptation aux indexes est laissée au viewer.
- **Win rate modeste** : L44997-44999 : "my win rate wasn't crazy. I was still taking losses, but this helped me pass funded accounts." Le trader ne donne PAS un win rate spécifique pour cette stratégie dans cette vidéo (contrairement à V065 qui montrait 81%).
- **Résultats affichés** : Exemple 4 sessions : +5.5% après un trade stoppé, puis +11% sur le 3e trade (1:4.4 à 1:5.63 RR). C'est de la demo/cherry-pick potentiellement.

---

## 4. Bruit / marketing (ignoré)

- L44847-44891 : Intro baskettball analogy ("you just need to master just a couple skills") — storytelling
- L44863-44869 : Plug vers "free course" en description — pub
- L45103-45104 : "Again, I explained that super in depth in the free course" — plug récurrent
- L45398-45513 : Outro mentorship / Discord plug — 115 lignes de marketing pur

---

## 5. Résumé des vérifications vidéo requises

| # | Point à vérifier | Ligne TXT | Bloquant? |
|---|-------------------|-----------|-----------|
| 1 | Heures exactes des sessions sur indicateur | L45003-45044 | Non — heures textuelles claires |
| 2 | Screenshot "push above session high" → déclenche monitoring 5m | L45243-45249 | Non — règle textuelle claire |
| 3 | Confirmer BOS = 1 candle close (pas 3) | L45163-45206 | **OUI** — vérifier si le trader montre plus d'un candle |
| 4 | Identifier le HIGH exact du "fakeout" pour SL | L44984-44986 | Non — rule dit "above the high of the London session fake out" |
| 5 | Confirmer entrée MARKET (pas LIMIT) au BOS | L45206-45210 | **OUI** — TXT dit "enter" sans préciser le type |
| 6 | Quantifier le "fantastic move" (seuil?) | L44947-44948 | Non bloquant — seuil implicite = dépasser session H/L |
| 7 | Voir l'exemple NY indexes de fin de vidéo | L45345-45395 | **OUI** — critique pour adaptation SPY/QQQ |
| 8 | Confirmer niveaux retirés en temps réel | L45230-45237 | Non — règle textuelle claire |

---

## 6. Analyse comparative : V066 vs playbooks existants

### NY_Open_Reversal (playbooks.yml L9)

| Dimension | V066 London Fakeout | NY_Open_Reversal (YAML) |
|-----------|---------------------|-------------------------|
| Session | London (03-08 ET) / NY pour indexes | NY uniquement (09:30-11:00 ET) |
| Instrument | GBP/JPY, GBP/USD (Forex) | SPY, QQQ |
| Trigger | Push au-dessus/en-dessous d'un SESSION HIGH/LOW | london_sweep_required: true |
| BOS | Candle close sous le low valide 5m | require_bos: false (!) |
| Entrée | MARKET après BOS (implicite) | LIMIT à pattern_close |
| SL | Au-dessus du HIGH du fakeout move | recent_swing (SWING) |
| TP | Session lows précédents (1:3 à 1:5.6) | min_rr: 3.0, tp1_rr: 3.0 |
| Candlestick patterns | Non requis dans V066 | engulfing, pin_bar, morning_star... |

**Verdict** : NY_Open_Reversal est une adaptation PARTIELLE du London Fakeout — il capture l'idée de sweep London + reversal NY, mais :
- Il inverse la logique d'entrée (LIMIT vs MARKET au BOS)
- Il ignore complètement le BOS 5m comme trigger (require_bos: false)
- Il exige des patterns chandelier non mentionnés dans V066
- Il manque la logique de ciblage sur session lows (TP fixe vs niveaux dynamiques)
- **Le london_sweep_required: true est le seul point commun solide.**

### London_Sweep_NY_Continuation (playbooks.yml L79)

| Dimension | V066 London Fakeout | London_Sweep_NY_Continuation (YAML) |
|-----------|---------------------|--------------------------------------|
| Session | London pour Forex, NY pour indexes | NY (09:30-12:00 ET) |
| Direction | CONTRA London fakeout move | Continuation du sens London |
| BOS | Requis (gate binaire sur 5m) | require_bos: true — mais logique différente |
| Entrée | Market au BOS | MARKET à bos_confirmation |

**Verdict** : London_Sweep_NY_Continuation est **fondamentalement différent** de V066. V066 est un REVERSAL (contra le move London) ; London_Sweep_NY_Continuation est une CONTINUATION (dans le sens London). Ce sont des stratégies opposées. Nom trompeur.

### Morning_Trap_Reversal (playbooks.yml L212)

| Dimension | V066 London Fakeout | Morning_Trap_Reversal (YAML) |
|-----------|---------------------|------------------------------|
| Session | London + NY | NY (09:30-10:30 ET) |
| Trigger | Sweep de session H/L + BOS 5m | require_sweep: true, require_bos: false |
| SL | Au-dessus du fakeout extreme | trap_extreme — correspond ! |
| Candlestick | Non requis | shooting_star, hammer, engulfing... |

**Verdict** : Morning_Trap_Reversal capture le mieux l'esprit de V066 côté NY — le stop_loss_logic.distance: "trap_extreme" est le seul paramètre exact. Mais il manque le BOS comme gate obligatoire et les session lows comme TP.

---

## 7. ÉCARTS identifiés entre V066 et les playbooks existants

### ÉCART 1 — BOS manquant dans NY_Open_Reversal (CRITIQUE)
- **Dans V066** : BOS 5m (candle close sous le low valide) est le **gate d'entrée obligatoire** — sans BOS, pas de trade.
- **Dans YAML** : `NY_Open_Reversal.ict_confluences.require_bos: false`
- **Impact** : Le playbook peut déclencher des trades sans confirmation BOS → faux signaux, exactement ce que V066 cherche à éviter.

### ÉCART 2 — TP dynamique sur session lows absent
- **Dans V066** : Le TP est positionné sur les session lows/highs **non consommés** les plus proches (dynamique, variable selon le contexte inter-session).
- **Dans YAML** : Tous les playbooks utilisent un `tp1_rr: 3.0` ou `tp1_rr: 2.5` fixe, sans notion de session levels.
- **Impact** : Le TP du playbook ne tire pas parti des RR naturellement élevés (1:4 à 1:5.6) que génère la stratégie V066.

### ÉCART 3 — Session highs/lows "consommés" non gérés
- **Dans V066** : Si un niveau de session a déjà été atteint, il est retiré de la liste des niveaux cibles.
- **Dans YAML/Engine** : Aucun mécanisme de "niveau consommé" n'existe. `market_state.asia_high` est statique une fois calculé.
- **Impact** : Des niveaux de liquidité déjà atteints peuvent être faussement ciblés comme TP.

### ÉCART 4 — Entrée LIMIT (YAML) vs MARKET (V066)
- **Dans V066** : Entrée market au moment du BOS (implicite — "I would press short").
- **Dans NY_Open_Reversal YAML** : `entry_logic.type: "LIMIT"` à pattern_close.
- **Impact** : Risque de slippage différent, et l'entrée LIMIT peut manquer le trade si le marché accélère post-BOS.

### ÉCART 5 — Candlestick patterns non requis dans V066
- **Dans V066** : Zéro mention de patterns chandelier (engulfing, pin bar, etc.). Le BOS est suffisant.
- **Dans YAML** : NY_Open_Reversal exige `required_families: [engulfing, pin_bar, morning_star, evening_star]`
- **Impact** : Filtre supplémentaire non fondé sur V066 → potentiellement trop restrictif.

---

## 8. ENGINE GAPS (lacunes pour implémenter V066)

### ENGINE GAP 1 — Session highs/lows calculés en temps réel : PARTIELLEMENT DISPONIBLE
- **Statut** : `market_state.asia_high`, `asia_low`, `london_high`, `london_low` existent dans MarketState (L312-315 pipeline.py).
- **Lacune** : Ces niveaux sont passés en entrée via `session_highs_lows` (market_state.py L212) mais **le calcul dynamique en intra-session n'est pas visible**. Il faudrait vérifier que le pipeline recalcule ces niveaux à chaque candle (pas seulement en début de session).
- **Manquant** : `ny_high` / `ny_low` — seuls asian et london sont dans le dict `session_highs_lows`.

### ENGINE GAP 2 — Détection de la transition London→NY : ABSENT
- **Statut** : L'engine reconnaît les sessions (ASIA, LONDON, NY) dans playbook_loader.py L517-527, mais aucune logique de "prev_session" ou de "fakeout occurred during London" n'existe.
- **Impact** : Impossible de conditionner un trade NY sur "London a déjà fait un fakeout ce matin."

### ENGINE GAP 3 — Niveaux de session "consommés" : ABSENT
- **Statut** : Aucun mécanisme pour tracker si un session level a été atteint pendant une session précédente. `liquidity.py` L190-217 référence `asia_high`, `london_high` etc. comme types de niveaux, mais sans état "consumed".
- **Impact** : La règle V066 "retirer les niveaux déjà atteints" est incodable sans cet état.

### ENGINE GAP 4 — BOS avec candle-close validation (pas wick) : PARTIELLEMENT DISPONIBLE
- **Statut** : Le BOS existe dans l'engine (`require_bos: true`, `bos_patterns` dans setup_engine.py). Mais la règle V066 est spécifique : **UNIQUEMENT une candle close** valide le BOS, pas un wick qui transperce.
- **Lacune** : Vérifier que l'implémentation actuelle du BOS filtre les wicks et n'accepte que les closes. Si non, c'est un bug potentiel par rapport à la règle source.
- **Manquant** : `min_candles_for_bos` — aucun paramètre YAML ne contrôle le nombre de candles nécessaires à la confirmation BOS.

### ENGINE GAP 5 — TP sur session lows/highs dynamiques : ABSENT dans YAML, PARTIELLEMENT dans code
- **Statut** : `setup_engine.py` L301-305 utilise déjà `market_state.asia_high` / `asia_low` pour TP. Mais ce n'est qu'un fallback `or (entry * 1.015)` et non la logique principale codée dans les playbooks YAML.
- **Impact** : Le mécanisme de TP sur session levels est dans le code mais pas exposé dans les YAML playbooks ni activé par défaut.

---

## 9. Stratégie V066 résumée (implémentable)

```
INSTRUMENTS: GBP/JPY, GBP/USD (Forex natif) → SPY/QQQ (adaptation NY session)
TIMEFRAME: 5m (setup + BOS + entrée)
SESSION FOREX: London 03:00-08:00 ET
SESSION INDEXES: NY 08:00-12:00 ET (extension logique, non confirmée dans vidéo)

STEP 1: Marquer avant l'ouverture session :
  - Asian HIGH + Asian LOW
  - New York HIGH + New York LOW (session précédente)
  - Retirer tout niveau déjà "consommé" par la session en cours

STEP 2: London session ouvre
  - Attendre que le prix DÉPASSE un session high ou session low (Asian ou NY)
  - C'est le "London Fakeout" déclencheur
  - Si move = UP → chercher SHORT setup
  - Si move = DOWN → chercher LONG setup

STEP 3: Sur 5m, monitorer les lows/highs valides
  - Définir LOW valide = 2 jambes (down then up), marquer le wick le plus bas
  - Attendre CANDLE CLOSE en dessous du LOW valide (pour SHORT)
  - NOTE : wick qui transperce = NO BOS, attendre close
  - Mettre à jour le niveau surveillé si un nouveau low se forme

STEP 4: À la clôture de la candle BOS :
  - Entrée : MARKET SHORT (ou LONG)
  - SL : au-dessus du HIGH du fakeout move (extrême du fakeout)
  - TP1 : session low le plus proche encore intact (ex: Asian low)
  - TP2 : session low de la session précédente (ex: NY low de la veille)
  - RR attendu : 1:3 minimum, 1:4 à 1:5+ si niveaux alignés

NO-TRADE conditions:
  - Aucun session high/low disponible intact comme cible TP
  - Prix n'a pas dépassé de session high/low (pas de fakeout)
  - BOS validé uniquement par wick (pas de candle close)
```

---

## 10. Note sur l'applicabilité au repo (SPY/QQQ)

La stratégie V066 est native **Forex/London session**. L'adaptation aux US indexes est :
- **Conceptuellement valide** : le même schéma fakeout/BOS/session-levels s'applique à NY session (fakeout de London high/low au NY open).
- **Non confirmée dans cette vidéo** : le trader coupe avant la démo indexes.
- **Partiellement implémentée** dans NY_Open_Reversal (london_sweep_required: true) mais avec des écarts critiques (no BOS requirement, TP fixe, entry LIMIT).

Avant de construire un nouveau playbook V066, il faut d'abord regarder si VIDEO 067+ contient la démo US indexes annoncée (L44893-44898 : "I'm going to show you guys how we can relate this over to us equities").
