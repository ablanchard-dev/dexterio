# wzq2AMsoJKY — The ONLY Equilibrium Video You'll Ever Need

**Source** : https://youtu.be/wzq2AMsoJKY · TJR · 1120.48s (~19min) · auto-generated EN captions
**Date extraction** : 2026-04-24

## 1. Thèse centrale
Equilibrium = 50% line entre swing high récent et swing low récent (calculé via GAN box tool). En uptrend, discounted price range (sous 50%) = zone d'achat. En downtrend, premium price range (au-dessus 50%) = zone de vente. C'est une **continuation confluence** (trend touch EQ puis continue), distincte des reversal confluences (liquidity sweep). TJR annonce avoir éliminé order blocks + breaker blocks : il n'utilise que equilibrium + FVG comme continuation confluences.

## 2. Mécanisme complet

### HTF bias
- Identifier uptrend / downtrend via HH-HL / LH-LL
- 4H, 1H, daily tous mentionnés comme TFs où appliquer equilibrium

### Setup TF
- Equilibrium peut s'appliquer à n'importe quel TF (4H, 1H, 5m) selon le contexte de trade (HTF bias vs LTF execution)

### Entry trigger (equilibrium-specific)

**Uptrend (buy setup)**
1. Identifier most recent swing low et most recent swing high
2. Draw equilibrium entre les deux (GAN box)
3. Attendre que price retrace dans discounted price range (sous 50%)
4. Voir buy orders fills out of discounted range (price respects equilibrium, pushes up)
5. Target = highs / draws on liquidity au-dessus
6. Entry confirmation sur LTF (5m break of structure to upside, ou 1m IFVG)

**Downtrend (sell setup)**
1. Identifier most recent swing high et most recent swing low
2. Draw equilibrium entre les deux
3. Attendre que price retrace dans premium price range (au-dessus 50%)
4. Voir sell orders fills out of premium range (price respects equilibrium, pushes down)
5. Target = lows / draws on liquidity en-dessous
6. Entry confirmation sur LTF (5m break of structure to downside)

### Stop loss
- NON-SPÉCIFIÉ (implicite : au-dessus du swing high pour short, sous swing low pour long)

### Take profit
- Liquidity targets (highs en uptrend, lows en downtrend)
- "Continue the uptrend" / "take out this low" — cibles = next external point

### Exit logic
- NON-SPÉCIFIÉ

### Sizing
- NON-SPÉCIFIÉ

## 3. Règles fermées (codables telles quelles)

### Définition equilibrium (codable)
- **Uptrend** : EQ = (recent_swing_low + recent_swing_high) / 2
- **Downtrend** : EQ = (recent_swing_high + recent_swing_low) / 2 (même formule, orientation différente)
- **Recent swing** = le plus proche en temps (pas le plus extrême) — TJR insiste : "most recent low up to the most recent high"

