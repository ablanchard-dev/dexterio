# PlsHO33j6B8 — Advanced Imbalance Concepts (NDOG / NWOG / NCOG / BPR)

**Source** : https://youtu.be/PlsHO33j6B8 · TJR · 23m06s · auto-generated captions (en)
**Date extraction** : 2026-04-24

## 1. Thèse centrale
Au-delà des FVG standards, 4 autres types d'imbalance existent : **NDOG** (New Day Opening Gap), **NWOG** (New Week Opening Gap), **NCOG** (New Candle Opening Gap, pratiquement inutile) et **BPR** (Balanced Price Range — "illiquid" range créé par un swift move up puis un swift move down, que le prix re-traverse rapidement à chaque ré-entrée).

## 2. Mécanisme complet

### NDOG / NWOG
- **HTF bias** : indépendant.
- **Setup TF** : daily (NDOG) / weekly (NWOG), observable sur 5m/1m aussi.
- **Entry trigger** : imbalance entre close j-1 et open j (NDOG : 1h market-closed window) ou close vendredi / open dimanche soir (NWOG : weekend window). Si gap non rempli tôt → target ; si on est dans le gap → entry vers la continuation après balance.
- **Stop loss** : NON-SPÉCIFIÉ.
- **Take profit** : le close de la bougie précédente (autre côté du gap).
- **Exit logic** : NON-SPÉCIFIÉ.
- **Sizing** : NON-SPÉCIFIÉ.

### NCOG
- Imbalance entre close bougie N et open bougie N+1 (même TF), pendant que le marché est ouvert.
- TJR dit explicitement : **"pretty fucking useless"** — occurrences microscopiques dans les marchés US ouverts.

