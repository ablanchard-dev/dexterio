# Source Truth Pack — VIDEO 010 "Five A+ iFVG Setups with Full Explanation"

**Video file**: `xLZ2ekyja4` (YouTube ID)
**Transcript**: `MASTER_FINAL.txt` L5443-5579
**Quality**: MOYENNE-BASSE (40% codable) — narration visuelle, peu de mécaniques explicites en chiffres
**Role in roadmap**: Aplus_01/03 — référence IFVG setup avec sweep+inversion

---

## 0. Avertissements transcription

| Ligne | Texte transcrit | Correction probable | Sévérité |
|-------|----------------|---------------------|----------|
| L5447 | "A plus IPG setups" | "A+ IFVG setups" | HAUTE — confirme motif récurrent |
| L5450 | "how my IPG setups work" | "how my IFVG setups work" | HAUTE |
| L5495 | "this is a one setter for life" | "this is a one setup for life" | MOYENNE — nom d'un autre format de vidéo |
| L5541, L5543 | "ipg", "ipg" | "IFVG" | HAUTE |
| L5462 | "one minute inverse off of a one minute for a rally gap" | "1m IFVG off of a 1m fair value gap" | HAUTE |
| L5471 | "singular fair rally gap" | "singular fair value gap (FVG)" | HAUTE |

**Pattern général**: Le STT confond systématiquement "IFVG" en "IPG" et "fair value gap" en "for a rally gap" / "for every gap". Tout "IPG" ou "rally gap" dans ce transcript = IFVG/FVG.

---

## 1. Définition de l'IFVG (Inverse Fair Value Gap)

### RÈGLE 1 — Définition structurelle de l'IFVG
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L5457-5462
- **Verbatim**: "I'm looking for an inversion fair value gap here I'm looking for a sweep of some sort of low here and I'm looking for a fair value gap to the left it can be in the higher time frame like the 50 minute or it could be a one minute inverse off of a one minute for a rally gap"
- **Interprétation**: Un IFVG est une inversion d'un FVG existant. Le FVG d'origine peut être sur HTF (ex: 5m, 15m, 1H) OU sur le même TF (ex: 1m inverse off of a 1m FVG). L'inversion = le prix ferme au-delà du FVG d'origine et "flip" la zone.
- **Formulation normalisée**: IFVG = (1) un FVG préexistant est présent, (2) le prix sweep à travers ce FVG, (3) le prix ferme de l'autre côté → la zone FVG devient une zone de support/résistance inversée.
- **NOTE**: Le trader ne parle pas d'"invalidation" au sens d'échec. Il parle d'**inversion** = le FVG est traversé et retournée en zone PD array opposée. C'est une nuance critique.

### CONTEXTE 1 — Distinction IFVG vs FVG ordinaire
- **Classification**: CONTEXTE DISCRÉTIONNAIRE
- **Source TXT**: L5500-5502
- **Verbatim**: "you can see that this is actually not a singular for a value gap but like subjectively it still is okay so if I ever see like a fair value gap like kind of a little combined I kind of just combine it into one"
- **Implication**: Le trader accepte des FVGs "combinés" (plusieurs gaps adjacents traités comme un seul). Pas de règle stricte sur la pureté du gap — jugement visuel.

---

## 2. FVG HTF "to the left"

### RÈGLE 2 — Présence d'un FVG HTF à gauche
- **Classification**: RÈGLE EXPLOITABLE (mais âge non précisé)
- **Source TXT**: L5455-5457, L5505-5507, L5513-5514, L5539-5543
- **Verbatim principal**: "I always look for a higher time frame fair value gap to the left or it could be in the same time frame"
- **Exemples dans la vidéo**:
  - Ex 1: FVG visible sur 3m et 5m à gauche (L5466-5467)
  - Ex 2: "delivering from this [FVG] to the left right here" (L5493)
  - Ex 3: "higher time frame hourly there was a favorite way over here" (L5505) — FVG pas visible à l'écran, juste "way to the left"
  - Ex 5: "hourly gap [...] delivering from this hourly gap" (L5543)
