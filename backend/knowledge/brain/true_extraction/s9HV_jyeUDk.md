# s9HV_jyeUDk — Backtested Trading Guru's Strategy : Here's the Truth

**Source** : https://youtu.be/s9HV_jyeUDk · IRONCLAD TRADING · 880 s (~14 min) · Auto-captions EN
**Date extraction** : 2026-04-24

## 1. Thèse centrale

L'auteur code et backtests 10 ans les "multi-time frame market structure strategies" de gurus YouTube (JIFX, Trading Geek, Luis Kelly, etc.) sur 5 paires Forex majeures. Résultat : **toutes les versions gurus perdent de l'argent** (pertes 72-86% sur 10 ans) à cause de 5 variables jamais définies (swing-n, TF pair, trend-swing-count, order-block gate, premium/discount gate). Après brute-force de 8 700 combinaisons, il trouve une combinaison qui fait +957%/10 ans (26% CAGR, MaxDD 50%) : **Daily HTF + 15m LTF, n=2 daily / n=6 15m, trend-swing-count=2, PAS d'order block, PAS de premium/discount zone**.

## 2. Mécanisme complet

- **HTF bias** : Daily chart. Swings avec n=2 (1 bougie de chaque côté). Trend = 2 HH+HL consécutifs (bull) ou 2 LH+LL (bear). Au 3e swing count, trop tard.
- **Setup TF** : 15-minute. Swings avec n=6 (filtre strict car noisy).
- **Entry trigger** : Market structure shift 15m — candle closes above recent 15m swing high (long) ou below 15m swing low (short).
- **Stop loss** : "recent swing low" (repris des gurus, pas audité par l'auteur).
- **Take profit** : "top of the range" (repris des gurus, fixe RR implicite, pas liquidity-targeting).
- **Exit logic** : NON-SPÉCIFIÉ (pas de BE, pas de trailing explicite, pas de time-stop mentionné).
- **Sizing** : NON-SPÉCIFIÉ (on devine fixed R vu "1175 trades / 72% WR / 957% total").

## 3. Règles fermées (codables telles quelles)

- `swing_n_htf = 2`, `swing_n_ltf = 6`
- `trend_swing_count = 2` (HH+HL ou LH+LL consécutifs pour déclarer trend)
- `htf_tf = "1D"`, `ltf_tf = "15m"`
- `use_order_block_gate = False` (l'auteur a testé : dégrade)
- `use_premium_discount_gate = False` (l'auteur a testé : dégrade)
- Entry = 15m candle close past swing point dans la direction du HTF trend
- Pullback requis avant MSS (mais pas formalisé comme filtre)

## 4. Règles floues / discrétionnaires

- "Wait for a pullback" : profondeur non spécifiée (Fib % ? swing % ? ATR ?)
- Stop "recent swing low" : quelle swing-n pour calculer le swing de référence ?
- "Top of the range" pour TP : quelle range ? jusqu'au prochain swing HTF ? TP fixed R ?
- Quand la structure devient "invalide" (reset du bias) → non-spécifié
- Pas de gestion du chevauchement de setups (cooldown ? max concurrent ?)

## 5. Conditions fertiles

- **Forex 5 paires liquides** (EUR, GBP, AUD, CHF, JPY vs USD implicite)
- **Tick data Ducascopy** 2016-2025 → 10 ans
- Regime "trends courts" (Forex) → trend-count=2 optimal
- L'auteur note explicitement : "I expect different results on crypto or equities where trend run longer"

## 6. Conditions stériles

- **4h/1h HTF** testés : "between -10% to -20% over 10 years" (best non-daily = +183% / 10 ans = 10% CAGR).
- Order block gate activé → 48 trades / 10 ans = 5/an, "not enough for meaningful return".
- Premium/Discount gate activé → même symptôme, trop de filtre, famine de trades.
- Trend-count ≥ 3 → performance drops significantly ("too late").

## 7. Contradictions internes / red flags

- Teste **8700 combinaisons sur le même dataset** → **massive overfitting risk** non reconnu. L'auteur dit "validated on different tickers and periods" mais ne montre pas le OOS split, ni de walk-forward, ni de permutation test.
- MaxDD 50% sur 10 ans → l'auteur lui-même dit "I wouldn't trade this strategy on its own" → honnête mais révèle que la "meilleure" combinaison reste impraticable standalone.
- `n=2` daily = swing ultra-permissive → probable cherry-pick du paramètre qui survit par chance.
- Pas de coût de transaction discuté explicitement dans la vidéo (tick data Ducascopy → peut incorporer spread mais non validé).
- "Just daily + 15m" → **pas de méthode pour choisir la paire TF a priori** ; il a juste gagné la loterie parmi des dizaines de combinaisons TF.

## 8. Croisement avec MASTER / QUANT / bot actuel

- **Révèle sur MASTER** : MASTER (ICT 71 transcripts) souffre exactement du même défaut → "swing high" jamais défini avec `n`, "higher highs/lows" jamais quantifié, "premium/discount" présenté comme obligatoire mais non-testé. Cette vidéo confirme **empiriquement** que les gates OB + P/D dégradent les stratégies basées sur market-structure-shift. Nos 10 data points négatifs cross-playbook valident la conclusion de la vidéo **par l'autre bout** : les primitives ICT importées telles-quelles n'ont pas d'edge.
- **Croisement QUANT** : cette vidéo est plus faible méthodologiquement que le corpus QUANT (pas de permutation test, pas de walk-forward, pas de split OOS explicite, 8700 combos sur même data = danger). QUANT nous aurait averti du risque overfitting ici. Rien de neuf vs QUANT, **confirmation en négatif** : un auteur publie un résultat "robust" 957%/10 ans sans les gates QUANT → très probablement overfit.
- **Implications pour le bot** :
  - Notre ambiguïté `swing_n` non-formalisée dans plusieurs détecteurs YAML → investiguer.
  - Confirme empiriquement que **order-block gate** ajouté sans preuve dégrade plutôt qu'aide (cf. notre OB_Retest_V004 n=2 / 4w, écho direct).
  - Nos gates HTF D/4H bias (Phase D.1 : effet nul) reçoivent une validation externe : le gain vient du choix TF lui-même, pas d'un post-filter HTF alignment sur un setup déjà émis.

## 9. Codability (4Q + 1Q classification)

- **Q1 Briques moteur existent ?** OUI partiel. Swing points (n-configurable) existent via `directional_change` k1/k3/k9. MSS existe via `detect_bos` / `detect_ifvg`. TF pair 1D/15m : `TimeframeAggregator` gère 15m, **pas de bar 1D intégrée actuellement** → à ajouter si tenté.
- **Q2 Corpus disponible ?** OUI pour SPY/QQQ 2025 (notre corpus existant), **pas pour Forex majeures** (out-of-scope bot). Transposer Daily+15m sur SPY/QQQ 6-12 mois est faisable.
- **Q3 Kill rules falsifiables possibles ?** OUI : n=2D + n=6 15m + trend-count=2, pas d'OB, pas de P/D → une seule config à tester. Kill si E[R]<0.05R / n<30 sur 4w SPY/QQQ ou si permutation p>0.05.
- **Q4 Gate §20 Cas attendu** : **C ou B**. Le gain de l'auteur vient probablement d'overfitting 8700 combos. Sur SPY/QQQ 2025 uptrend, trend-count=2 daily produira beaucoup de longs et quasi aucun short → biais directionnel asymétrique déjà documenté Legs 1-2.
- **Q5 Classification** : **méthodologie** (démontage guru) + candidat **playbook** secondaire (Daily-15m MSS).

## 10. Valeur pour le bot

Principal apport = **validation externe méthodologique** : les gates OB + P/D que la littérature ICT impose "par dogme" sont démontrés **empiriquement néfastes** sur 8700 combinaisons × 5 paires × 10 ans. Confirme notre verdict Phase C.1 (vwap_regime effet nul / destructeur) et Phase 4.2 (VIX overlay destructeur). Apport secondaire = candidat playbook minimal **Daily-bias + 15m MSS** sur SPY/QQQ à smoke-tester 1 semaine (pas prioritaire vs backlog §0.5bis existant). **Pas d'apport quant** : méthodologie naïve (8700 combos, pas de WF, pas de permutation), donc verdict "950% over 10y" à tenir pour suspect. Retenir la direction, pas le chiffre.

## 11. Citation-clés

> "This YouTuber Jifx marks these as swing highs and swing lows in his video. But why isn't this considered a swing point? What about this one? You see the problem? The criteria is never clearly defined. [...] They cherrypick the cleanest, most perfect examples using hindsight and present them as if it's obvious."

> "Using order blocks and discount zones doesn't help increasing return. Actually using them made the results worse. [...] When I required these conditions, trading opportunities dropped so much that the strategy only took an average of 48 trades over an entire 10 years. That's less than five trades a year, not enough to generate any meaningful return."

> "Honestly, I wouldn't trade this strategy on its own. The return profile is interesting, but the draw down is too large for me to be comfortable with it as a standalone system. If I were to use it at all, I would treat it as one piece of a larger portfolio combined with other uncorrelated strategies."
