# 6ao3uXE5KhU — This Simple Options Strategy Crushes SPY (27% CAGR, 2.4 Sharpe)

**Source** : https://youtu.be/6ao3uXE5KhU · Volatility Vibes · 2135 s (~35 min) · Auto-captions EN
**Date extraction** : 2026-04-24

## 1. Thèse centrale

Stratégie **options calendar spread** pilotée par un seul indicateur, le **"Forward Factor" (FF)**. Exploite un biais persistant et académiquement documenté du term structure de volatilité implicite : quand le front IV est sur-bid en backwardation, la forward IV implicite par les deux expirations est sous-évaluée. Long calendar spread (sell front / buy back) profite de ce mispricing. **27% CAGR / 2.4 Sharpe / 19 ans backtest / 124-166 trades/mois** sur univers d'actions liquides (pas SPY directement — c'est le titre click-bait).

## 2. Mécanisme complet

- **HTF bias** : sans objet — options, pas de directional bias sur l'underlying. La stratégie est **market-neutral forward-volatility**.
- **Setup TF** : daily (IV chain snapshot daily). Pas de TF intraday.
- **Entry trigger** :
  1. Calculer `FF = (IV_front - IV_forward) / IV_forward` avec `IV_forward = sqrt((IV2² × T2 − IV1² × T1) / (T2 − T1))` (T en années).
  2. Utiliser **X-earn IV** (IV stripped of earnings premium).
  3. Si `FF >= 0.20` (~ 0.22-0.23 en pratique pour cibler ~20 trades/mois), **open long calendar** : sell front-dated ATM (ou ±35Δ double calendar), buy back-dated same strike.
- **Stop loss** : aucun. Hold jusqu'à expiration front. Max loss = débit payé (+ artefact slippage jusqu'à ~100-110% du débit).
- **Take profit** : aucun seuil R. Exit = **spread close right before front contract expiry** (pin risk avoided).
- **Exit logic** : mécanique : `expiry_front - 1 day` (ou "just before close on expiry day"), **close entire spread as a spread** (pas leg-by-leg).
- **Sizing** : **fractional Kelly (quarter Kelly ou moins)**, cap 2-8% equity par position (4% par défaut), allouer en priorité aux FF les plus élevés.

## 3. Règles fermées (codables telles quelles)

- `FF_threshold = 0.20` (recommandé général) ou `0.22-0.23` (pour ~20 trades/mois)
- `DTE_pair ∈ {(30,60), (30,90), (60,90)}` avec buffer ±5 DTE
- `structure = "ATM_call_calendar"` ou `"±35Δ_double_calendar"` (video recommande ATM pour simplicité, 35Δ double si on veut skew+tent wider)
- `option_volume_20d_avg >= 10_000 contracts/day` (liquidity filter)
- `avoid_earnings_between_entry_and_T2` (ou utiliser X-earn IV strictement)
- `position_cap = 2-8% equity` (default 4%)
- `sizing = quarter_kelly or less`
- `exit_rule = "close as spread, day before front expiry"`
- Portfolio : allouer capital en priorité aux FF les plus élevés jusqu'à saturation

## 4. Règles floues / discrétionnaires

- "Liquid tickers with elevated near-term IV and backwardated term structure" : comment screener programmatiquement la backwardation ? (proxy = FF > seuil suffit)
- Choix ATM vs 35Δ double : l'auteur dit "marginal difference, go ATM pour simplicité" mais pas de règle objective de switch
- Capacity limit : "capped number of simultaneous spreads per symbol based on open interest and volume" mais formule exacte non donnée
- Action en cas de gap overnight extrême : NON-SPÉCIFIÉ
- Rebalancing intra-cycle : NON-SPÉCIFIÉ (la video dit "hold until just before front expiry, no tweaking")

## 5. Conditions fertiles

- **Backwardated term structure** (front IV > forward IV)
- **Localized panic, sector shocks, headlines** → front IV puffed up vs back
- **Mid-liquidity single names** que les grands funds ignorent (mais volume suffisant pour retail)
- **Quarter Kelly sizing** + diversification beaucoup de tickers (double calendar sur 20-30 noms concurrents optimal)
- **FF ≥ 0.20 X-earn** sur n'importe quel pair DTE (30-60, 30-90, 60-90), le 60-90 est le meilleur risk-adjusted

## 6. Conditions stériles

- **FF < 0 (contango)** : still solid mais "nettement moins profitable", à éviter ou sizing réduit.
- **Trade blindly sans condition FF** : mean return **négatif** sur toutes les paires DTE et structures (300k+ observations). Le calendar n'est PAS un free lunch.
- **Trading through earnings** sans X-earn adjustment : comparaison apples vs oranges, dégrade la stratégie.
- **Full Kelly sizing** : returns similaires à half/quarter Kelly mais Sharpe nettement inférieur, MaxDD convex.
- **Few tickers, size up** : pire que diversifier sur beaucoup de noms.

## 7. Contradictions internes / red flags

