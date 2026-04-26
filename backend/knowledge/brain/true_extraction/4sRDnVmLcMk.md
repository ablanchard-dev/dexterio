# 4sRDnVmLcMk — Path to Profitability: Inverse Fair Value Gaps Explained

**Source** : https://youtu.be/4sRDnVmLcMk · TJR · 22m32s · auto-generated captions (en)
**Date extraction** : 2026-04-24

## 1. Thèse centrale
L'Inverse Fair Value Gap (IFVG) est une **confluence de confirmation** (changement de trend) — un FVG qui "devrait" agir en continuation mais qui se fait disrespect par une bougie qui ferme de l'autre côté, signalant que le trend en cours se renverse. Plus rapide que la Break-of-Structure (BoS) classique, donc R:R meilleur.

## 2. Mécanisme complet
- **HTF bias** : NON-SPÉCIFIÉ dans cette vidéo (TJR assume qu'on sait déjà identifier le trend en place par higher-highs/higher-lows ou lower-highs/lower-lows).
- **Setup TF** : montré principalement sur 4H (exemples clairs), mentionne "every single time frame" → TF-agnostic.
- **Entry trigger** : **candlestick closure** (pas wick) de l'autre côté du FVG. Pour IFVG bearish : une bougie ferme sous le **bas** d'un bullish FVG (l'FVG qui devait soutenir le trend up). Pour IFVG bullish : bougie ferme au-dessus du **haut** d'un bearish FVG.
- **Stop loss** : NON-SPÉCIFIÉ explicitement ; implicite dans l'exemple R:R 1:1.3 et 1:2 → SL au-dessus du swing récent (du FVG ou de la structure qui a invalidé).
- **Take profit** : **liquidity draws** (pools de liquidité à gauche du chart : lows précédents pour shorts, highs précédents pour longs). Pas de TP fixed RR — on cible les draws visibles.
- **Exit logic** : NON-SPÉCIFIÉ (pas de BE shift, pas de trailing mentionnés).
- **Sizing** : NON-SPÉCIFIÉ.

## 3. Règles fermées (codables telles quelles)
- IFVG bearish = candle close **under the bottom** of a bullish FVG.
- IFVG bullish = candle close **above the top** of a bearish FVG.
- Must be a **full closure** (not just a wick).
- Le FVG pertinent est celui créé dans le trend actuel (continuation confluence qui se fait invalider).
- Stacked FVGs (no retrace between them) : utiliser la **dernière** (la plus éloignée dans la direction du trend) pour confirmer l'inverse. Les FVG intermédiaires peuvent être disrespectées sans invalider le trend.
- IFVG produit souvent un signal **avant** la BoS classique (quelques bars d'avance).

## 4. Règles floues / discrétionnaires
- "Within the current trend" — nécessite de savoir définir le trend (non codifié précisément ici).
- "Stacked" : defini par "no retrace / no black candle between them" — codable mais à tester.
- Risk/reward target (2R vs 0.5R) = décision discrétionnaire basée sur draws visibles.

## 5. Conditions fertiles
- 4H TF explicitement utilisé, exemples clairs.
- "I use this confluence almost every single day, almost more than break of structure."
- Fertile quand un FVG récent de continuation est présent et se fait invalider tôt vs attendre la BoS.

## 6. Conditions stériles
- Pas de FVG valide dans la zone → rien à inverser.
- Wick only, pas de closure → ne compte pas.
- Stacked FVGs : disrespect de la 1ère seulement = pas un vrai IFVG (trend encore intact).

## 7. Contradictions internes / red flags
- Warning explicite : "We can't just be taking sell positions on inverse fair value gaps to the downside and taking buy positions to inverse fair value gaps to the upside willy-nilly." IFVG n'est **qu'une confluence**, pas un signal tradeable isolé — nécessite liquidity sweep + BoS/IFVG + FVG/EQ. 
- R:R affichés (1:1.3, 1:2) sont illustratifs — aucune stat de win rate / expectancy.
- Pas de définition opératoire de SL.

## 8. Croisement avec MASTER (contexte bot actuel)
- **Confirmé** : FVG definition identique (3-candle imbalance). Break-of-Structure = close above/below prior swing.
- **Nuancé/précisé** : IFVG = "candle **close** through the FVG" (pas wick) — MASTER peut être moins explicite sur closure vs wick. Règle **stacked FVGs : invalider la dernière, pas la 1ère** = précision que MASTER ne détaille pas toujours.
- **Contredit** : pas directement. 
- **Nouveau** : la classification explicite **liquidity = reversal confluence**, **BoS = confirmation confluence**, **FVG = continuation confluence**, **IFVG = confirmation confluence**. Cette grille en 3 catégories est un framework pédagogique utile.

## 9. Codability (4Q + 1Q)
- Q1 Briques moteur existent ? OUI — FVG détecteur implémenté + IFVG via `detect_ifvg` (cf [`master.yaml`](backend/knowledge/playbooks/master.yaml) et `aplus_03_ifvg_flip_5m`). Closure check = standard.
- Q2 Corpus disponible ? OUI — SPY/QQQ 5m/15m/4h dans calib_corpus_v1.
- Q3 Kill rules falsifiables ? OUI — E[R] > 0.05R sur n ≥ 30.
- Q4 Gate §20 Cas attendu ? **C dominant** déjà observé sur Aplus_03 v1/v2 (E[R] -0.074 → -0.019). Cas D possible si l'hypothèse "IFVG seul suffit" est fausse (confirmé empiriquement : signal isolé = pas d'edge).
- Q5 Classification : **management (règle d'invalidation pour stacked FVGs)** + **filtre (IFVG précoce comme substitut BoS)**. Pas un playbook autonome.

## 10. Valeur pour le bot
- **Règle stacked FVGs "use the last one for invalidation"** : à coder dans `detect_ifvg` — ne pas compter la 1ère invalidation d'un stack comme IFVG valide. Vérifier si implémentation actuelle respecte déjà ce critère.
- **IFVG early-trigger vs BoS** : gain R:R potentiellement mesurable. Pourrait être un **filtre d'entry timing** sur playbooks existants (ex : Aplus_03, Engulfing) : si IFVG détecté avant BoS sur même direction, armer setup plus tôt.
- **Grille 3-confluences (liquidity / confirmation / continuation)** : framework utile pour structurer futures stacks playbooks, pas un playbook en soi.
- **Valeur limitée** isolément — Aplus_03 v1/v2 ont déjà prouvé que signal IFVG 5m seul ne porte pas d'edge (E[R] -0.02 à -0.074). Cette vidéo ne change pas ce verdict.

## 11. Citations-clés
- [line 287-291] *"I use this confluence almost every single day almost more than breakup structure because more often than not it happens before breakup structures even do."* → gain timing vs BoS.
- [line 389-395] *"The bottom fair value gap when we have multiple fair value gaps stacked up on top of each other needs to be inverse. Why? Because price closing underneath this fair value gap... it doesn't mean anything. Why? Because we can still come down and fill this gap to push price higher."* → règle stacked FVG.
- [line 275-283] *"We can't just be taking sell positions on inverse fair value gaps to the downside... willy-nilly and just expecting for price to go in our direction. However, this is a very very key confluence that is going to be beneficial."* → IFVG = confluence, pas signal standalone.