### Règles équilibrium
- Rule A : Uptrend + price < EQ (discounted) = potential buy zone
- Rule B : Uptrend + price > EQ (premium) = wait (don't buy in premium)
- Rule C : Downtrend + price > EQ (premium) = potential sell zone
- Rule D : Downtrend + price < EQ (discounted) = wait (don't sell in discount)

### Règles d'usage trading
- Equilibrium = **continuation confluence** (pas reversal)
- Reversal confluence = liquidity sweep (distinct)
- Stack requis : sweep + BOS + equilibrium retrace = full TJR setup
- "Order blocks" et "breaker blocks" = **éliminés** par TJR — "More often than not, equilibrium is getting filled when that order block or breaker block is getting hit, which pretty much renders order blocks and breaker blocks completely useless."

## 4. Règles floues / discrétionnaires
- Quelle "most recent swing" choisir ? Si structure a HH/HL récents multiples, lequel prendre ? TJR dit "most recent" mais comment détecter algorithmiquement ? (directional_change.py avec k=3 ? k=9 ?)
- Quand redessiner equilibrium ? À chaque nouvelle swing ? Après BOS ?
- "Fill equilibrium" = tap the 50% line ? ou close through ? ou wick into ?
- Combien de temps est valide un equilibrium avant "stale" ?

## 5. Conditions fertiles
- Structure claire HH-HL (uptrend) ou LH-LL (downtrend)
- Swings récents bien définis (pas de noise, pas de choppiness)
- Volume / momentum confirmant quand price tap EQ
- Liquidity pool opposé au trend disponible comme target

## 6. Conditions stériles
- NON-SPÉCIFIÉ explicitement dans cette vidéo, mais implicite :
- Range market (pas de trend → pas de continuation)
- Swings trop étroits (EQ zone trop petite à tap)

## 7. Contradictions internes / red flags
- **Claim "seven figures last year"** : "one of the key confluences that I use within my strategy that has helped me make seven figures last year alone." Aucune preuve. Marketing.
- **"Equilibrium is by far one of the easiest confluences"** + **élimination d'OB/BB** = surconfiance. Une méthode "simple" qui fait 7 chiffres = claim rouge classique.
- **Insultes envers spectateurs** qui se trompent sur la définition ("shove them so far up your little ass", "self-diagnosed on the spectrum") — compense avec humour une **simplicité suspecte** de la méthode.
- **Exemples cherry-pick 4H** : "We just showed literally back-to-back times within the same trend" — 2 exemples dans un seul downtrend = pas une étude statistique.
- **"Let me know if equilibrium gets filled when that order block is getting hit. More often than not..."** — **demande au spectateur de faire le test**, ne le fait pas lui-même. Délégation de burden of proof.
- **Contradiction avec stratégie complète** : dans TEp3a-7GUds il parle de FVG 5m OU equilibrium 5m comme continuation confluences. Dans cette vidéo il élimine OB/BB **mais garde FVG**. FVG et equilibrium sont redondants ? conflictuels ? non-résolu.
- Aucune stat de hit rate de equilibrium-based entries.

## 8. Croisement avec MASTER (contexte bot actuel)
- **Concepts MASTER confirmés** :
  - Premium/discounted price ranges (concept ICT de base)
  - Continuation vs reversal confluences
- **Concepts MASTER nuancés/précisés** :
  - Equilibrium = 50% précis (pas 33/67 fib ou autres) entre most recent swing H et most recent swing L
  - Ne pas utiliser swing le plus extrême (ex plusieurs mois), utiliser le plus récent
- **Concepts MASTER contredits** :
  - MASTER couvre order blocks extensivement (vocabulaire ICT classique). TJR les **élimine**. Si TJR a raison → **OB_Retest_V004** (actuellement DEFER dans le bot) est inutile. Le bot l'a déjà déprécé — cohérent avec TJR.
  - MASTER couvre breaker blocks. TJR les élimine aussi.
- **Concepts nouveaux absents de MASTER** :
  - **GAN box tool** (TradingView tool) — pas de formalisation dans MASTER
  - **"Most recent"** swing comme règle stricte (pas le plus extrême) — souvent flou dans MASTER
  - Équivalence affirmée OB/BB ≈ equilibrium → substitution justifiable

## 9. Codability (4Q + 1Q classification)
- Q1 Briques moteur existent ?
  - Swing detection : OUI via `directional_change.py` (k1/k3/k9 zigzag)
  - Equilibrium calculation : **NON** — trivial à ajouter (EQ = (swing_high + swing_low) / 2), feature à construire
  - Premium/discounted zone detection : **NON** — basé sur EQ, à construire
  - Tap into EQ detection : **NON** — à ajouter (price touches EQ zone avec tolerance)
- Q2 Corpus disponible ? OUI.
- Q3 Kill rules falsifiables ? OUI — subset "EQ-aligned" vs "counter" E[R] delta > 0.05R testable.
- Q4 Gate §20 Cas attendu ? **A potentiel** (confluence simple à coder, test rapide). Risque **C** (pas d'edge sur corpus 2025 SPY/QQQ) comme les autres confluences testées.
- Q5 Classification : **continuation confluence / filtre entry** (pas playbook autonome, brick réutilisable)

## 10. Valeur pour le bot

### Valeur concrète
- **Brick equilibrium à construire** comme continuation confluence alternative à FVG. Simple :
  ```
  def detect_equilibrium_tap(swing_high, swing_low, price, tolerance_pct=0.1):
      eq = (swing_high + swing_low) / 2
      return abs(price - eq) / (swing_high - swing_low) < tolerance_pct
  ```
- Permet d'enrichir Aplus_01/03/04 v2 avec un 2e type de continuation confluence (en plus de FVG 5m). Double le nombre de matches potentiels.
- Potentielle **substitution** pour OB/BB dans le schéma (déjà DEFER/KILL dans le bot) : réallouer l'effort vers equilibrium.

### Priorité
- **Faible priorité standalone**. Une continuation confluence de plus sur un signal déjà bear (IFVG/BOS isolé E[R]<0 confirmé 3 data points Aplus_03_v2 / Aplus_04_v2 α''/ε).
- **Haute priorité en support** de v2 pipeline TJR (TEp3a-7GUds + ironJFzNBic) : equilibrium est un élément nommé de la stratégie complète, pas intégré dans le bot.

### Risque d'échec
- TJR admet lui-même ne plus utiliser OB/BB. Si equilibrium ≈ OB/BB statistiquement sur SPY/QQQ, le bot a déjà testé l'equivalent (OB_Retest_V004 = n=2, gate k3 reject 98%). Redoundance possible.
- Seul, une confluence ne produit pas d'edge (leçon cumulée du bot).

## 11. Citations-clés
- "All that this little line does, which is equilibrium, it distinguishes us between the premium price range, which is above equilibrium, and the discounted price range, which is underneath equilibrium."
- "It's from the most recent low up to the most recent high." (définition stricte)
- "Equilibrium is a confluence that I like to call a continuation confluence... where we are looking for the trend to come into it and then continue out of it."
- "I no longer use order blocks. I no longer use breaker blocks. The only continuation confluences that I need and that I use are equilibrium and fair value gaps because simplicity is key."
- "Whenever you see a potential order block or breaker block entry, go ahead and mark out equilibrium and let me know if equilibrium gets filled when that order block or breaker block is getting hit. More often than not, equilibrium is getting filled, which pretty much renders order blocks and breaker blocks completely useless."
- "Has helped me make seven figures last year alone." (claim marketing non-vérifiable)