### BPR
- **HTF bias** : contextuel.
- **Setup TF** : n'importe lequel ; exemples sur 5m.
- **Définition** : un range qui a été traversé **swift up** puis **swift down** (ou inverse). Le range entre les deux extrêmes est "illiquid".
- **Entry trigger** : quand le prix re-rentre dans le BPR **après** l'avoir complètement quitté, s'attendre à une traversée rapide vers l'autre extrême. Entry soit au bord du BPR (target other side) soit à l'intérieur (cible l'autre côté). Avec confirmation bullish/bearish.
- **Stop loss** : NON-SPÉCIFIÉ.
- **Take profit** : l'autre extrême du BPR.
- **Exit logic** : NON-SPÉCIFIÉ.
- **Sizing** : NON-SPÉCIFIÉ.

## 3. Règles fermées (codables telles quelles)
- **NDOG** : gap entre `close[prev_day]` et `open[current_day]`. Target = le close de la veille, ou entry dans le gap pour continuation.
- **NWOG** : gap entre `close[Friday]` et `open[Sunday_evening]`. Même logique.
- **NCOG** : gap entre `close[bar N]` et `open[bar N+1]` — **à ignorer** pour le bot (TJR explicite).
- **BPR** : séquence de bars avec **swift move up** (N bars, ≥ X ATR move) **suivi ou précédé** d'un **swift move down** traversant la même zone. Le range intersecté = BPR.
- Re-entry dans BPR déjà quitté → expected fast traversal.

## 4. Règles floues / discrétionnaires
- "Swift move" : pas de définition quantitative (combien de bars ? combien d'ATR ?). À calibrer.
- "Completely left the BPR" avant re-entry : flou. Faut-il `min_bars_outside` ? `min_distance_from_mid` ?
- "Illiquid price range" : sémantique, pas un seuil numérique.
- Utilisation d'un BPR comme entry nécessite "bullish/bearish confirmation" (non définie).

## 5. Conditions fertiles
- NWOG : Monday NY open, gap pas rempli en Sunday low-volume session → target opportunity lundi.
- BPR : clairement présent sur 5m / 15m indices US selon les exemples. "C'est partout" (TJR).
- NDOG : rare (fenêtre 1h), utilisable surtout si gap non rempli en Asian session.

## 6. Conditions stériles
- NCOG : marché ouvert, continuous trading → gaps microscopiques, inutilisables.
- NDOG/NWOG : si rempli immédiatement à l'ouverture → pas d'entry.
- BPR : en range / choppy → pas de swift move initial, pas de BPR formé.

## 7. Contradictions internes / red flags
- TJR **avoue** : "The odds of you guys using this is I mean, I don't want to say it's low, but very rarely" (NDOG/NWOG). Aveu de faible fréquence tradable.
- NCOG : explicitement inutile mais enseigné par "duty".
- BPR : **aucune définition quantitative** — "swift move" est subjectif.
- Pas de stats, pas de win-rate, pas de SL défini.
- Exemple de trade perso : "my trade on Tuesday was actually taken off of this" mais pas de PnL, pas de contexte exit/sizing.

## 8. Croisement avec MASTER (contexte bot actuel)
- **Confirmé** : FVG comme imbalance (définition identique).
- **Nouveau relatif à MASTER** :
  - **NDOG / NWOG** : concepts ICT classiques mais non forcément implémentés côté bot. Les sessions-related gaps (pré/post marché + weekend) peuvent être un vecteur de biais directionnel distinct du RTH intraday.
  - **BPR** : concept proche d'un "range d'imbalance étendu" — MASTER parle probablement de "liquidity void" qui est similaire. BPR stricto-sensu = swift-up + swift-down = un pattern à la fois plus large et plus spécifique qu'un simple FVG multi-bars.
- **Nuancé** : NCOG est explicitement rejeté par TJR → MASTER peut encourager à tracker tous les gaps, TJR tranche : only NDOG/NWOG.

## 9. Codability (4Q + 1Q)
### NDOG / NWOG
- Q1 Briques ? **NON** directement. Pas de `detect_ndog` / `detect_nwog` dans le repo. Nécessite sessions calendar (SPY close 16:00 ET, open 09:30 ET next day — attention aux NDOG = gap between Asian session close / US open = 17:00 ET close / 18:00 ET open pour futures).
- Q2 Corpus ? OUI — calendar sessions dispo.
- Q3 Kill rules ? OUI.
- Q4 Cas §20 ? **B probable** pour NDOG (rareté fenêtre 1h) ; **A/C possible** pour NWOG (plus fréquent mais liquidité Monday variable).
- Q5 Classification : **playbook candidat "NWOG_Monday_Target"** (target le gap vendredi→dimanche si non rempli Sunday). Ou **filtre context** (marquer les journées avec NDOG/NWOG actif comme régime particulier).

### BPR
- Q1 Briques ? **NON** directement. Détecteur nécessaire : swing up fast + swing down fast traversant la même zone.
- Q2 Corpus ? OUI.
- Q3 Kill rules ? OUI.
- Q4 Cas §20 ? **C probable** (concept vague, détection discrétionnaire → signal noisy).
- Q5 Classification : **brique de target / reconnaissance de zones illiquides**, pas playbook autonome.

### NCOG
- Classification : **pédagogique uniquement**, à ignorer.

## 10. Valeur pour le bot
- **NWOG (New Week Opening Gap)** = candidat playbook **honnête à tester** :
  - Détection : gap entre SPY `close[Friday 16:00 ET]` et `open[Sunday 18:00 ET]` (ou Monday 09:30 ET pour cash SPY).
  - Target : fill du gap si non rempli en Sunday overnight.
  - Window : Monday 09:30 → session_end si gap encore ouvert.
  - Playbook Family F candidat (Premarket family déjà testée en partie via Aplus_02 mais approche différente : Aplus_02 = sweep+BOS dans fenêtre premarket ; NWOG = pure gap-target).
  - **Priorité** : moyenne. Simple à coder (détection gap triviale), signal rare (~1/semaine), risque Cas B/C mais mécanisme statistique solide (gap fill edge documenté en equities).
- **BPR** : **valeur faible-moyenne** en standalone. Pourrait être utilisé comme **zone de target** pour les playbooks existants (ex : Aplus_03/04 TP qui cherchent "liquidity_draw" pourraient aussi cibler BPR swift-move edges).
- **NDOG** : **valeur faible** (fréquence + fenêtre 1h difficile à capturer sur SPY cash). Pour futures ES, plus pertinent.
- **NCOG** : **valeur nulle** (TJR confirme).

## 11. Citations-clés
- [line 80-85] *"Price more often than not has a very high probability of actively wanting to seek out these gaps and these imbalanced price ranges specifically new day and new week opening gaps to balance it out."* → hypothèse gap-fill directionnel.
- [line 141-144] *"[NCOG is] pretty freaking useless. Um, but I figured I would put it in there because it does happen."* → rejet explicite NCOG.
- [line 370-382] *"Typically, when we have a big swift move straight up or straight down, when price re-enters that range, it will be able to one completely fill that range right back up, but also move just as swiftly down through it as it moved up."* → définition opératoire BPR.
