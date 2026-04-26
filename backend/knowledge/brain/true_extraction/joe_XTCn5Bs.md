# joe_XTCn5Bs — Path to Profitability: Equilibrium Explained

**Source** : https://youtu.be/joe_XTCn5Bs · TJR · 14m26s · auto-generated captions (en)
**Date extraction** : 2026-04-24

## 1. Thèse centrale
L'équilibrium est le **50% mark entre le most-recent low et le most-recent high** (d'un swing dans le trend courant) — utilisé comme **continuation confluence** : acheter sous l'équilibrium en uptrend (discounted range) / vendre au-dessus en downtrend (premium range).

## 2. Mécanisme complet
- **HTF bias** : défini par la structure de swings en place (HH/HL = uptrend, LH/LL = downtrend). TF agnostique (montré sur weekly et low TF).
- **Setup TF** : n'importe lequel, mais les exemples clairs sont weekly/daily/4H/1H et un exemple 5m mentionné ailleurs.
- **Entry trigger** : prix doit **poker sous l'équilibrium** (en uptrend) ou **poker au-dessus de l'équilibrium** (en downtrend). Puis rebond dans la direction du trend.
- **Stop loss** : NON-SPÉCIFIÉ dans cette vidéo.
- **Take profit** : **most recent high** (en uptrend) ou **low** (en downtrend), et draws de liquidité beyond. Pas fixed RR.
- **Exit logic** : NON-SPÉCIFIÉ.
- **Sizing** : NON-SPÉCIFIÉ.

## 3. Règles fermées (codables telles quelles)
- Equilibrium = mid-point (50%) entre **most-recent swing low** et **most-recent swing high**.
- En uptrend : on trace depuis le most recent low (after HH) UP to most recent high. Prix doit **poke below** equilibrium pour valider retrace → buy opportunity.
- En downtrend : on trace depuis most recent high DOWN to most recent low. Prix doit **poke above** equilibrium → sell opportunity.
- **"Most recent" = strict** — TJR hurle dessus : pas le low de 3 swings en arrière, le **dernier** swing low/high avant le retrace en cours.
- À chaque nouveau HH (uptrend) ou LL (downtrend), on redessine l'équilibrium avec le nouveau low/high.

## 4. Règles floues / discrétionnaires
- "Poke" = toucher et rebondir — pas de définition précise de la profondeur minimale (équilibrium touché exactement, ou sous-pénétration requise ?). TJR montre "we poke our head just barely underneath" comme valide.
- Définition du "most recent swing low/high" implique une détection de swing (lookback?). Pas codifié ici.
- Equilibrium utilisé **en combinaison** avec FVG, IFVG, BoS, liquidity sweep — pas isolément.

## 5. Conditions fertiles
- Uptrend clairement défini (après un HH confirmé).
- Fonctionne sur tous TF mentionnés (weekly exemple explicite, low TF aussi).

## 6. Conditions stériles
- Si équilibrium n'est pas atteint, TJR utilise FVG à la place comme continuation alternative.
- Ranging/choppy : non mentionné mais implicite (besoin de structure HH/HL ou LH/LL pour définir le swing).

## 7. Contradictions internes / red flags
- TJR crie pendant 3 min que les gens se trompent sur "most recent" → signe que c'est une règle discrétionnaire malgré son affirmation que c'est "simple".
- "Completely and utterly useless to you guys if not used with correct context" — aveu explicite que c'est un filtre, pas un signal autonome.
- Aucune stat, aucun win-rate, pas de SL défini.

## 8. Croisement avec MASTER (contexte bot actuel)
- **Confirmé** : concept **premium/discount** depuis MASTER (50% dealing range).
- **Nuancé/précisé** : MASTER parle souvent de "dealing range" plus large (swing H/L significatifs). TJR précise **most-recent** = le swing actif dans la leg en cours, ce qui rend le concept opérationnel sur TF basse intraday.
- **Nouveau relatif à MASTER** : l'utilisation de l'**équilibrium comme continuation confluence stackable** avec FVG (si FVG non rempli, EQ peut servir de proxy retrace).

## 9. Codability (4Q + 1Q)
- Q1 Briques moteur existent ? **NON directement** — il faut un détecteur de swings + calcul du 50% mark. Pas de brique `equilibrium_zone` connue dans le repo. Proche de `confluence_zone.py` mais le calcul 50% swing-active est absent.
- Q2 Corpus disponible ? OUI.
- Q3 Kill rules falsifiables ? OUI (E[R] > 0.05R, n ≥ 30).
- Q4 Gate §20 Cas attendu ? **C probable** (filtre de retrace classique, souvent déjà capturé par 0.5 Fib / VWAP). Cas B possible si signal rare (requiert un swing clair + poke précis).
- Q5 Classification : **filtre / continuation confluence** (pas playbook). Utilisable comme brique de retrace-entry dans un stack ICT.

## 10. Valeur pour le bot
- **Brique `equilibrium_active_swing`** potentiellement utile comme **continuation filter** dans playbooks A+01/A+03/A+04 (Family A/B). À stacker avec FVG (si les deux cibles sont touchées → entry plus fort) ou comme alternative (si FVG absent).
- **Risque doublon** : VWAP / EMA / 0.5 Fib couvrent déjà l'idée de "retrace dans discount". Valeur ajoutée à démontrer.
- **Ne pas créer un playbook "Equilibrium_Bounce" standalone** — même pathologie que Aplus_03 (signal isolé = pas d'edge).

## 11. Citations-clés
- [line 75-78] *"All that it does is it identifies the 50% mark from the most recent swing low up to the most recent swing high within a trend as a continuation confluence."* → définition précise, codable.
- [line 125-128] *"When we are in an uptrend, we take it from the MOST RECENT LOW... Because this is where every [bleep] idiot [bleep] this [bleep] up."* → règle strictement "most recent", pas les swings anciens.
- [line 212-214] *"This confluence is completely and utterly useless to you guys if it is not used with correct context."* → aveu explicite : filtre, pas signal.