- **Timeframe du FVG HTF**: Mentionné: 5m, 3m, 15m, 1H. La référence est toujours "un TF plus élevé que celui de l'entrée".
- **Âge du FVG**: NON PRÉCISÉ. L5504: "there's way like I'm the higher time frame hourly there was a favorite way over here okay" → le FVG peut être "way to the left" (loin dans le passé). Aucun seuil de candles ou de temps donné.
- **Formulation normalisée**: À l'entrée, un FVG doit exister sur un TF supérieur au TF d'exécution, dans la direction du trade. Le prix "delivers from" ce FVG = le FVG est le point d'origine du mouvement.

---

## 3. Règles du sweep de liquidité

### RÈGLE 3 — Sweep requis dans ou vers le FVG
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L5457, L5460, L5465-5467, L5492-5494, L5503, L5524-5527, L5536-5537
- **Verbatim principal**: "I'm looking for some sort of liquidity sweep into that fair value gap"
- **Exemples**:
  - Ex 1: "we had our sweep of a bunch of these lows here [...] we swept into a five minute fair value gap as well as sweeping this low" (L5465-5467) → sweep de lows multiples, sweep DANS le FVG 5m
  - Ex 2: "we swept this high so we swept the high inside for a rally gap got barely any displacement above it" (L5493-5494) → sweep du high DANS le FVG (bearish example, premium)
  - Ex 3: "manipulation like here" (L5503) → terme générique pour sweep
  - Ex 4: "sweep this low and we're delivering from a gap [...] we're sweeping a low inside this for valley gap" (L5524-5527) → sweep du low À L'INTÉRIEUR du FVG
  - Ex 5: "swept all these lows" (L5536) → sweep de lows empilés (stacked lows)
- **Formulation normalisée**: Le sweep doit pénétrer physiquement dans la zone du FVG HTF. Un simple test extérieur ne suffit pas. Le price action "inside" le FVG est ce qui déclenche le signal.
- **ÉCART ENGINE**: La phrase "sweeping a low INSIDE the FVG" implique une relation spatiale : `sweep_low >= fvg_zone_low AND sweep_low <= fvg_zone_high`. L'engine actuel ne vérifie PAS cette relation.

### RÈGLE 4 — Stacked lows / multiple lows = meilleure liquidité
- **Classification**: HEURISTIQUE À VALIDER
- **Source TXT**: L5536-5537
- **Verbatim**: "swept all these lows specifically i mean i guess we've marked this one in hindsight okay um but what's what matters here is these lows are stacked so we sweep all these stacked lows"
- **Implication**: Un sweep de lows empilés (plusieurs supports au même niveau) est de meilleure qualité qu'un sweep d'un seul low. Pas de seuil numérique fourni.

---

## 4. Règles d'inversion (inverse out of it)

### RÈGLE 5 — L'inversion = close de l'autre côté du FVG
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L5471-5472, L5494-5498, L5507-5508, L5526-5528
- **Verbatim**:
  - "a singular [FVG] right here that was broken with decent momentum okay you can see was you know close above here so this is where you take the entry" (L5471-5472)
  - "swept the high came through for every I got closed below it" (L5498) → pour short: close under the FVG
  - "very very big candle over this which would be an a-plus setup" (L5507-5508)
  - "high momentum back above okay" (L5527)
- **Formulation normalisée**: L'inversion = un candle ferme au-delà de la zone FVG avec "decent momentum". Pour LONG: close ABOVE le FVG. Pour SHORT: close BELOW le FVG.
- **Momentum requis**: Explicitement mentionné "with decent momentum" et "barely any displacement" (ex 2, considéré moins idéal). Un gap/FVG dans le candle d'inversion lui-même est le signe optimal.

### RÈGLE 6 — "Barely any displacement" = setup moins fort
- **Classification**: HEURISTIQUE À VALIDER
- **Source TXT**: L5493-5494
- **Verbatim**: "swept this high inside for a rally gap got barely any displacement above it"
- **Implication**: Un candle qui sweep et inverse mais avec peu de déplacement (wick long, corps petit) est un setup de qualité inférieure — A plutôt que A+.

---

## 5. Règles d'entrée

### RÈGLE 7 — Entrée sur le close du candle d'inversion
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L5471-5472, L5494-5495, L5531-5533
- **Verbatim**:
  - "close above here so this is where you take the entry" (L5472)
  - "here's the close blow [below] so here would be the entry" (L5494-5495)
  - "here's the entry" (L5532) — sur le 15m après inversion