- Titre "Crushes SPY" → trompeur : la stratégie n'est **pas sur SPY directement**, c'est un univers cross-sectional de ~300k observations sur actions à fort volume d'options. SPY seul aurait peu de backwardation opportunities.
- **Auteur promeut son produit** (Oakquants.com : screener, calculator, community) → biais commercial évident, pas fatal mais à noter. Le backtest utilise leur propre data/simulator.
- **19 ans backtest 2007-2026** : inclut 2008 + 2020, positif. Bien — mais le test n'est pas walk-forward explicitement ; seuils FF optimisés sur full sample (potentielle curve-fit sur les seuils 0.14/0.03/0.41 pour ATM et 0.11/0.01/0.14 pour 35Δ).
- Win rate 47-57% avec mean return positif → typical long-vol-like payoff skewed positive. Mais MaxDD **non mentionné** dans la vidéo (seulement Sharpe et CAGR). Red flag — toujours demander MaxDD.
- "Very few participants explicitly trade forward volatility" = crowding risk si publié → auteur publie pour vendre produit, paradoxe classique (cf. vidéo 5 fIEwVmJJ06s qui exactement démonte ce pattern).

## 8. Croisement avec MASTER / QUANT / bot actuel

- **Révèle sur MASTER** : MASTER (ICT) est **intégralement sur underlying directional**, aucun concept de volatility term structure, aucune mention options. **Gap méthodologique massif** : si 10 data points cross-playbook négatifs sur SPY/QQQ intraday RTH ne convergent pas, c'est peut-être parce que **la classe d'actif + timeframe est structurellement anti-edge retail** (all HFT-arbitraged), et que le vrai edge pour un retail systématique SPY-related passe par **options term structure** (moat = infrastructure/knowledge, pas latency).
- **Croisement QUANT** : QUANT corpus mentionne calendar spreads et vol trading de manière générique ; ici on a une **recette complète + seuils + sizing + backtest 19 ans**. Apporte du concret opérationnel que QUANT n'avait pas.
- **Implications pour le bot** :
  - **Pivot stratégique possible** : notre bot actuel (SPY/QQQ 1m-5m intraday RTH ICT) a 10 data points négatifs. Un pivot vers **options sur SPY + underlying liquides** changerait complètement la thèse.
  - Cependant, **infra actuelle ne supporte pas options** (pas de chain data, pas de pricing Black-Scholes, pas d'expiration management). Sprint complet requis → hors-scope immédiat (cf. CLAUDE.md "Hors scope : UI, live IBKR, refonte moteur").
  - **Tag pour backlog §0.5bis entrée future** si toutes autres pistes ICT échouent : "Options forward-factor calendar spread SPY/liquid-names 19-year backtest edge".
  - Le **Kelly fractional + position cap + diversification 20-30 noms** est une leçon portfolio-level applicable aussi à notre futur full-portfolio discipline, même sur underlying.

## 9. Codability (4Q + 1Q classification)

- **Q1 Briques moteur existent ?** **NON**. Rien dans DexterioBOT ne gère options chain data, IV interpolation, Greeks, expiration calendar, spread as a single instrument. Sprint dédié requis (chain provider, IV calculation, spread pricing, margin model, pin-risk handling).
- **Q2 Corpus disponible ?** **NON** en interne. Polygon a options chain mais pas dans notre setup actuel. Alternative = Oakquants screener (closed-source commercial).
- **Q3 Kill rules falsifiables possibles ?** OUI sur 3 mois OOS : Sharpe < 1.5 OR CAGR < 10% OR MaxDD > 30%. Paper 60 jours requis pour valider cost model real.
- **Q4 Gate §20 Cas attendu** : **D (hypothèse économique à valider)** + **C secondaire** si replication échoue (edge erroded depuis paper publication — cf. vidéo 5). 19 ans de data suggère robustesse mais seuils optimisés sur full sample = risque curve-fit.
- **Q5 Classification** : **playbook** complet (nouveau, hors-scope infra actuel) + **pédagogique** (formules FF, variance time-additivity).

## 10. Valeur pour le bot

**Apport stratégique majeur** mais **hors-scope infra immédiat**. Cette vidéo est un des seuls dans le corpus TRUE à proposer une stratégie avec : (a) papier académique de support, (b) backtest 19 ans, (c) règles complètement mécaniques, (d) formulation open-source du signal (formule FF donnée). **À intégrer dans backlog §0.5bis comme "Entrée Plan B si toutes les pistes ICT/pivot-TF échouent"** — justifie l'effort de sprint options si on accepte de pivoter définitivement hors ICT. Ne change pas le plan court terme (gate §0.7 G4 + backlog Aplus_01 TRUE HTF / Jegadeesh-Titman). Apporte aussi **leçon portfolio** (quarter Kelly, position cap 4%, diversifier 20-30 noms) transférable à notre future discipline multi-playbook.

## 11. Citation-clés

> "If FF is greater than zero, the front IV is greater than the forward IV. This typically happens when term structure is in backwardation, signaling near-term stress or fear. Historically, this setup has shown very strong performance with a high sharp ratio and robust returns."

> "In all cases, just blindly trading all of these positions results in a negative mean return. That's an important baseline. The calendar is not a free lunch. If you don't condition on the term structure, transaction costs and slippage will grind you down if you fire every time."

> "At quarter Kelly sizing, sharp ratios are the highest across the board. Kegger barely declines relative to full sizing, but the stability and efficiency of returns improve substantially. [...] Favor fractional Kelly quarter or less and spread risk across names rather than leaning hard into a few."
