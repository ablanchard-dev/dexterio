# vlnNPFu4rEQ — 6 Rules I've Learned From 6 Years of Trading

**Source** : https://youtu.be/vlnNPFu4rEQ · TJR · 894.88 s (~14:55) · auto-generated EN captions (465 entries)
**Date extraction** : 2026-04-24

## 1. Thèse centrale
Six règles discipline / risk management / psychologie que TJR aurait voulu connaître au début : turn-off, journaling, pas de hopping de stratégies, patience/discipline, trading plan obligatoire, risk management absolu. **Zéro contenu stratégique** (pas de setup, pas de pattern, pas de TF ICT). C'est une vidéo de meta-règles destinée aux débutants.

## 2. Mécanisme complet
- **HTF bias** : NON-SPÉCIFIÉ (hors scope vidéo)
- **Setup TF** : NON-SPÉCIFIÉ
- **Entry trigger** : NON-SPÉCIFIÉ
- **Stop loss** : NON-SPÉCIFIÉ
- **Take profit** : NON-SPÉCIFIÉ
- **Exit logic** : NON-SPÉCIFIÉ
- **Sizing** : "Risk management plan that helps us live to trade another day" — position fixe permettant de survivre aux séries perdantes. Pas de R explicite ni de fraction de Kelly.

## 3. Règles fermées (codables telles quelles)
- **Rule 1 — Daily trade cap** : si le bot fait un win → stop de la journée (arrêter nouveaux setups). Idem après un loss → pas de "revenge trade" immédiat.
- **Rule 6 — Risk management absolu** : jamais risquer l'account entier sur un trade ; taille fixe / R par trade ; survie > maximisation court terme. Déjà implémenté côté bot (caps session, max risk per trade).
- **Rule 2 — Journaling obligatoire** : chaque trade doit être taggé avec ses features (pattern, TF, HTF bias, etc.) pour audit a posteriori, sinon impossible de diagnostiquer. Déjà implémenté côté bot (parquets trades + stats per-playbook).

## 4. Règles floues / discrétionnaires (nécessitent interprétation)
- **Rule 3 — Don't jump from strategy to strategy** : "Tu peux être profitable avec n'importe quelle stratégie, l'indépendant est la psycho + risk." Non-codable : c'est un conseil humain.
- **Rule 4 — Patience + discipline** : "I will be patient" écrit 3× dans un journal. Non-codable.
- **Rule 5 — Trading plan = strategy + risk plan** : meta-rule sur le fait d'avoir un plan. Le bot a déjà un plan (YAMLs + risk_engine).

## 5. Conditions fertiles
NON-APPLICABLE (pas de setup).

## 6. Conditions stériles
NON-APPLICABLE. Ce que TJR dit : **ne pas trader** quand on est émotionnel (post-win high, post-loss revenge), quand on n'a pas de plan, quand on veut "get rich quick".

## 7. Contradictions internes / red flags
- **Red flag majeur** : TJR dit rule 3 "tu peux être profitable avec n'importe quelle stratégie, l'important est psycho+risk" — **cette affirmation est empiriquement contredite par notre corpus**. Nous avons testé 26 playbooks + 6 MASTER families, toutes négatives sur SPY/QQQ 2025 intraday avec risk mgmt correct. La stratégie compte.
- **Claim non-vérifiable** : "98% of traders fail" — statement retail classique, pas de source.
- **Capital-gated implicite** : la vidéo suppose qu'on peut se permettre 2 ans d'apprentissage unprofitable ("I spent 2 years as unprofitable trader"), ce qui revient à dire que c'est un hobby de riche.
- **"Just stop taking trades off of order blocks, boom, profitable"** — exemple hyper simpliste pour illustrer le journaling ; en réalité les OB peuvent être -EV mais leur exclusion seule ne rend pas un compte profitable.
- **"Be patient, be disciplined"** répété mais jamais opérationnalisé en règle testable.

## 8. Croisement avec MASTER (contexte bot actuel)
- **Concepts MASTER confirmés** : aucun (hors scope).
- **Concepts MASTER nuancés/précisés** : aucun (hors scope).
- **Concepts MASTER contredits** : aucun (hors scope).
- **Concepts nouveaux absents de MASTER** : aucun. C'est une vidéo "meta" sans contenu ICT.

## 9. Codability (4Q + 1Q classification)
- **Q1 Briques moteur existent ?** OUI — caps session, risk-per-trade, cooldown, journaling trades parquet déjà présents dans `risk_engine.py` / `backend/data/backtest_results/`.
- **Q2 Corpus disponible ?** NON-APPLICABLE (pas de setup à backtester).
- **Q3 Kill rules falsifiables possibles ?** NON (rules psychologiques non-falsifiables empiriquement sur un bot).
- **Q4 Gate §20 Cas attendu identifié ?** NON-APPLICABLE.
- **Q5 Classification** : **pédagogique** (meta-rules humaines, ≠ playbook, ≠ filtre, ≠ contexte, ≠ management codable).

## 10. Valeur pour le bot
**Faible / zéro actionnable nouveau.** Toutes les règles opérationnelles sont déjà en place :
- Rule 1 (daily cap) : déjà via `max_trades_per_session` + `max_daily_loss_r`.
- Rule 2 (journaling) : déjà via parquets trades per-campaign.
- Rule 6 (risk mgmt) : déjà via `max_risk_r_per_trade` + position-sizing.
- Rules 3/4/5 : pas codables (psychologie humaine).
Seul point à retenir : **Rule 3 contredite empiriquement par notre bot** — la stratégie compte, et 10 data points négatifs prouvent que "psycho+risk seuls" ne suffisent pas. Pas de nouveau playbook, pas de nouvel overlay, pas de nouveau filtre de régime, pas de nouvelle logique TP. À classer "content zéro" pour DexterioBOT.

## 11. Citation-clés
- *"Rule number one is just knowing when to turn off the charts. If you win money for the day, especially when you guys are in the early phases of trading, turn it off."* — [26.56–35.04] — confirme le `max_trades_per_session` existant et suggère un kill-switch "one winner, stop".
- *"Strategy just gives you the probability. And then on top of that, you need the psychology to be able to stick to the strategy and the psychology to be able to stick to your risk management plan."* — [302.0–310.3] — le point le plus cité de la vidéo, **et empiriquement faux pour notre bot** : 10 data points négatifs avec risk mgmt parfait.
- *"You can have the best strategy in the world... If you are risking your entire account every single trade, guess what? One of those 3% times is going to come around and then boom, squad wipe."* — [672–692] — fonde le plafonnement du risk per-trade, déjà en place.