- **Formulation normalisée**: L'entrée se prend sur le **close du candle d'inversion** (pas sur un retest). Pas de limit order 50% FVG ici — c'est une **market/immediate entry** à la fermeture du candle d'inversion.
- **ÉCART vs V065**: V065 entre à 50% du FVG sur limit order. V010 entre au close du candle d'inversion (market order ou limit au close).
- **ÉCART vs IFVG_5m_Sweep playbook**: Le YAML dit `type: "LIMIT"`, `zone: "pattern_close"` — partiellement cohérent (pattern_close = close du candle d'inversion) mais le YAML désigne une limite order, pas nécessairement une entrée immédiate.

### RÈGLE 8 — Alternative: retest de la zone après inversion
- **Classification**: HEURISTIQUE À VALIDER
- **Source TXT**: L5547-5549 (ex 5, A vs A+)
- **Verbatim**: "what would make this an a setup like was would be if you know you took this one because this is almost like the second entry right and it's a little higher so this would be the a setup but this would be the a plus because this is the lowest entry you can get"
- **Formulation normalisée**: Entrer au premier candle d'inversion = A+. Attendre un retest/second pullback = A seulement. L'A+ setup requiert l'entrée au plus bas possible (pour long) ou plus haut (pour short).

---

## 6. Stop Loss

### RÈGLE 9 — SL = close sous le FVG (principal)
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L5472-5474, L5519-5520
- **Verbatim**:
  - "my stop loss is typically a close below the fair value gap in this case actually put a hard stop underneath this order block" (L5472-5474)
  - "stop loss would be closed below" (L5519-5520)
- **Formulation normalisée**: SL par défaut = close en-dessous du bas de la zone FVG (pour LONG) ou close au-dessus du haut (pour SHORT). Variante: hard stop sous l'Order Block (mentionné une fois comme alternative plus large).
- **Type de SL**: C'est un **close-based SL** selon la règle principale, pas un hard stop. Pour LONG: `sl_level = fvg_zone_low`, invalide si `close < sl_level`.
- **ÉCART engine**: L'engine actuel utilise `type: "SWING"`, `distance: "recent_swing"`. La vidéo précise que le SL = close sous le FVG, pas le swing récent. C'est plus précis et plus étroit.

---

## 7. Take Profit

### RÈGLE 10 — TP = prochain FVG non rempli au-dessus
- **Classification**: HEURISTIQUE À VALIDER
- **Source TXT**: L5480-5482
- **Verbatim**: "if there's a unbalanced fair value gap above you know I'm gonna scale some if not I'm just gonna try to go for here you know but it just depends"
- **Formulation normalisée**: TP1 = prochain FVG non équilibré dans la direction. S'il y a un "imbalance" au-dessus (pour LONG), scale là. Sinon, target the next liquidity level.

### RÈGLE 11 — Scale à 50% d'un niveau clé
- **Classification**: CONTEXTE DISCRÉTIONNAIRE
- **Source TXT**: L5475-5477
- **Verbatim**: "I actually call this on my live stream okay and I end up scaling half here for one hour because this was a fifty percent level and I knew if I was wrong we'd reject it"
- **Implication**: Partial exit à 50% d'un range/niveau HTF. Purement discrétionnaire — dépend de la lecture du niveau.

### RÈGLE 12 — TP 2R mentionné
- **Classification**: HEURISTIQUE À VALIDER
- **Source TXT**: L5511-5512
- **Verbatim**: "one it's 2r and two there's a fair value up here and we don't really know if it's going to break"
- **Implication**: Le trader utilise 2R comme cible minimale acceptable. Mais ce n'est pas une règle fixe — "targets are a little more subjective all i care about is you understand why" (L5512-5513). Le 2R est une référence, pas un TP fixe.
- **ÉCART vs IFVG_5m_Sweep playbook**: Le YAML dit `min_rr: 3.0`, `tp1_rr: 3.0`. La vidéo mentionne 2R comme suffisant. Écart de 50% sur le RR minimal.

---

## 8. Filtre Discount/Premium

### RÈGLE 13 — Pour LONG: être en discount (sous 50% du range)
- **Classification**: RÈGLE EXPLOITABLE
- **Source TXT**: L5468-5470, L5508, L5525-5526
- **Verbatim**:
  - "the other thing I like about it is it's in discount okay so discount just basically means we're pretty low in the range right if I were to draw a box you know and map out this range we're below fifty percent of this box okay so we're below fifty percent of the box that's when you want to buy" (L5468-5470)
  - "we are in discount we're at lower day V shape above swept liquidity" (L5508)
  - "delivering from a gap in discount right we're coming close to low a day" (L5525-5526)
- **Formulation normalisée**: Pour LONG: prix < 50% du range du jour (ou du range de la jambe). Pour SHORT: prix > 50% (premium). C'est un filtre directionnel — le trader précise "that's when you want to buy".

### RÈGLE 14 — Exception: premium acceptable si narrative bearish
- **Classification**: CONTEXTE DISCRÉTIONNAIRE
- **Source TXT**: L5487-5492
- **Verbatim**: "for this leg alone do you see how you know we have all this engineer liquidity here right so we know the bias is bearish [...] I still count this is okay this is not this is on premium you know because it made sense to go down here"
- **Implication**: Pour SHORT en premium, c'est valide si la narrative HTF est bearish. Le filtre discount/premium n'est pas absolu — il est conditionnel à la narrative.

---

## 9. Analyse par exemple

### Exemple 1 — LONG, 3m/5m, breakeven
- **Qualité mécanique**: HAUTE
- **Éléments présents**: Sweep des lows (multiples), sweep INTO le 5m FVG, FVG à gauche sur 3m+5m, discount (< 50% box), inversion bullish avec momentum, entrée au close, SL sous l'OB, scale à 1R (50% level)
- **Éléments manquants**: HTF FVG exact non quantifié, pas de TP cible défini
- **Résultat**: Breakeven — scale à 1R puis retour

### Exemple 2 — SHORT, premium, narrative bearish
- **Qualité mécanique**: MOYENNE
- **Éléments présents**: FVG à gauche, sweep du high DANS le FVG, inversion bearish (close below), delivering from HTF FVG, premium avec narrative bearish valide
- **Particularité**: "barely any displacement" = qualité inférieure. Setup quand même A+ car tous autres critères remplis.
- **Éléments manquants**: Timeframe exact non précisé, TP pas discuté

### Exemple 3 — LONG, FVG combiné + hourly HTF
- **Qualité mécanique**: MOYENNE
- **Éléments présents**: FVG HTF (1H) "way to the left", manipulation/sweep, discount, "very big candle" = inversion forte
- **Particularité**: FVG "combiné" accepté (subjective). FVG hourly pas visible à l'écran.
- **Éléments manquants**: Entrée exacte pas clarifiée, TP discuté mais "subjective"

### Exemple 4 — LONG, double FVG, near low of day
- **Qualité mécanique**: MOYENNE-HAUTE
- **Éléments présents**: Sweep des lows, FVG (double, combiné), discount (near low of day), high momentum retour au-dessus
- **Particularité**: RR "not super high" vers le high interne → trade marginal mais concept valide
- **Éléments manquants**: Timeframe pas explicité

### Exemple 5 — LONG, 15m, hourly FVG, A+ vs A distinction
- **Qualité mécanique**: HAUTE
- **Éléments présents**: 15m timeframe, sweep de lows empilés, delivering from 1H FVG, entrée au low of day après inversion, discount (coin du range selon "corners of the range")
- **Particularité**: Distinction A+ (premier candle d'inversion) vs A (second entry/retest). C'est la règle de qualité d'entrée la plus claire de la vidéo.
- **Éléments manquants**: TP exact pas discuté

### Éléments COMMUNS aux 5 exemples
1. FVG HTF préexistant à gauche (3m/5m/15m/1H selon le setup)
2. Sweep de liquidité (lows pour LONG, highs pour SHORT) qui pénètre dans le FVG
3. Candle d'inversion avec momentum (close de l'autre côté)
4. Filter discount (pour LONG) / premium (pour SHORT) — avec exception narrative
5. Entrée au close du candle d'inversion (A+) ou au retest (A)
6. SL = close sous/sur le FVG
7. Delivering from = le trade va dans la direction du FVG HTF (FVG = magnet)

---

## 2. Éléments HEURISTIQUES (à valider)

### HEURISTIQUE 1 — Âge max du FVG HTF
- **Source TXT**: L5505 "there was a favorite way over here okay" — FVG loin dans le passé accepté
- **Problème**: Aucun seuil temporel ou en candles. Une campagne doit fixer un paramètre: `htf_fvg_max_age_candles` (suggestion: 50 candles 1H?).

### HEURISTIQUE 2 — Seuil du "decent momentum" pour l'inversion
- **Source TXT**: L5471 "broken with decent momentum"
- **Problème**: Pas de métrique. Suggérés: `candle_body_pct > 0.6` (corps > 60% du range du candle) ou `displacement_pct > 0.1%`.

### HEURISTIQUE 3 — "Corners of the range" (ex 5)
- **Source TXT**: L5534-5535 "according to this range k corners arrange work very lis range right"
- **Problème**: Transcription dégradée. Probablement "corners of the range work very well in this range" → accentue l'idée que les trades aux extrêmes du range (haut ou bas) sont préférables. Non quantifiable directement.

### HEURISTIQUE 4 — Distinction A+ vs A (qualité d'entrée)
- **Source TXT**: L5545-5549
- **Verbatim**: "this would be the a setup but this would be the a plus because this is the lowest entry you can get"
- **Règle**: A+ = entrée sur le premier candle d'inversion (lowest/highest). A = entrée sur un candle suivant/retest. Mécaniquement codable mais la définition de "first inversion candle" nécessite une clarification (est-ce le premier close au-delà du FVG?).

---

## 3. Bruit / marketing (ignoré)

- L5447-5449: Plug Apex account code "dodgy" — pub
- L5450-5453: Référence au PDF gratuit — promotion
- L5550-5579: Mentorship plug (Eliana, payouts, appels de sélection) — 100% marketing, zéro contenu technique

---

## 4. ÉCARTS — Vidéo vs Implémentation actuelle

### ÉCART E1 — Définition de l'IFVG (critique)
| Dimension | Vidéo V010 | Engine `ifvg.py` |
|-----------|-----------|-----------------|
| Mécanisme | Sweep INTO le FVG + close de l'autre côté → la zone FVG devient support/résistance | Close au-delà du FVG (`last_close < zone_low`) → signal immédiat |
| Sweep requis | **OUI — explicitement** "liquidity sweep into that FVG" | **NON** — l'engine détecte seulement la clôture au-delà, pas le sweep préalable |
| Relation spatiale | Le sweep doit pénétrer dans la zone du FVG | Non vérifié |
| Résultat | L'IFVG est un **événement en 2 temps** (sweep + inversion) | L'IFVG est détecté en **1 temps** (close seulement) |

**Impact**: L'engine produit des faux positifs — tout close au-delà d'un FVG récent est signalé, même sans sweep préalable.

### ÉCART E2 — FVG HTF requis (critique)
| Dimension | Vidéo V010 | IFVG_5m_Sweep YAML |
|-----------|-----------|-------------------|
| Condition | FVG HTF à gauche **obligatoire** | `allow_fvg: true` — optionnel |
| Timeframe | TF supérieur (5m, 15m, 1H selon setup) | `setup_tf: "5m"` — pas de lien HTF |
| Position du prix | Doit "deliver FROM" le FVG HTF | Non vérifié |

**Impact**: Le playbook YAML ne requiert pas de FVG HTF — il manque la condition fondamentale du setup.

### ÉCART E3 — Sweep requis dans le FVG (critique)
| Dimension | Vidéo V010 | IFVG_5m_Sweep YAML |
|-----------|-----------|-------------------|
| Condition | `require_sweep: false` → sweep NON requis | Vidéo: sweep **obligatoire** |
| Relation spatiale | Sweep doit pénétrer dans la zone FVG | Non vérifié |

**Impact**: La condition la plus importante du setup (sweep INTO FVG) est désactivée dans le YAML.

### ÉCART E4 — Stop Loss
| Dimension | Vidéo V010 | IFVG_5m_Sweep YAML |
|-----------|-----------|-------------------|
| Type | Close sous/sur le FVG | `type: "SWING"`, `distance: "recent_swing"` |
| Zone | Zone du FVG d'inversion | Swing récent (plus large) |

**Impact**: SL trop large → RR moins favorable.

### ÉCART E5 — Take Profit / RR
| Dimension | Vidéo V010 | IFVG_5m_Sweep YAML |
|-----------|-----------|-------------------|
| TP1 | Prochain FVG non rempli, ou 2R | `tp1_rr: 3.0` |
| TP2 | Prochain niveau de liquidité | `tp2_rr: 5.0` |
| BE | Non mentionné dans la vidéo | `breakeven_at_rr: 1.5` |

**Impact**: Le YAML exige un RR minimal 3:1 alors que la vidéo mentionne 2R comme suffisant. Le breakeven à 1.5R n'est pas du tout discuté dans la vidéo.

### ÉCART E6 — Filtre discount/premium
| Dimension | Vidéo V010 | IFVG_5m_Sweep YAML |
|-----------|-----------|-------------------|
| Condition | Discount pour LONG, premium pour SHORT (< ou > 50% du range) | Non mentionné |
| Exception | Premium pour SHORT valide si narrative bearish | N/A |

**Impact**: Le filtre de zone le plus discriminant de la vidéo est absent du YAML.

### ÉCART E7 — `required_signals: ["IFVG@5m"]` absent du YAML IFVG_5m_Sweep
Le playbook `IFVG_5m_Sweep` dans `playbooks.yml` utilise `allow_fvg: true` dans `ict_confluences` mais n'a pas de `required_signals`. Seul le test dans `test_required_signals_and_sessions.py` référence `IFVG_BEAR@5m` — c'est un test unitaire, pas un playbook actif.

---

## 5. Gaps Engine (ENGINE GAPS)

### GAP G1 — Sweep spatial non détecté
**Problème**: Le détecteur `ifvg.py` ne vérifie pas si le prix a préalablement pénétré dans la zone du FVG avant de fermer de l'autre côté. Il ne peut pas détecter "sweep INTO an existing FVG".

**Ce qu'il faudrait**:
```python
# Pour un FVG bullish (zone_low à zone_high):
# Sweep into FVG = min(candle.low) pour les candles entre idx_end et idx_inversion
#                  était <= zone_high (le prix est entré dans la zone)
# Puis close < zone_low (inversion)
wick_penetrated_fvg = any(c.low <= zone_high for c in candles[idx_end+1:idx_inv])
```

### GAP G2 — Limite de récence trop restrictive
**Problème**: `if idx_end < n - 5: continue` — seuls les FVGs des 5 derniers candles sont considérés.

**Vidéo**: Les FVGs peuvent être "way to the left" sur le 1H — des dizaines ou centaines de candles plus tôt. Sur 5m, un FVG 1H "way to the left" peut avoir 288+ candles 5m.

**Impact**: L'engine ignore tous les FVGs HTF pertinents — c'est une contrainte majeure qui explique en partie le signal zéro en backtest.

### GAP G3 — `required_signals: ["IFVG@5m"]` non utilisé dans IFVG_5m_Sweep
**Problème**: Le YAML `IFVG_5m_Sweep` dans `playbooks.yml` n'a pas de `required_signals` déclaré. La plomberie pour `required_signals` existe dans `playbook_loader.py` (L735-780) mais n'est pas activée pour ce playbook.

**Impact**: Le playbook peut "matcher" sans aucun IFVG détecté — les filtres reposent sur `candlestick_patterns` et `ict_confluences`, pas sur l'IFVG lui-même.

### GAP G4 — Direction de l'IFVG inversée dans `ifvg.py`
**Observation**: Dans `ifvg.py` (L64-84), un FVG bullish inversé produit un signal `direction='bearish'`. Dans la vidéo, un FVG bullish traversé vers le bas constitue une inversion bearish — le signal bearish est correct.

Mais dans le playbook `Aplus_03` (YAML transcripts), la logique est: "Bearish FVG invalidated → look for LONG". Ce sont des conventions opposées:
- `ifvg.py`: FVG_bullish invalidé → ifvg signal bearish
- `Aplus_03`: FVG_bearish invalidé → trade LONG

Les deux sont cohérents si on lit "l'IFVG" comme le **signal généré** (bullish = aller long) plutôt que comme "le FVG qui a été invalidé". Pas d'incohérence dans la convention finale, mais la documentation est confuse.

---

## 6. Stratégie V010 résumée (implémentable)

```
CONCEPT: IFVG A+ Setup
TIMEFRAME: tout TF (exemples: 1m, 3m, 5m, 15m)
SESSION: NY (pas de restriction explicite dans cette vidéo)

CONDITION 1 (GATE BINAIRE): FVG HTF à gauche dans la direction du trade
  - Pour LONG: FVG bullish sur TF supérieur (5m, 15m, 1H)
  - Pour SHORT: FVG bearish sur TF supérieur
  - Position: "delivering from" = prix provient de ce FVG vers la cible

CONDITION 2 (GATE BINAIRE): Sweep de liquidité DANS le FVG
  - Pour LONG: sweep de lows (stacked preferred) qui pénètre dans la zone FVG
  - Pour SHORT: sweep de highs qui pénètre dans la zone FVG bearish
  - La relation spatiale est obligatoire: wick_low <= fvg_zone_high

CONDITION 3 (GATE BINAIRE): Candle d'inversion avec momentum
  - Pour LONG: close ABOVE fvg_zone_high (inversion bullish)
  - Pour SHORT: close BELOW fvg_zone_low (inversion bearish)
  - Momentum requis: "decent" (corps > bruit, pas de "barely any displacement")

FILTRE DISCOUNT/PREMIUM:
  - LONG: prix < 50% du range du jour (discount) → préféré mais pas absolu
  - SHORT: prix > 50% du range (premium) → préféré mais pas absolu
  - Exception: narratif HTF peut justifier trade en zone contraire

ENTRÉE:
  - A+: market order au close du candle d'inversion (premier candle)
  - A: limit order au retest de la zone FVG (deuxième chance)

STOP LOSS:
  - Pour LONG: close sous la zone FVG (fvg_zone_low)
  - Pour SHORT: close au-dessus de la zone FVG (fvg_zone_high)
  - Alternative: hard stop sous/sur l'Order Block adjacent

TAKE PROFIT:
  - TP1: prochain FVG non équilibré au-dessus/en-dessous (unbalanced FVG)
  - TP2: prochain niveau de liquidité HTF
  - 2R minimum acceptable (non fixe)
  - Partial scale possible à 50% d'un niveau de résistance clé

QUALITÉ A+ vs A:
  - A+: entrée au premier candle d'inversion (lowest entry for long)
  - A+: discount (pour long) ou premium (pour short) + narrative alignée
  - A+: sweep de stacked lows/highs (multiple = meilleur)
  - A: retest/second entry
```

---

## 7. Vérifications vidéo requises

| # | Point à vérifier | Ligne TXT | Bloquant? |
|---|-----------------|-----------|-----------|
| 1 | Screenshot ex 1: visuel du sweep INTO le 5m FVG | L5465-5472 | OUI — définit la relation spatiale |
| 2 | Confirmer timeframe exact des exemples 2 et 4 | L5485, L5517 | MOYEN |
| 3 | Screenshot ex 5: distinction A+ vs A visuellement | L5545-5549 | OUI — clarifier "first inversion candle" |
| 4 | Confirmer "50 minute" (L5461) = "5 minute" (erreur STT?) | L5461 | MOYEN — affecte le TF HTF min |
| 5 | Clarifier "corners of the range" (L5534-5535) | L5534 | FAIBLE — concept qualitatif |
| 6 | Confirmer discount/premium = 50% du range du JOUR ou de la jambe | L5468-5470 | OUI — paramètre clé |

**Verdict**: 3 vérifications bloquantes nécessaires pour implémentation fidèle. Le noyau mécanique (FVG HTF + sweep dans FVG + inversion + discount) est suffisamment clair pour une implémentation beta.

---

## 8. Comparaison avec Aplus_01 (playbooks_Aplus_from_transcripts.yaml)

`Aplus_01_MarketOpen_Sweep_IFVG_Breaker` est partiellement aligné mais diffère sur plusieurs points:
- Source: Video 064 (différente de Video 010)
- Condition "IFVG forms AFTER the sweep" dans Aplus_01 vs Video 010: sweep INTO existing FVG → inversion
- Aplus_01 mentionne "breaker block OR order block OR FVG fill zone (confluence)" — Video 010 ne mentionne que l'OB comme alternative SL, pas comme zone d'entrée
- Aplus_01 restreint à `MARKET_OPEN_WINDOW` — Video 010 montre 5 exemples sans restriction de session explicite
- Video 010 est probablement plus proche de `Aplus_03_IFVG_Flip_from_FVG_Invalidation` (sans la restriction d'Apex/Market Open)
