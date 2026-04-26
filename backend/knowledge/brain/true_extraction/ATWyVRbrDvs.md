# ATWyVRbrDvs — Backtesting my 85% win rate trading strategy (pays me $1k/day)

**Source** : https://youtu.be/ATWyVRbrDvs · Tradewriter · 897 s (~15 min) · Auto-captions EN
**Date extraction** : 2026-04-24

## 1. Thèse centrale

L'auteur prétend backtester "en temps réel" sa stratégie "LCE" (Level-Confirmation-Execution) sur 1 semaine d'ES futures (3-7 novembre) pour montrer son 85% win rate. En pratique : pas de backtest systématique, juste 5 jours de **chart reading discrétionnaire** avec Ichimoku clouds multi-TF (1h / 30m / 15m / 5m) pour établir bias, puis breakout level-to-level sur 5m. Pitch pour son "LCE Accelerator" payant.

## 2. Mécanisme complet

- **HTF bias** : Ichimoku cloud sur 1h + 30m + 15m. "Bullish" si cloud slopes up, "bearish" si slopes down, "flat" sinon. Combinaison des 3 TF donne bias directional (mildly / firmly / flat).
- **Setup TF** : 5-minute. Identifier "supply/demand levels" (non-définis formellement, tracés à l'œil).
- **Entry trigger** : **breakout** d'un level supply (long) ou demand (short), confirmé par le bias HTF aligné. Si HTF flat → prêt pour les deux côtés mais "make sure price fully breaks out so we don't get caught in a range".
- **Stop loss** : "above market structure, about halfway between the two levels" (entre zone broken et zone suivante).
- **Take profit** : "next supply/demand level" (level-to-level).
- **Exit logic** : BE shift à 50-60% du move dans la direction ("move stop to break even once price moves 50-60% in my direction").
- **Sizing** : risque identique tous les trades ("no sizing up or down"), **max 2 trades/jour**.

## 3. Règles fermées (codables telles quelles)

- RTH only : 9:30-16:00 ET ("realistically done before noon")
- Only breakout trades (pas de mean reversion, pas d'entry mid-range)
- Max 2 trades/jour
- BE shift à ~55% du move vers TP
- Stop = halfway entre level broken et level suivant
- TP = level suivant (level-to-level)
- Fixed R sizing

## 4. Règles floues / discrétionnaires

- **"Supply/demand levels"** : jamais définis mécaniquement. L'auteur les trace à la main sur les exemples. Pas de `swing_n`, pas de largeur de zone, pas de logic pour les re-test ou invalidation. **C'est le trou noir de la stratégie**.
- **Ichimoku cloud bias** : "mildly / firmly / flat" — seuils non-chiffrés (pente ? épaisseur cloud ?).
- "Cloud flip" mentionné comme signal positif pour short mais pas de critère formel.
- Décision "enter immediately vs wait for next level" : arbitraire, dépend du feeling de la probabilité.
- Reset quotidien du bias : à 9:30 overnight data ? À la veille close ?

## 5. Conditions fertiles

- ES futures (seul instrument testé dans la démo)
- Trend days (jeudi → "strong trend day, plenty of moves")
- RTH matin (< noon) → "when real volume shows up"
- HTF alignés (1h + 30m + 15m tous bearish ou tous bullish)

## 6. Conditions stériles

- HTF flat sur tous TF (jeudi) → auteur dit qu'il a quand même pris un trade (cloud flip 5m), donc pas vraiment "stérile" dans son discours
- Range-bound days
- Long trades quand HTF all bearish ("going long here is basically equivalent of going long at strong resistance")

## 7. Contradictions internes / red flags (DÉMONTAGE)

- **"Backtesting" = visual chart review 5 jours**. Ce n'est PAS un backtest quantifié :
  - Aucun code, aucun CSV, aucune logique programmatique
  - Aucun calcul réel de win rate sur large sample (5 jours × 1-2 trades/jour = 5-10 trades = sample minuscule)
  - Aucun test statistique, aucun OOS, aucune permutation
- **Claim "85% win rate $1k/day"** : **non supporté** par ce qui est montré. Des 5 trades montrés : 4 wins + 1 BE/loss = 80% au mieux. Le titre est marketing.
- **Cherry-picked week** : "most recent at time of recording" — MAIS novembre 2025 ES était globalement un régime directionnel fort (baissier), idéal pour breakout. L'auteur ne montre pas les semaines de range (où la stratégie ne marcherait pas).
- **Discretionary throughout** : "we can check the 15-minute really quickly just to see", "let's say we want to be patient and wait" — décisions subjectives partout.
- **BE shift retroactif** : sur Friday, premier trade stopped out. L'auteur dit "I like to move stop to BE at 50-60%, so this would have been break even — let's assume worst case, full loss". Cette optionalité = lui ne sait pas lui-même si son backtest compte ce trade comme BE ou L.
- **"Pays me $1k/day"** titre → aucune preuve, aucune screenshot P&L live.
- **Pitch LCE Accelerator** est le vrai produit — la vidéo est un **ad** déguisé en backtest.

## 8. Croisement avec MASTER / QUANT / bot actuel

- **Révèle sur MASTER** : confirme **exactement** le pattern dénoncé par vidéo 1 (s9HV_jyeUDk) et vidéo 5 (fIEwVmJJ06s) : un guru **prétend** avoir une stratégie backtestée, mais montre un chart review 5 jours + mains baladeuses. **"Supply/demand levels"** sont exactement le même problème que "swing high" chez ICT → jamais mécanisés. Si on remplace "supply/demand" par "FVG" ou "OB" on retrouve le même flou. Cette vidéo est **la preuve par l'exemple** de ce que nos 10 data points négatifs révèlent : l'impossibilité d'obtenir mécaniquement ce que le guru montre visuellement.
- **Croisement QUANT** : anti-exemple. Tout ce que QUANT prescrit (bar permutation, walk-forward, sensitivity) est absent ici. La vidéo précédente (W722Ca8tS7g) a 4 techniques que cette vidéo-ci **viole toutes les 4**.
- **Implications pour le bot** :
  - **Leçon 1** : n'ajouter aucun playbook à DexterioBOT basé sur "bias Ichimoku multi-TF" sans formaliser les seuils de "sloping" (angle minimum, épaisseur min, durée trending).
  - **Leçon 2** : notre bar §0.5bis "E[R]_pre_reconcile > 0.197R/trade + n>30" est exactement ce qui **refuse** ce type de vidéo. Garder la barre haute.
  - **Leçon 3 (meta)** : si nous entendons "85% win rate" sans (a) sample size > 100, (b) split OOS, (c) max DD, (d) methodology reproductible → rejeter par défaut. Déjà dans `feedback_real_results_bar.md` (user bar +0.10R, Polygon retest rejeté sur quasi-BE).
  - **Leçon 4** : le **BE shift à 50-60%** est cohérent avec notre exploration B2 (BE 1.0→2.15R sur Morning_Trap → Δ E[R] +0.024 mais pas au-dessus 0). Idée pas fausse mais pas suffisante.

## 9. Codability (4Q + 1Q classification)

- **Q1 Briques moteur existent ?** Ichimoku cloud pas encore dans nos détecteurs (check `backend/engines/patterns/*`). Supply/demand levels existent via swing points. BE shift existe.
- **Q2 Corpus disponible ?** OUI (SPY/QQQ/ES 2025 en notre possession).
- **Q3 Kill rules falsifiables possibles ?** OUI si on code les règles. Problème = "supply/demand levels à l'œil" non-codables.
- **Q4 Gate §20 Cas attendu** : **B (schéma sous-exercé parce que signal mal formalisé)** ou **C (edge absent)**. Rang attendu = les "level-to-level breakout" simplement = breakout de swing-high/low déjà testé (BOS_Scalp_1m) → E[R] = -0.118. Donc Cas C probable.
- **Q5 Classification** : **pédagogique / anti-exemple** (pas un playbook codable tel quel).

## 10. Valeur pour le bot

**Aucune valeur positive directe**. Cette vidéo est utile uniquement comme **catalogue de red flags** à surveiller sur TOUT contenu externe (y compris vidéos TRUE futures) : (1) "backtest" = chart review ≤ 2 semaines, (2) win rate annoncé sans sample size, (3) levels tracés discrétionnairement, (4) BE shift optional-retrospective, (5) pitch payant en dernière minute. Cela **confirme rétrospectivement** notre verdict sur les 7 "MASTER faithful" (Phase D.2) : "vocab-borrowing" n'est pas "MASTER-faithful" — exactement parce que les primitives (supply/demand, FVG, OB) sont visuelles chez le guru et doivent être mécanisées avant d'être testées. **Pas de nouveau playbook candidat pour DexterioBOT**. **À classer comme pédagogique négative** dans le MASTER_PLAYBOOK_MAP.

## 11. Citation-clés

> "Rule number one, every trade must follow the LCE model. Level, confirmation, execution. If it's not a level-to-level trade, I don't touch it. Period." [— rule énoncée mais jamais formalisée dans la vidéo ; "level" = tracé à l'œil sur chaque chart]

> "The price ended up moving straight to our target. That's our one successful breakout trade for the day and we lock it in. That's it. Then we close our screens and wait for the next session." [— Monday résumée en 2 phrases, pas de quantification, sample=1]

> "So, I'd be break even on this trade or maybe take a loss if I didn't move my stop to break even on time. So, let's go with the worst-case scenario here, and let's say I've taken a full loss." [— Friday trade stopped out, auteur admet lui-même qu'il ne sait pas si c'est BE ou L → révèle que son "85% WR" dépend de choix discrétionnaires rétrospectifs]
