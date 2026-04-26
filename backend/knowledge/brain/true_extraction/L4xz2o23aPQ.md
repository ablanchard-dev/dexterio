# L4xz2o23aPQ — Path to Profitability: Time Theory Explained

**Source** : https://youtu.be/L4xz2o23aPQ · TJR · 662.48s (~11min) · auto-generated EN captions
**Date extraction** : 2026-04-24

## 1. Thèse centrale
Le marché NY a des fenêtres temporelles exploitables fixes : manipulation de 9:30 à 9:50 ET, puis entrée idéale de 9:50 à 10:10 ET (macro window). Pas de trade acceptable après 10:30 ET ("done for the day"). Les sessions Asia/London servent de draws on liquidity pour le NY.

## 2. Mécanisme complet
- **HTF bias** : NON-SPÉCIFIÉ dans cette vidéo (renvoi vidéo "advanced liquidity concept" pour session highs/lows comme draws)
- **Setup TF** : 5m / 1m intraday ; regarde manipulation durant 9:30-9:50 window
- **Entry trigger** : après manipulation (sweep d'un high/low), retrace, entrée idéale entre 9:50-10:10 ET ("macro window")
- **Stop loss** : NON-SPÉCIFIÉ précisément dans cette vidéo
- **Take profit** : "high time frame draw on liquidity" (ex. highs d'Asia, London, previous day) — visé explicitement comme liquidity target, pas fixed RR
- **Exit logic** : session-end implicite — "done for the day" à 10:30 si pas de trade, PM session 13:00 possible mais TJR ne la trade pas
- **Sizing** : NON-SPÉCIFIÉ

## 3. Règles fermées (codables telles quelles)
- Asian session : 18:00-03:00 ET
- London session : 03:00-08:30 ET (overlap techniquement jusqu'à 11:30 ET mais on arrête quand la suivante ouvre)
- NY pre-market : 08:30-09:30 ET (manipulation pré-market "très typique")
- NY RTH : 09:30-17:00 ET
- Spread hour : 17:00-18:00 ET (no market open, spreads s'élargissent)
- Manipulation window RTH : 09:30-09:50 ET (fenêtre principale — bare minimum)
- Entry window macro : 09:50-10:10 ET (ideal entry time)
- Cut-off daily : pas de trade après 10:30 ET ("market tends to slow down")
- PM session : 13:00 ET (existe mais TJR ne trade pas)

## 4. Règles floues / discrétionnaires (nécessitent interprétation)
- "Sometimes the manipulation happens 9:30 to 9:40, and there's an entry at 9:45" — la fenêtre n'est pas point-blank
- "I take trades at 10:20 sometimes. I take trades at 9:45 sometimes" — contradiction avec règle fermée ci-dessus
- "Bare minimum, some form of manipulation between 9:30 to 9:50" — "some form" non-défini opérationnellement
- High-impact news day = "not going to be super beneficial" — quel filtre news ? non-spécifié

## 5. Conditions fertiles
- NY RTH open 9:30 (nouvelle money entrant, manipulation attendue)
- Jours normaux sans news macro haute
- Présence de liquidity pools (session highs/lows, previous day) à portée pour target

## 6. Conditions stériles
- High-impact news day (explicitement : "isn't going to be super beneficial for us")
- Price action "kind of sucks" days (Monday exemple où manipulation window = "literally nothing")
- Pas de pool de liquidity identifiable comme draw
- Après 10:30 ET (market slows down)

## 7. Contradictions internes / red flags
- Dit "cut-off 10:30" puis "I take trades at 10:20 sometimes". Incohérent — la règle est "preferred window" pas absolute.
- "Happens every single day" affirmé, puis Monday exemple ne le montre pas clairement ("this isn't a very good example") — survivorship bias dans la présentation.
- Aucune donnée sur hit rate historique, E[R], WR. Zéro métrique quantitative.
- "Sometimes 9:45", "sometimes 10:20" — la fenêtre est plus discrétionnaire qu'elle n'en a l'air.

## 8. Croisement avec MASTER (contexte bot actuel)
- **Concepts MASTER confirmés** : sessions Asia/London/NY comme structure temporelle, NY open comme catalyseur de manipulation, liquidity pools (highs/lows de session) comme draws et targets.
- **Concepts MASTER nuancés/précisés** :
  - MASTER mentionne "sessions" ; cette vidéo précise les bornes horaires exactes ET (18:00/03:00/08:30/09:30/17:00/18:00)
  - Macro window 09:50-10:10 précisée (TJR call ça "the macro" — concept ICT existant mais souvent flou dans MASTER)
  - Spread hour 17:00-18:00 explicitée
- **Concepts MASTER contredits** : aucun
- **Concepts nouveaux absents de MASTER** :
  - Cut-off 10:30 explicite ("if I can't find a trade by 10:30, I'm done for the day")
  - Pre-market 08:30-09:30 comme fenêtre de "pre-market manipulation" à observer (distinct de RTH manipulation)
  - PM session 13:00 explicitée mais out-of-scope TJR

## 9. Codability (4Q + 1Q classification)
- Q1 Briques moteur existent ? OUI — session windows déjà dans `patterns_config.yml`, alias `NY_Open` etc. `PREMARKET_NY` alias ajouté Leg 3.
- Q2 Corpus disponible ? OUI — 2025 SPY/QQQ 1m/5m RTH couvert.
- Q3 Kill rules falsifiables ? OUI — filtre "entry only 09:50-10:10 ET" = simple boolean gate, testable en A/B.
- Q4 Gate §20 Cas attendu ? **Contexte/filtre, pas playbook** — probable Cas A si corpus 91% déjà RTH (comme VIX Leg 4.2), Cas C si degrade baseline.
- Q5 Classification : **filtre temporel + contexte pédagogique** (pas un playbook autonome)

## 10. Valeur pour le bot
- **Overlay time-gate** candidat : restriction entry window 09:50-10:10 ET sur les survivors (News_Fade, Engulfing, Session_Open, Liquidity_Sweep). Facile à implémenter (1 gate booléen).
- **Risque** : corpus 2025 survivor_v1 déjà "91% en bande fertile" analogie VIX Leg 4.2 — si majorité des trades déjà dans cette fenêtre, effet nul ou destructeur (perd n<30). À tester mais basse priorité.
- **Cut-off 10:30** potentiellement utile comme kill-switch daily ("no new trade after 10:30"). À tester sur survivor_v1.
- **Pas de nouveau playbook**. Contenu trop mince pour standalone. 90% overlap avec savoir ICT générique.

## 11. Citations-clés
- "We have open at 9:30, we have manipulation from 9:30 to 9:50, and then from 9:50 really till like 10:10... we have our entry period."
- "If I can't find a trade by 10:30, I'm done for the day, because that's when the market tends to slow down."
- "This doesn't have to be point-blank period, like we can only look to enter at 9:50 to 10:10. That's not the case. I take trades at 10:20 sometimes. I take trades at 9:45 sometimes."
