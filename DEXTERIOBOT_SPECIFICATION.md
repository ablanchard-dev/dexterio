# DexterioBOT Daily & Scalping - Spécification Complète

## Document de Référence Technique
**Version:** 1.0  
**Date:** Janvier 2025  
**Objectif:** Bot de trading algorithmique pour SP500/Nasdaq avec stratégies ICT/TJR/Alex

---

## TABLE DES MATIÈRES

1. [Vue d'ensemble](#1-vue-densemble)
2. [Architecture Modulaire](#2-architecture-modulaire)
3. [Stratégies & Playbooks](#3-stratégies--playbooks)
4. [Patterns de Chandeliers](#4-patterns-de-chandeliers)
5. [Money Management & Risk Engine](#5-money-management--risk-engine)
6. [Modes de Trading](#6-modes-de-trading)
7. [Journalisation & Amélioration Continue](#7-journalisation--amélioration-continue)
8. [Roadmap d'Implémentation](#8-roadmap-dimplémentation)

---

## 1. VUE D'ENSEMBLE

### 1.1 Objectif Global

**DexterioBOT Daily & Scalping** est un agent de trading algorithmique conçu pour :
- Trader **SP500 (ES/SPY)** et **Nasdaq 100 (NQ/QQQ)** en intraday
- Exécuter **1-2 trades de Daily Trading** + **0-2 trades de Scalping** par jour
- Maximiser le **winrate** avec une approche "sniper" (Mode SAFE)
- Offrir une option agressive pour plus d'opportunités (Mode AGRESSIF)

### 1.2 Instruments & Timeframes

**Instruments obligatoires:**
- **SP500:** ES (futures) / SPY (ETF)
- **Nasdaq 100:** NQ (futures) / QQQ (ETF)

**Extension future:**
- Forex paires majeures (EURUSD, GBPUSD, USDJPY)

**Timeframes:**
- **Flux temps réel:** M1 (1 minute)
- **Agrégation:** M5, M15, H1, H4, Daily
- **Analyse HTF:** Daily, H4, H1
- **Micro-structure:** M1, M5

**Sessions de trading:**
- **Asie (18h-2h ET):** Définition du range nocturne, draw on liquidity
- **Londres (3h-11h ET):** Sweeps, fake-outs, manipulation
- **New York (9h30-16h ET):** Session principale
  - **Kill Zone matin:** 9h30-11h
  - **Kill Zone après-midi:** 14h-15h30

### 1.3 Philosophie de Trading (TJR)

**Principes fondamentaux:**
1. **Prédire le prix, pas courir après l'argent** - Focus sur la qualité des setups
2. **Patience & Discipline** - Attendre les meilleures configurations
3. **Vision long terme** - Marathon, pas sprint
4. **Psychologie > Stratégie** - Contrôle émotionnel prioritaire
5. **Simplicité** - Moins c'est plus, maîtriser un système cohérent
6. **Journaling systématique** - Apprendre de chaque trade

---

## 2. ARCHITECTURE MODULAIRE

### 2.1 Module Flux de Marchés (Data Feed)

**Responsabilités:**
- Connexion aux sources de données temps réel
- Construction des bougies M1 en temps réel
- Agrégation en M5, M15, H1, H4, Daily
- Synchronisation horaire (sessions Asie/Londres/NY)

**Sources de données:**
- **V1 (Dev/Test):** Yahoo Finance (yfinance) + replay simulé
- **V2 (Live):** Finnhub WebSocket (variable: `FINNHUB_API_KEY`)

**Implémentation:**
```python
class DataFeedEngine:
    def __init__(self, symbols=['SPY', 'QQQ'], source='yfinance'):
        self.symbols = symbols
        self.source = source
        self.candles = {tf: [] for tf in ['M1', 'M5', 'M15', 'H1', 'H4', 'D']}
    
    def connect_websocket(self):
        """Connexion Finnhub WebSocket en V2"""
        pass
    
    def aggregate_candles(self, m1_candle):
        """Agrège M1 vers timeframes supérieurs"""
        pass
    
    def get_session_info(self, timestamp):
        """Détermine session (Asie/Londres/NY)"""
        pass
```

### 2.2 Module Analyse HTF & Biais (Market State Engine)

**Responsabilités:**
- Analyse top-down (Daily → H4 → H1)
- Détermination du biais directionnel du jour
- Classification du profil de session
- Identification des niveaux HTF importants

**Profils de Session (TJR):**
1. **Session précédente plate (consolidation)** → Attente manipulation + reversal
2. **Session précédente avec manipulation sans gros trend** → Attente reversal principal
3. **Session précédente avec manipulation & trend** → Attente continuation

**Biais directionnel:**
- **Bullish:** Recherche de longs (continuations haussières, reversals haussiers)
- **Bearish:** Recherche de shorts (continuations baissières, reversals baissiers)
- **Neutre/Range:** Attente de breakout directionnel

**Niveaux HTF à marquer:**
- Previous Day High/Low (PDH/PDL)
- Session Highs/Lows (Asia, London, NY)
- FVG HTF (Daily, H4)
- Zones de liquidité (relative equal highs/lows)
- Order Blocks HTF

**Implémentation:**
```python
class MarketStateEngine:
    def __init__(self):
        self.bias = None  # 'bullish', 'bearish', 'neutral'
        self.session_profile = None  # 1, 2, ou 3
        self.htf_levels = {}
    
    def analyze_daily_h4_h1(self, daily_data, h4_data, h1_data):
        """Analyse HTF pour déterminer biais"""
        # 1. Identifier structure Daily (HH/HL ou LH/LL)
        # 2. Vérifier manipulation sessions précédentes
        # 3. Marquer liquidité prise/non prise
        # 4. Définir biais du jour
        pass
    
    def classify_session_profile(self, previous_session_data):
        """Classe le profil selon les 3 types TJR"""
        pass
    
    def mark_htf_levels(self, data):
        """Marque PDH/PDL, FVG HTF, etc."""
        pass
```

### 2.3 Module Détection de Liquidité & Manipulation

**Responsabilités:**
- Maintenir liste des niveaux de liquidité pertinents
- Détecter les sweeps (chasse de stops)
- Émettre alertes "liquidité prise sur [niveau X]"
- Gérer surveillance temporelle

**Types de liquidité:**
- **Session Highs/Lows:** Asia High/Low, London High/Low
- **Previous Day Highs/Lows**
- **Relative Equal Highs/Lows:** Clusters d'ordres
- **Trendline Liquidity:** Au-dessus/en-dessous de trendlines

**Détection de Sweep:**
- Prix franchit niveau + X ticks (ex: 3-5 ticks)
- Retour rapide en dessous/au-dessus du niveau
- Formation d'une bougie de rejet (pin bar, engulfing)

**Implémentation:**
```python
class LiquidityEngine:
    def __init__(self):
        self.liquidity_levels = []
        self.swept_levels = []
    
    def add_liquidity_level(self, level, level_type, timeframe):
        """Ajoute niveau de liquidité à surveiller"""
        self.liquidity_levels.append({
            'price': level,
            'type': level_type,  # 'high', 'low', 'equal_highs', etc.
            'timeframe': timeframe,
            'swept': False
        })
    
    def detect_sweep(self, current_candle, level):
        """Détecte si sweep s'est produit"""
        # Critères:
        # - Wick dépasse niveau de X ticks
        # - Close retourne de l'autre côté
        # - Formation de rejection candle
        pass
    
    def emit_sweep_alert(self, level):
        """Émet alerte sweep détecté"""
        pass
```

### 2.4 Module Pattern Recognition

**Responsabilités:**
- Détection des patterns ICT (BOS, CHOCH, FVG, SMT)
- Reconnaissance des patterns de chandeliers
- Calcul des confluences techniques
- Scoring de qualité des setups

**Sous-modules:**

#### 2.4.1 Détection BOS/CHOCH (Break of Structure)
```python
def detect_bos(self, timeframe, direction):
    """
    Détecte cassure de structure sur micro-TF (M1/M5)
    
    BOS Haussier:
    - Close au-dessus du dernier pivot high
    
    BOS Baissier:
    - Close en-dessous du dernier pivot low
    """
    pass

def detect_choch(self, timeframe):
    """
    Change of Character = changement de dynamique
    - Implicit dans BOS opposé au mouvement précédent
    """
    pass
```

#### 2.4.2 Détection Fair Value Gap (FVG)
```python
def detect_fvg(self, candles):
    """
    FVG = Gap d'inefficacité sur 3 bougies
    
    FVG Bullish:
    - High de bougie 1 < Low de bougie 3
    
    FVG Bearish:
    - Low de bougie 1 > High de bougie 3
    """
    fvgs = []
    for i in range(len(candles) - 2):
        c1, c2, c3 = candles[i:i+3]
        
        # FVG Bullish
        if c1['high'] < c3['low']:
            fvgs.append({
                'type': 'bullish',
                'top': c3['low'],
                'bottom': c1['high'],
                'midpoint': (c3['low'] + c1['high']) / 2
            })
        
        # FVG Bearish
        if c1['low'] > c3['high']:
            fvgs.append({
                'type': 'bearish',
                'top': c1['low'],
                'bottom': c3['high'],
                'midpoint': (c1['low'] + c3['high']) / 2
            })
    
    return fvgs
```

#### 2.4.3 Détection SMT Divergence
```python
def detect_smt(self, spy_data, qqq_data):
    """
    Smart Money Technique - Divergence entre indices corrélés
    
    SMT Bearish:
    - QQQ fait nouveau high
    - SPY ne confirme pas (lower high)
    
    SMT Bullish:
    - QQQ fait nouveau low
    - SPY ne confirme pas (higher low)
    """
    pass
```

#### 2.4.4 Reconnaissance Patterns de Chandeliers

**Patterns prioritaires (de la bible des chandeliers):**

**Patterns de Reversal Bullish:**
1. **Hammer** - Petit corps en haut, longue ombre basse (≥2x corps)
2. **Bullish Engulfing** - Bougie haussière englobe bougie baissière précédente
3. **Morning Star** - 3 bougies: bearish + petit corps + bullish fort
4. **Piercing Line** - Bougie haussière clôture >50% dans corps bearish précédent
5. **Bullish Harami** - Petit corps haussier contenu dans grand corps bearish
6. **Dragonfly Doji** - Doji avec longue ombre basse

**Patterns de Reversal Bearish:**
1. **Shooting Star** - Petit corps en bas, longue ombre haute (≥2x corps)
2. **Bearish Engulfing** - Bougie baissière englobe bougie haussière précédente
3. **Evening Star** - 3 bougies: bullish + petit corps + bearish fort
4. **Dark Cloud Cover** - Bougie baissière clôture >50% dans corps bullish précédent
5. **Bearish Harami** - Petit corps baissier contenu dans grand corps bullish
6. **Gravestone Doji** - Doji avec longue ombre haute

**Patterns de Continuation:**
1. **Three White Soldiers** - 3 bougies haussières consécutives avec clôtures progressives
2. **Three Black Crows** - 3 bougies baissières consécutives avec clôtures progressives
3. **Bullish/Bearish Marubozu** - Corps plein sans ombres, forte conviction

**Patterns d'Indécision:**
1. **Doji** - Open = Close, indécision marché
2. **Spinning Top** - Petit corps, ombres égales des deux côtés
3. **High Wave** - Petit corps, longues ombres haut et bas

**Implémentation:**
```python
class CandlestickPatternEngine:
    
    def detect_hammer(self, candle):
        """Hammer: corps petit en haut, ombre basse ≥2x corps"""
        body = abs(candle['close'] - candle['open'])
        lower_wick = min(candle['open'], candle['close']) - candle['low']
        upper_wick = candle['high'] - max(candle['open'], candle['close'])
        
        if lower_wick >= 2 * body and upper_wick < body * 0.1:
            return {'pattern': 'hammer', 'strength': 'strong' if lower_wick >= 3 * body else 'medium'}
        return None
    
    def detect_engulfing(self, candle1, candle2):
        """Engulfing: bougie 2 englobe complètement bougie 1"""
        # Bullish Engulfing
        if (candle1['close'] < candle1['open'] and  # C1 bearish
            candle2['close'] > candle2['open'] and  # C2 bullish
            candle2['open'] <= candle1['close'] and
            candle2['close'] >= candle1['open']):
            return {'pattern': 'bullish_engulfing', 'strength': 'strong'}
        
        # Bearish Engulfing
        if (candle1['close'] > candle1['open'] and  # C1 bullish
            candle2['close'] < candle2['open'] and  # C2 bearish
            candle2['open'] >= candle1['close'] and
            candle2['close'] <= candle1['open']):
            return {'pattern': 'bearish_engulfing', 'strength': 'strong'}
        
        return None
    
    def detect_morning_star(self, c1, c2, c3):
        """Morning Star: bearish + petit corps + bullish fort"""
        c1_bearish = c1['close'] < c1['open']
        c2_small = abs(c2['close'] - c2['open']) < abs(c1['close'] - c1['open']) * 0.3
        c3_bullish = c3['close'] > c3['open']
        c3_closes_high = c3['close'] > (c1['open'] + c1['close']) / 2
        
        if c1_bearish and c2_small and c3_bullish and c3_closes_high:
            return {'pattern': 'morning_star', 'strength': 'strong'}
        return None
    
    def detect_doji(self, candle):
        """Doji: open ≈ close (tolérance 0.1% du range)"""
        body = abs(candle['close'] - candle['open'])
        total_range = candle['high'] - candle['low']
        
        if body <= total_range * 0.001:
            # Classifier type de doji
            lower_wick = min(candle['open'], candle['close']) - candle['low']
            upper_wick = candle['high'] - max(candle['open'], candle['close'])
            
            if lower_wick >= 2 * upper_wick:
                return {'pattern': 'dragonfly_doji', 'strength': 'medium'}
            elif upper_wick >= 2 * lower_wick:
                return {'pattern': 'gravestone_doji', 'strength': 'medium'}
            else:
                return {'pattern': 'standard_doji', 'strength': 'weak'}
        return None
```

### 2.5 Module Playbook Engine

**Playbooks basés sur ICT/TJR/Alex:**

#### Playbook 1: NY Open Reversal (Fake Breakout)
```python
{
    'name': 'NY_Open_Reversal',
    'description': 'Faux départ à l\'ouverture NY puis inversion',
    'conditions': [
        'Range Asie clairement défini',
        'Londres casse un extrême du range (sweep)',
        'Pas de suivi durable du breakout',
        'BOS opposé sur M1/M5 après sweep',
        'Alignement avec biais HTF'
    ],
    'timing': '9h30-10h30 ET',
    'entry': 'Limit order sur FVG ou 50% du sweep',
    'stop_loss': 'Au-delà du sweep high/low + 3-5 ticks',
    'take_profit': 'Extrémité opposée du range / Pool de liquidité',
    'risk_reward': '≥2:1',
    'quality': 'A+'
}
```

#### Playbook 2: London Sweep / Fake Breakout
```python
{
    'name': 'London_Sweep',
    'description': 'Fake breakout session Londres puis reversal NY',
    'conditions': [
        'Range Asie marqué',
        'Londres casse High/Low Asie',
        'Retour dans le range rapidement',
        'BOS dans direction opposée',
        'FVG créé sur la cassure'
    ],
    'timing': '8h-10h ET',
    'entry': 'Sur pullback dans FVG',
    'stop_loss': 'Au-delà du sweep',
    'take_profit': 'Opposé du range Asie',
    'risk_reward': '≥2:1',
    'quality': 'A+'
}
```

#### Playbook 3: Continuation de Tendance sur Pullback
```python
{
    'name': 'Trend_Continuation_Pullback',
    'description': 'Rejoindre tendance établie sur correction',
    'conditions': [
        'Biais HTF clairement établi (Daily/H4)',
        'Prix revient sur zone technique (FVG, Order Block)',
        'Structure fractale se reforme (BOS dans sens trend)',
        'Présence FVG dans zone pullback'
    ],
    'timing': 'Toute session NY',
    'entry': 'Limit sur FVG ou niveau optimal',
    'stop_loss': 'Sous/au-dessus du pullback low/high',
    'take_profit': 'Nouveaux extremes / Extension Fib',
    'risk_reward': '≥1.5:1',
    'quality': 'A'
}
```

#### Playbook 4: Manipulation + Reversal (ICT)
```python
{
    'name': 'ICT_Manipulation_Reversal',
    'description': 'Sweep de liquidité + BOS opposé',
    'conditions': [
        'Niveau de liquidité identifié (PDH/PDL, Equal Highs/Lows)',
        'Sweep du niveau confirmé',
        'BOS opposé sur M1/M5',
        'FVG créé sur BOS',
        'SMT divergence favorable (optionnel)',
        'Alignement biais HTF'
    ],
    'timing': 'Kill zones (9h30-11h, 14h-15h30)',
    'entry': 'Retracement dans FVG à 50% ou optimal entry',
    'stop_loss': 'Au-delà du sweep + buffer',
    'take_profit': 'Pool de liquidité opposé',
    'risk_reward': '≥2:1',
    'quality': 'A+'
}
```

### 2.6 Module Setup Engine

**Responsabilité:** Fusion des signaux pour scorer et classer les setups.

**Scoring vectoriel:**
```
Score Setup = w1 × ICT_Score + w2 × Pattern_Score + w3 × Playbook_Score

Avec:
- ICT_Score: Présence Sweep (0.3) + BOS (0.3) + FVG (0.2) + SMT (0.2)
- Pattern_Score: Qualité pattern chandelier (0-1)
- Playbook_Score: Alignement avec playbook connu (0-1)

Poids par défaut: w1=0.4, w2=0.3, w3=0.3
```

**Classification des setups:**
- **A+** : Score ≥ 0.85, toutes confluences présentes
- **A** : Score ≥ 0.70, confluences majeures présentes
- **B** : Score ≥ 0.55, confluences partielles
- **C** : Score < 0.55, configuration faible (ignoré)

**Implémentation:**
```python
class SetupEngine:
    def __init__(self):
        self.weights = {'ict': 0.4, 'pattern': 0.3, 'playbook': 0.3}
    
    def calculate_ict_score(self, setup_data):
        """Score basé sur présence éléments ICT"""
        score = 0.0
        if setup_data.get('sweep'): score += 0.3
        if setup_data.get('bos'): score += 0.3
        if setup_data.get('fvg'): score += 0.2
        if setup_data.get('smt'): score += 0.2
        return score
    
    def calculate_pattern_score(self, pattern_data):
        """Score basé sur qualité pattern chandelier"""
        if not pattern_data:
            return 0.0
        
        strength_map = {'strong': 1.0, 'medium': 0.7, 'weak': 0.4}
        return strength_map.get(pattern_data.get('strength'), 0.0)
    
    def calculate_playbook_score(self, playbook_match):
        """Score basé sur alignement playbook"""
        if not playbook_match:
            return 0.0
        
        conditions_met = playbook_match.get('conditions_met', 0)
        total_conditions = playbook_match.get('total_conditions', 1)
        return conditions_met / total_conditions
    
    def score_setup(self, setup_data):
        """Calcule score final et classe le setup"""
        ict_score = self.calculate_ict_score(setup_data)
        pattern_score = self.calculate_pattern_score(setup_data.get('pattern'))
        playbook_score = self.calculate_playbook_score(setup_data.get('playbook'))
        
        final_score = (
            self.weights['ict'] * ict_score +
            self.weights['pattern'] * pattern_score +
            self.weights['playbook'] * playbook_score
        )
        
        # Classification
        if final_score >= 0.85:
            quality = 'A+'
        elif final_score >= 0.70:
            quality = 'A'
        elif final_score >= 0.55:
            quality = 'B'
        else:
            quality = 'C'
        
        return {
            'score': final_score,
            'quality': quality,
            'ict_score': ict_score,
            'pattern_score': pattern_score,
            'playbook_score': playbook_score
        }
```

---

## 3. STRATÉGIES & PLAYBOOKS

### 3.1 Daily Trading (1-2 trades/jour)

**Objectif:** Trades de haute qualité avec R:R élevé et winrate prioritaire.

**Process quotidien:**

1. **Pré-ouverture NY (avant 9h30 ET):**
   - Analyser Daily/H4/H1 pour biais
   - Marquer range Asie (High/Low)
   - Identifier si Londres a manipulé/sweeped
   - Noter niveaux de liquidité clés
   - Déterminer profil de session attendu

2. **Session NY (9h30-16h):**
   - Surveiller ouverture pour fake breakout potentiel
   - Attendre sweep + BOS confirmé
   - Vérifier confluences (FVG, pattern, SMT)
   - Valider alignement avec biais HTF

3. **Critères d'entrée Daily (Mode SAFE):**
   - Setup qualité **A+** uniquement
   - Minimum 4 confluences sur 6:
     * ✓ Sweep de liquidité clair
     * ✓ BOS opposé confirmé
     * ✓ FVG présent
     * ✓ Pattern chandelier valide
     * ✓ Alignement biais HTF
     * ✓ SMT divergence favorable (optionnel mais fort)
   - Timing dans kill zone
   - R:R ≥ 2:1

**Exemple de Trade Daily:**
```
Contexte:
- Biais: Bearish (Daily en downtrend, PDH non cassé)
- Range Asie: 450.20 - 451.80
- Londres: Sweep du high Asie à 452.10 à 8h15

Setup:
- 9h35: Prix fait nouveau high à 452.30 (sweep PDH)
- 9h42: BOS bearish sur M5 (casse pivot low à 451.60)
- FVG bearish créé entre 452.10-451.85
- Pattern: Bearish Engulfing sur M5
- SMT: QQQ fait higher high, SPY ne confirme pas

Entrée:
- Type: Limit order à 452.00 (50% FVG)
- Entry: 452.00
- Stop Loss: 452.45 (au-dessus sweep + 15 ticks)
- Take Profit 1: 450.50 (Low Asie)
- Take Profit 2: 449.80 (PDL)

Risque:
- Distance SL: 0.45 points
- Capital risqué: 2% ($1000 sur compte $50k)
- Taille position: Calculée pour risquer $1000 sur 0.45 points
- R:R: 3:1 (TP2)

Résultat: +2.20 points, +$2,200 (+4.4%)
```

### 3.2 Scalping (0-2 trades/jour)

**Objectif:** Trades rapides dans kill zones, même logique structurée.

**Différences vs Daily Trading:**
- **Timeframes:** Focus M1/M5 principalement
- **Durée:** 5-30 minutes par trade
- **R:R:** Minimum 1.5:1 (plus court)
- **Targets:** Niveaux intermédiaires, FVG opposés, round numbers

**Process Scalping:**

1. **Identification de la kill zone:**
   - 9h30-10h15: Ouverture NY (volatilité max)
   - 10h-11h: Post-ouverture (réaction aux news)
   - 14h-15h: Fin de journée (repositionnement)

2. **Critères d'entrée Scalp (Mode SAFE):**
   - Setup qualité **A+** uniquement
   - Minimum 3 confluences sur 5:
     * ✓ Micro-sweep visible sur M1
     * ✓ BOS M1/M5 confirmé
     * ✓ FVG M1 présent
     * ✓ Pattern chandelier sur M5
     * ✓ Dans sens du biais Daily
   - R:R ≥ 1.5:1

**Exemple de Scalp:**
```
Contexte:
- Biais: Bullish (Daily uptrend)
- Daily Trade: Déjà pris +2R ce matin
- Heure: 14h05 (Kill zone après-midi)

Setup:
- 14h05: Micro-sweep du low à 453.20 sur M1
- 14h08: BOS bullish M1 (casse pivot high à 453.45)
- FVG bullish créé entre 453.25-453.35
- Pattern: Bullish Pin Bar sur M5

Entrée:
- Type: Limit à 453.30 (dans FVG)
- Entry: 453.30
- Stop Loss: 453.15 (sous sweep)
- Take Profit: 453.70 (resistance intermédiaire)

Risque:
- Distance SL: 0.15 points
- Capital risqué: 1% ($500 sur $50k)
- R:R: 2.6:1

Résultat: +0.40 points en 18 minutes, +$1,300
```

---

## 4. PATTERNS DE CHANDELIERS

### 4.1 Liste Exhaustive des Patterns Autorisés

**Source:** Candlestick Patterns Bible (50 patterns) + Candle & Breakout Pattern Guide

#### Catégorie A: Patterns de Reversal Bullish (Bottom)

| Pattern | Description | Conditions | Force |
|---------|-------------|------------|-------|
| **Hammer** | Petit corps haut, longue ombre basse | Lower wick ≥2x body, apparaît après downtrend | ★★★★ |
| **Bullish Engulfing** | Bougie verte englobe bougie rouge | C2 ouvre ≤ C1 close, C2 close ≥ C1 open | ★★★★★ |
| **Morning Star** | 3 bougies: red + small + strong green | C3 close > 50% de C1, gap down sur C2 | ★★★★★ |
| **Morning Doji Star** | Morning Star avec Doji au milieu | C2 = Doji, gap down, C3 green fort | ★★★★ |
| **Piercing Line** | Green close >50% dans red précédent | C2 ouvre sous C1 low, close >50% C1 body | ★★★★ |
| **Bullish Harami** | Petit green dans grand red | C2 body complètement dans C1 body | ★★★ |
| **Dragonfly Doji** | Doji avec longue ombre basse | Open=Close, lower wick ≥2x body | ★★★ |
| **Three White Soldiers** | 3 bougies vertes progressives | Chaque open dans body précédent, closes ascendants | ★★★★★ |
| **Tweezer Bottom** | 2 bougies avec lows identiques | C1 & C2 ont même low, C2 bullish | ★★★ |
| **Bullish Belt Hold** | Long green sans lower wick | Open = Low, strong buying from open | ★★★ |
| **Abandoned Baby Bullish** | Doji gap avec reversal | C2 doji gap down, C3 green gap up | ★★★★ |
| **Bullish Kicker** | Red puis green avec gap up | C2 ouvre ≥ C1 open, fort gap | ★★★★★ |
| **Three Outside Up** | Engulfing + confirmation | C1-C2 = Engulfing, C3 close > C2 | ★★★★ |
| **Three Inside Up** | Harami + confirmation | C1-C2 = Harami, C3 close > C1 high | ★★★ |
| **Inverted Hammer** | Petit corps bas, longue ombre haute | Upper wick ≥2x body, après downtrend | ★★★ |

#### Catégorie B: Patterns de Reversal Bearish (Top)

| Pattern | Description | Conditions | Force |
|---------|-------------|------------|-------|
| **Shooting Star** | Petit corps bas, longue ombre haute | Upper wick ≥2x body, après uptrend | ★★★★ |
| **Bearish Engulfing** | Bougie rouge englobe bougie verte | C2 ouvre ≥ C1 close, C2 close ≤ C1 open | ★★★★★ |
| **Evening Star** | 3 bougies: green + small + strong red | C3 close < 50% de C1, gap up sur C2 | ★★★★★ |
| **Evening Doji Star** | Evening Star avec Doji milieu | C2 = Doji, gap up, C3 red fort | ★★★★ |
| **Dark Cloud Cover** | Red close >50% dans green précédent | C2 ouvre au-dessus C1 high, close <50% C1 | ★★★★ |
| **Bearish Harami** | Petit red dans grand green | C2 body complètement dans C1 body | ★★★ |
| **Gravestone Doji** | Doji avec longue ombre haute | Open=Close, upper wick ≥2x body | ★★★ |
| **Three Black Crows** | 3 bougies rouges progressives | Chaque open dans body précédent, closes descendants | ★★★★★ |
| **Hanging Man** | Hammer mais au top | Identique à Hammer, contexte = uptrend | ★★★★ |
| **Tweezer Top** | 2 bougies avec highs identiques | C1 & C2 ont même high, C2 bearish | ★★★ |
| **Bearish Belt Hold** | Long red sans upper wick | Open = High, strong selling from open | ★★★ |
| **Abandoned Baby Bearish** | Doji gap avec reversal | C2 doji gap up, C3 red gap down | ★★★★ |
| **Bearish Kicker** | Green puis red avec gap down | C2 ouvre ≤ C1 open, fort gap | ★★★★★ |
| **Three Outside Down** | Engulfing bearish + confirmation | C1-C2 = Engulfing, C3 close < C2 | ★★★★ |
| **Three Inside Down** | Harami bearish + confirmation | C1-C2 = Harami, C3 close < C1 low | ★★★ |

#### Catégorie C: Patterns d'Indécision

| Pattern | Description | Usage |
|---------|-------------|-------|
| **Doji** | Open = Close | Indécision, attendre confirmation |
| **Spinning Top** | Petit corps, ombres égales | Indécision, pause dans trend |
| **High Wave** | Petit corps, très longues ombres | Forte volatilité, indécision |

#### Catégorie D: Patterns de Continuation

| Pattern | Description | Contexte |
|---------|-------------|----------|
| **Marubozu Bullish** | Long green sans ombres | Forte conviction, continuation uptrend |
| **Marubozu Bearish** | Long red sans ombres | Forte conviction, continuation downtrend |
| **Bullish Separating Lines** | Continuation après pullback | Red puis green opening au même niveau |
| **Rising Three Methods** | 3 petites corrections dans uptrend | Trend reprend après pause |
| **Falling Three Methods** | 3 petites corrections dans downtrend | Trend reprend après pause |

### 4.2 Intégration dans le Bot

**Priorités de détection:**
1. **Tier 1 (Must-have):** Engulfing, Morning/Evening Star, Hammer/Shooting Star, Three Soldiers/Crows, Doji
2. **Tier 2 (Important):** Harami, Pin Bar, Belt Hold, Piercing/Dark Cloud
3. **Tier 3 (Nice-to-have):** Kicker, Abandoned Baby, Tweezer, Three Outside/Inside

**Usage:**
- Patterns seuls ne suffisent pas → Doivent être combinés avec ICT + Playbooks
- Patterns renforcent score de setup (+0.2 à +0.4 selon force)
- Pattern contradictoire avec biais HTF → Invalidation du setup

---

## 5. MONEY MANAGEMENT & RISK ENGINE

### 5.1 Règles de Base (TJR)

**Risque par trade:**
- **Base:** 2% du capital par trade
- **Après perte:** 1% jusqu'à trade gagnant
- **Après gain:** Retour à 2%

**Exemple avec capital $50,000:**
```
Trade 1: Risque 2% = $1,000 → Perte → Solde $49,000
Trade 2: Risque 1% = $490 → Perte → Solde $48,510
Trade 3: Risque 1% = $485 → Gain +2R → Solde $49,480
Trade 4: Risque 2% = $990 → Continuer...
```

### 5.2 Schéma de Sizing Dynamique (2% → 1% → 2%)

```python
class RiskEngine:
    def __init__(self, initial_capital):
        self.capital = initial_capital
        self.current_risk_pct = 0.02  # 2%
        self.last_trade_result = None
        self.trades_history = []
    
    def calculate_position_size(self, entry_price, stop_loss, symbol):
        """Calcule taille position basée sur risque"""
        risk_amount = self.capital * self.current_risk_pct
        risk_per_unit = abs(entry_price - stop_loss)
        
        if symbol in ['SPY', 'QQQ']:
            # ETF: 1 share = $X
            position_size = risk_amount / risk_per_unit
        elif symbol in ['ES', 'NQ']:
            # Futures: points × multiplier
            multiplier = 50 if symbol == 'ES' else 20  # ES=$50/pt, NQ=$20/pt
            position_size = risk_amount / (risk_per_unit * multiplier)
        
        return round(position_size, 2)
    
    def update_after_trade(self, trade_result):
        """Met à jour le risque selon résultat trade"""
        self.trades_history.append(trade_result)
        
        if trade_result['pnl'] < 0:
            # Perte: passer à 1%
            self.current_risk_pct = 0.01
        else:
            # Gain: revenir à 2%
            self.current_risk_pct = 0.02
        
        # Mettre à jour capital
        self.capital += trade_result['pnl']
    
    def check_daily_limits(self):
        """Vérifier limites quotidiennes"""
        today_trades = [t for t in self.trades_history if t['date'] == datetime.now().date()]
        
        # Limite pertes/jour
        daily_loss = sum(t['pnl'] for t in today_trades if t['pnl'] < 0)
        max_daily_loss = self.capital * 0.03  # 3% max loss/jour
        
        if abs(daily_loss) >= max_daily_loss:
            return {'can_trade': False, 'reason': 'Max daily loss reached'}
        
        # Limite nombre de trades (Mode SAFE)
        daily_count = len(today_trades)
        if daily_count >= 4:  # 2 Daily + 2 Scalps max
            return {'can_trade': False, 'reason': 'Max trades per day reached'}
        
        return {'can_trade': True}
```

### 5.3 Gestion Multi-Actifs (SPY + QQQ)

**Problématique:** SPY et QQQ sont corrélés → Risque de doubler l'exposition.

**Solutions:**

#### Option 1: Priorité à l'instrument optimal (SMT)
```python
def select_optimal_instrument(spy_setup, qqq_setup, smt_data):
    """Choisir le meilleur instrument selon SMT"""
    if smt_data['type'] == 'bearish':
        # SMT bearish: QQQ plus faible → Shorter QQQ
        return 'QQQ' if qqq_setup['score'] >= spy_setup['score'] else None
    elif smt_data['type'] == 'bullish':
        # SMT bullish: SPY plus fort → Longer SPY
        return 'SPY' if spy_setup['score'] >= qqq_setup['score'] else None
    else:
        # Pas de SMT: choisir le meilleur score
        return 'SPY' if spy_setup['score'] > qqq_setup['score'] else 'QQQ'
```

#### Option 2: Fractionnement du risque
```python
def split_risk_multi_asset(spy_setup, qqq_setup, total_risk_pct=0.02):
    """Prendre les deux mais avec risque fractionné"""
    if spy_setup['quality'] == 'A+' and qqq_setup['quality'] == 'A+':
        # Les deux setups sont excellents
        return {
            'SPY': {'risk_pct': total_risk_pct / 2},  # 1% each
            'QQQ': {'risk_pct': total_risk_pct / 2}
        }
    else:
        # Un seul setup de qualité suffisante
        return {
            'SPY' if spy_setup['score'] > qqq_setup['score'] else 'QQQ': {
                'risk_pct': total_risk_pct
            }
        }
```

### 5.4 Stop Loss & Take Profit

**Stop Loss:**
- **Placement:** Au-delà du niveau invalidant le setup
  - Sweep long: SL sous le sweep low - buffer (3-5 ticks)
  - Sweep short: SL au-dessus du sweep high + buffer
- **Type:** Stop Loss Order (SLO) hard au broker
- **Jamais déplacer vers le haut le SL** (sauf breakeven)

**Take Profit:**
- **TP1 (50% position):** Premier niveau de liquidité / R:R 1.5:1
- **TP2 (30% position):** Deuxième niveau / R:R 2.5:1
- **TP3 (20% position):** Extension / R:R 3:1+

**Break-Even:**
- Déplacer SL à l'entrée après +0.5R de profit latent

**Trailing Stop (optionnel):**
- Activer après +1R
- Trail de 0.3R sous le dernier swing high/low

### 5.5 Kill-Switch & Limites

**Arrêt immédiat si:**
1. **Perte quotidienne ≥ 3%** du capital
2. **3 pertes consécutives** dans la journée
3. **Drawdown du compte ≥ 10%** depuis le peak

**Limites Mode SAFE:**
- Maximum **2 Daily Trades** par jour
- Maximum **2 Scalps** par jour
- Si 1er Daily Trade gagnant: Peut arrêter la journée
- Cooldown de 30 min après perte

**Limites Mode AGRESSIF:**
- Maximum **5 trades** par jour total
- Mêmes kill-switches que SAFE
- Pas de cooldown mais respect du max daily loss

---

## 6. MODES DE TRADING

### 6.1 Mode SAFE (Max Winrate)

**Philosophie:** "Sniper" - Très peu de trades, qualité maximale.

**Caractéristiques:**

| Critère | Valeur |
|---------|--------|
| **Setups autorisés** | A+ uniquement |
| **Daily Trades/jour** | 1-2 maximum |
| **Scalps/jour** | 0-2 maximum |
| **Sessions actives** | New York principalement |
| **Londres** | Seulement si setup ultra limpide |
| **Confluences minimum** | 4/6 pour Daily, 3/5 pour Scalp |
| **R:R minimum** | 2:1 (Daily), 1.5:1 (Scalp) |
| **Risque/trade** | 2% → 1% → 2% |
| **Arrêt après gain** | Possible si 1er trade +2R |
| **Cooldown après perte** | 30 minutes |

**Filtres supplémentaires:**
- Pas de trade en range serré (ATR Daily < moyenne)
- Pas de trade 5 min avant/après news majeures (NFP, FOMC, CPI)
- Alignement obligatoire avec biais HTF (Daily/H4)
- Pattern chandelier Tier 1 requis

**Exemple journée Mode SAFE:**
```
8h00: Analyse pré-ouverture
      → Biais: Bearish (Daily downtrend)
      → Range Asie: 450-451.50
      → Londres: Sweep du high Asie à 451.80

9h35: Setup Daily detected
      → NY Open Reversal (Playbook match)
      → Sweep confirmé à 452.10
      → BOS bearish M5 confirmé
      → FVG present
      → Bearish Engulfing M5
      → SMT: QQQ non-confirmation
      → Score: 0.92 (A+)

9h42: Entrée SHORT SPY @ 452.00
      → SL: 452.50 (+0.50)
      → TP1: 450.50 (-1.50) → R:R 3:1
      → Risque: 2% ($1,000)

11h15: TP1 hit → +$3,000 (+6%)
       → Fin de la journée (1 trade gagnant)

Bilan: 1 trade, +6%, respect total du plan
```

### 6.2 Mode AGRESSIF (Max Opportunités)

**Philosophie:** Profiter de toutes les configurations propres.

**Caractéristiques:**

| Critère | Valeur |
|---------|--------|
| **Setups autorisés** | A+, A (score ≥ 0.70) |
| **Trades/jour** | Jusqu'à 5 total |
| **Sessions actives** | Londres + New York |
| **Confluences minimum** | 3/6 pour Daily, 2/5 pour Scalp |
| **R:R minimum** | 1.5:1 |
| **Risque/trade** | 2% → 1% → 2% (ou fractionné si multi-asset) |
| **Arrêt après gain** | Non, continue tant que limites non atteintes |
| **Cooldown** | Non |

**Différences clés:**
- Peut trader durant session Londres (8h-11h ET)
- Accepte setups qualité A (0.70-0.84)
- Peut prendre SPY + QQQ simultanément (risque fractionné)
- Scalps plus fréquents dans kill zones

**Exemple journée Mode AGRESSIF:**
```
8h15: Setup Londres
      → London Sweep du range Asie
      → Score: 0.72 (A)
      → Entrée SHORT QQQ → +1.5R

9h45: Setup NY Open
      → Reversal confirmé
      → Score: 0.89 (A+)
      → Entrée SHORT SPY → +2R

10h30: Scalp
       → Micro-sweep M1
       → Score: 0.75 (A)
       → Entrée LONG QQQ → -1R (perte)

14h15: Scalp
       → Score: 0.71 (A)
       → Risque réduit à 1% (après perte)
       → Entrée SHORT SPY → +2R

Bilan: 4 trades, 3 wins / 1 loss, +4.5R net
```

### 6.3 Tableau Comparatif

| Aspect | Mode SAFE | Mode AGRESSIF |
|--------|-----------|---------------|
| **Objectif** | Max Winrate (>70%) | Max Opportunités |
| **Fréquence** | Très sélectif | Opportuniste |
| **Setups** | A+ only | A+ et A |
| **Trades/jour** | 2-4 max | 5 max |
| **Sessions** | NY only | Londres + NY |
| **Risque psychologique** | Faible (peu de trades) | Moyen (plus actif) |
| **Courbe apprentissage** | Idéal débutant | Trader confirmé |
| **Drawdowns** | Très limités | Modérés |
| **Profit potentiel/jour** | 2-6R | 4-10R |

---

## 7. JOURNALISATION & AMÉLIORATION CONTINUE

### 7.1 Structure du Journal de Trading

**Champs obligatoires par trade:**

```python
trade_journal_entry = {
    # Identification
    'trade_id': 'UUID',
    'date': '2025-01-15',
    'time_entry': '09:42:15',
    'time_exit': '11:15:30',
    'duration_minutes': 93,
    
    # Instrument
    'symbol': 'SPY',
    'direction': 'SHORT',
    
    # Contexte Marché
    'bias_htf': 'bearish',
    'session_profile': 2,  # Type TJR
    'session': 'New York',
    'market_conditions': 'Trending down, high volume',
    
    # Setup
    'playbook': 'NY_Open_Reversal',
    'setup_quality': 'A+',
    'setup_score': 0.92,
    'confluences': {
        'sweep': True,
        'bos': True,
        'fvg': True,
        'pattern': 'Bearish Engulfing',
        'smt': True,
        'htf_alignment': True
    },
    
    # Exécution
    'entry_price': 452.00,
    'stop_loss': 452.50,
    'take_profit_1': 450.50,
    'take_profit_2': 449.80,
    'position_size': 200,
    'risk_amount': 1000,
    'risk_pct': 0.02,
    
    # Résultat
    'exit_price': 450.50,
    'pnl_dollars': 3000,
    'pnl_pct': 0.06,
    'r_multiple': 3.0,
    'outcome': 'win',
    'exit_reason': 'TP1 hit',
    
    # Psychologie
    'emotions_entry': 'Confident, patient',
    'emotions_during': 'Calm, trusted the plan',
    'emotions_exit': 'Satisfied, disciplined',
    'mistakes': 'None',
    'lessons': 'Perfect execution of playbook',
    
    # Screenshots
    'screenshots': ['chart_entry.png', 'chart_exit.png'],
    
    # Notes
    'notes': 'Textbook NY Open Reversal. All confluences aligned perfectly.'
}
```

### 7.2 Métriques de Performance

**Suivi quotidien:**
```python
daily_metrics = {
    'date': '2025-01-15',
    'trades_count': 2,
    'wins': 2,
    'losses': 0,
    'winrate': 100.0,
    'total_r': 4.5,
    'avg_r_per_trade': 2.25,
    'pnl_dollars': 5500,
    'pnl_pct': 11.0,
    'largest_win': 3000,
    'largest_loss': 0,
    'trading_mode': 'SAFE',
    'setup_quality_avg': 0.90,
    'best_playbook': 'NY_Open_Reversal'
}
```

**Suivi hebdomadaire:**
```python
weekly_metrics = {
    'week': '2025-W03',
    'trades_count': 12,
    'wins': 9,
    'losses': 3,
    'winrate': 75.0,
    'total_r': 12.5,
    'avg_r_per_trade': 1.04,
    'pnl_dollars': 15000,
    'pnl_pct': 30.0,
    'profit_factor': 2.8,
    'sharpe_ratio': 1.85,
    'max_consecutive_wins': 4,
    'max_consecutive_losses': 2,
    'best_day': {'date': '2025-01-15', 'pnl': 5500},
    'worst_day': {'date': '2025-01-17', 'pnl': -1200},
    'playbooks_performance': {
        'NY_Open_Reversal': {'count': 5, 'winrate': 80.0, 'avg_r': 2.1},
        'London_Sweep': {'count': 3, 'winrate': 66.7, 'avg_r': 1.5},
        'Trend_Continuation': {'count': 4, 'winrate': 75.0, 'avg_r': 1.8}
    }
}
```

### 7.3 Analyse Post-Trade

**Process quotidien (fin de journée):**
1. **Review chaque trade:**
   - Setup était-il conforme aux critères?
   - Exécution a-t-elle été disciplinée?
   - Erreurs commises?
   - Leçons apprises?

2. **Analyse patterns:**
   - Quels setups ont le mieux fonctionné?
   - Quels playbooks sont les plus rentables?
   - Y a-t-il des patterns d'échec récurrents?

3. **Émotions:**
   - État émotionnel global de la journée?
   - Moments de FOMO/Fear/Greed?
   - Respect du plan?

**Process hebdomadaire:**
1. **Statistiques:**
   - Winrate par setup type
   - R moyen par playbook
   - Profit Factor global
   - Sharpe Ratio

2. **Ajustements:**
   - Faut-il modifier les poids de scoring?
   - Certains setups à filtrer davantage?
   - Opportunités d'amélioration des entrées/sorties?

3. **Objectifs:**
   - Définir objectifs pour semaine suivante
   - Travailler sur points faibles identifiés

### 7.4 Mode Agent - Apprentissage

**Mécanisme d'amélioration:**

```python
class AgentLearning:
    def __init__(self):
        self.setup_weights = {'ict': 0.4, 'pattern': 0.3, 'playbook': 0.3}
        self.playbook_filters = {}
        self.performance_history = []
    
    def analyze_setup_performance(self, trades_history):
        """Analyse performance par type de setup"""
        setup_stats = {}
        
        for trade in trades_history:
            setup_key = f"{trade['playbook']}_{trade['setup_quality']}"
            
            if setup_key not in setup_stats:
                setup_stats[setup_key] = {'wins': 0, 'losses': 0, 'total_r': 0}
            
            if trade['outcome'] == 'win':
                setup_stats[setup_key]['wins'] += 1
            else:
                setup_stats[setup_key]['losses'] += 1
            
            setup_stats[setup_key]['total_r'] += trade['r_multiple']
        
        return setup_stats
    
    def adjust_weights(self, performance_data):
        """Ajuste poids du scoring selon performance réelle"""
        # Si setups avec fort ICT mais faible pattern marchent mieux:
        # → Augmenter w_ict, diminuer w_pattern
        
        # Exemple simplifié
        if performance_data['ict_heavy_setups']['winrate'] > 0.75:
            self.setup_weights['ict'] += 0.05
            self.setup_weights['pattern'] -= 0.025
            self.setup_weights['playbook'] -= 0.025
        
        # Normaliser pour garder somme = 1
        total = sum(self.setup_weights.values())
        self.setup_weights = {k: v/total for k, v in self.setup_weights.items()}
    
    def refine_filters(self, losing_trades):
        """Identifie patterns communs dans trades perdants"""
        # Ex: Si beaucoup de pertes sur London Sweep le lundi
        # → Ajouter filtre "éviter London Sweep le lundi"
        
        common_patterns = self.find_common_patterns(losing_trades)
        
        for pattern in common_patterns:
            if pattern['frequency'] > 0.3:  # 30%+ des pertes
                self.playbook_filters[pattern['key']] = pattern['filter']
```

---

## 8. ROADMAP D'IMPLÉMENTATION

### Version 1.0 - MVP Dashboard + Paper Trading (Semaines 1-4)

**Objectif:** Plateforme fonctionnelle avec analyse temps réel, détection setups, paper trading.

#### Phase 1.1: Backend Core (Semaine 1)

**Tâches:**
1. **Setup projet & architecture**
   - Structure modulaire Python
   - MongoDB schemas (trades, setups, metrics)
   - FastAPI endpoints de base

2. **Module Data Feed (yfinance)**
   ```python
   # /backend/engines/data_feed.py
   - Récupération données historiques SPY/QQQ
   - Construction bougies M1/M5/M15/H1/H4/D
   - Simulation flux temps réel (replay)
   ```

3. **Module Market State**
   ```python
   # /backend/engines/market_state.py
   - Analyse HTF (Daily/H4/H1)
   - Détermination biais directionnel
   - Classification profil session
   - Marquage niveaux HTF
   ```

4. **Module Liquidity Detection**
   ```python
   # /backend/engines/liquidity.py
   - Identification niveaux liquidité
   - Détection sweeps
   - Tracking liquidité prise/non prise
   ```

**Livrables:**
- API endpoints: `/api/market-state`, `/api/liquidity-levels`
- Tests unitaires modules core
- Documentation API

#### Phase 1.2: Pattern & Setup Engines (Semaine 2)

**Tâches:**
1. **Candlestick Pattern Engine**
   ```python
   # /backend/engines/patterns/candlesticks.py
   - Implémentation Tier 1 patterns (15 patterns)
   - Détection Engulfing, Stars, Hammer/Shooting Star, etc.
   - Scoring de force des patterns
   ```

2. **ICT Pattern Engine**
   ```python
   # /backend/engines/patterns/ict.py
   - Détection BOS/CHOCH
   - Détection FVG
   - Détection SMT divergence
   ```

3. **Setup Engine**
   ```python
   # /backend/engines/setup.py
   - Scoring vectoriel
   - Classification A+/A/B/C
   - Fusion signaux ICT + Patterns + Playbooks
   ```

4. **Playbook Engine**
   ```python
   # /backend/engines/playbooks.py
   - Implémentation 4 playbooks principaux
   - Matching conditions vs market state
   - Suggestions setups Daily/Scalp
   ```

**Livrables:**
- API endpoints: `/api/patterns/detect`, `/api/setups/current`
- Dashboard JSON avec setups détectés en temps réel
- Tests avec données historiques

#### Phase 1.3: Risk & Execution Engines (Semaine 3)

**Tâches:**
1. **Risk Engine**
   ```python
   # /backend/engines/risk.py
   - Calcul position sizing
   - Schéma 2% → 1% → 2%
   - Kill-switch & limites quotidiennes
   - Gestion multi-actifs (SPY/QQQ)
   ```

2. **Paper Trading Execution**
   ```python
   # /backend/engines/execution/paper_trading.py
   - Broker simulé interne
   - Orders: Market, Limit, Stop Loss, Take Profit
   - Slippage simulé réaliste
   - Gestion positions ouvertes
   ```

3. **Trade Journal**
   ```python
   # /backend/engines/journal.py
   - Logging complet trades
   - Stockage MongoDB
   - Calcul métriques
   ```

**Livrables:**
- API endpoints: `/api/trades/execute`, `/api/trades/history`, `/api/risk/status`
- Système paper trading fonctionnel
- Journal trades persistant

#### Phase 1.4: Frontend Dashboard (Semaine 4)

**Tâches:**
1. **Layout principal**
   ```jsx
   // /frontend/src/pages/Dashboard.js
   - Header: Biais du marché, mode trading, capital
   - Sidebar: Niveaux HTF, liquidité
   - Main: Graphiques + Setups détectés
   - Footer: Statistiques journée
   ```

2. **Composants clés**
   ```jsx
   - <MarketStateWidget /> : Biais, profil session, niveaux HTF
   - <SetupsPanel /> : Liste setups détectés (A+/A/B)
   - <TradingChart /> : Prix + annotations (FVG, BOS, sweeps)
   - <ActiveTradesPanel /> : Positions ouvertes
   - <JournalPanel /> : Trades passés avec détails
   - <MetricsPanel /> : Winrate, R total, profit factor
   ```

3. **Modes de trading**
   ```jsx
   - Toggle SAFE / AGRESSIF
   - Filtres setups selon mode
   - Affichage critères respectés
   ```

4. **Interactivité**
   ```jsx
   - Bouton "Execute Trade" sur chaque setup
   - Validation manuelle avant exécution
   - Gestion SL/TP en temps réel
   ```

**Livrables:**
- Dashboard React complet
- WebSocket temps réel (setups, prix, trades)
- UX/UI intuitive et pro

#### Phase 1.5: Testing & Validation (Semaine 4-5)

**Tâches:**
1. **Backtesting**
   - Replay 6 mois de données SPY/QQQ
   - Validation détection setups
   - Mesure performance papier

2. **Tests de cohérence**
   - Setups détectés correspondent-ils aux playbooks?
   - Scoring cohérent avec confluences?
   - Risk management respecté?

3. **Optimisation**
   - Ajustement poids scoring
   - Fine-tuning seuils A+/A/B
   - Performance optimisation (latence)

**Livrables:**
- Rapport backtest 6 mois
- Métriques: Sharpe, Sortino, Max DD, Winrate, Profit Factor
- V1.0 stable et validée

---

### Version 1.5 - Mode AGRESSIF + Améliorations (Semaines 5-6)

**Tâches:**
1. **Implémentation Mode AGRESSIF**
   - Filtres élargis (setups A acceptés)
   - Trading session Londres
   - Multi-setups simultanés

2. **Session Londres**
   - Playbook London Sweep complet
   - Détection fake-outs pré-NY
   - Kill zones Londres

3. **Scalping amélioré**
   - Micro-patterns M1
   - Entries plus réactives
   - Targets intermédiaires

4. **Optimisations UI**
   - Notifications push setups A+
   - Alertes sonores
   - Mode "Auto-suggest" entries

**Livrables:**
- Mode AGRESSIF fonctionnel
- Stats comparatives SAFE vs AGRESSIF
- Dashboard enrichi

---

### Version 2.0 - Live Trading + Finnhub + IBKR (Semaines 7-10)

**Objectif:** Passage en trading réel avec données live et broker.

#### Phase 2.1: Intégration Finnhub WebSocket (Semaine 7)

**Tâches:**
1. **Connexion WebSocket**
   ```python
   # /backend/engines/data_feed_finnhub.py
   import websocket
   
   def connect_finnhub():
       ws = websocket.WebSocketApp(
           f"wss://ws.finnhub.io?token={FINNHUB_API_KEY}",
           on_message=on_message,
           on_error=on_error
       )
       ws.run_forever()
   
   def on_message(ws, message):
       # Parse tick data
       # Construire bougies M1 en temps réel
       # Feed autres modules
   ```

2. **Migration Data Feed**
   - Switch yfinance → Finnhub
   - Maintien compatibilité backtest (yfinance)
   - Gestion reconnexion automatique

**Livrables:**
- Flux temps réel SPY/QQQ fonctionnel
- Latence < 100ms
- Stabilité connexion

#### Phase 2.2: Intégration Interactive Brokers (Semaines 8-9)

**Tâches:**
1. **Connexion IBKR API**
   ```python
   # /backend/engines/execution/ibkr_adapter.py
   from ib_insync import IB, Stock, Order
   
   class IBKRExecutionEngine:
       def __init__(self):
           self.ib = IB()
           self.ib.connect('127.0.0.1', 7497, clientId=1)
       
       def place_order(self, symbol, action, quantity, order_type, limit_price=None):
           contract = Stock(symbol, 'SMART', 'USD')
           order = Order()
           order.action = action
           order.totalQuantity = quantity
           order.orderType = order_type
           if limit_price:
               order.lmtPrice = limit_price
           
           trade = self.ib.placeOrder(contract, order)
           return trade
   ```

2. **Adaptateur générique**
   - Interface commune Broker
   - Implémentations: Paper / IBKR / (futures: Alpaca, etc.)
   - Switch facile entre modes

3. **Gestion ordres avancée**
   - OCO (One-Cancels-Other) pour SL+TP
   - Bracket orders
   - Modification ordres en cours

4. **Monitoring positions**
   - Sync temps réel positions IBKR
   - Calcul P&L live
   - Alertes déviations

**Livrables:**
- Trading live IBKR fonctionnel
- Tests exhaustifs paper IBKR
- Sécurité: double-check avant envoi ordres réels

#### Phase 2.3: Tests Live & Monitoring (Semaine 10)

**Tâches:**
1. **Phase pilote**
   - Trading avec capital réduit ($5k-$10k)
   - Mode SAFE exclusivement
   - Surveillance manuelle intensive

2. **Monitoring avancé**
   - Alertes erreurs critiques
   - Logs détaillés toutes opérations
   - Dashboard monitoring serveur

3. **Fail-safes**
   - Kill-switch manuel d'urgence
   - Limites broker-side
   - Auto-shutdown si comportement anormal

**Livrables:**
- V2.0 live validated
- Documentation complète
- Procédures d'urgence

---

### Version 3.0 - Agent Learning + Extensions (Futur)

**Roadmap long terme:**

1. **Agent Learning**
   - Ajustement auto des poids scoring
   - Détection patterns gagnants/perdants
   - Optimisation dynamique filtres

2. **Extension Forex**
   - Adaptation playbooks EURUSD, GBPUSD, USDJPY
   - Gestion sessions Asia/London/NY Forex
   - Corrélations inter-marchés

3. **Features avancées**
   - ML pour prédiction qualité setups
   - Analyse sentiment market
   - Intégration calendrier économique

4. **Multi-stratégies**
   - Swing trading (H4/Daily)
   - Position trading (Weekly)
   - Options overlay

---

## ANNEXES

### A. Glossaire ICT/TJR

| Terme | Définition |
|-------|------------|
| **BOS** | Break of Structure - Cassure d'un pivot high/low |
| **CHOCH** | Change of Character - Changement de dynamique micro |
| **FVG** | Fair Value Gap - Zone d'inefficacité prix |
| **SMT** | Smart Money Technique - Divergence indices corrélés |
| **PDH/PDL** | Previous Day High/Low |
| **Sweep** | Chasse de stops, franchissement niveau + retour |
| **Order Block** | Zone où gros ordres ont été exécutés |
| **Liquidity** | Ordres en attente (stops, limits) |
| **Kill Zone** | Période haute probabilité setups |
| **Draw on Liquidity** | Attraction prix vers zone liquidité |

### B. Checklist Setup Daily (Mode SAFE)

```
□ Analyse HTF faite (biais déterminé)
□ Range Asie marqué
□ Niveau de liquidité identifié
□ Sweep confirmé (wick + close opposé)
□ BOS opposé détecté sur M5
□ FVG présent
□ Pattern chandelier valide (Tier 1)
□ SMT divergence favorable (optionnel)
□ Timing dans kill zone (9h30-11h)
□ R:R ≥ 2:1
□ Score setup ≥ 0.85 (A+)
□ Pas de news majeure dans 30 min
□ Capital disponible pour risque 2%
□ Limites quotidiennes non atteintes
□ État psychologique optimal
```

### C. Checklist Exécution Trade

```
□ Setup validé par Setup Engine
□ Position size calculée correctement
□ Entry price déterminé (limit optimal)
□ Stop Loss placé (au-delà invalidation)
□ Take Profit 1 défini (R:R min atteint)
□ Take Profit 2 défini (extension)
□ Ordre préparé (pas encore envoyé)
□ Double-check tous paramètres
□ Journal pré-trade complété
□ EXECUTION → Envoi ordre
□ Confirmation réception ordre
□ Monitoring position active
□ Breakeven stop si +0.5R
□ Exit selon plan (TP ou SL)
□ Journal post-trade complété
```

### D. Formules Clés

**Position Sizing (ETF):**
```
Position Size = (Capital × Risk%) / (Entry - Stop Loss)

Exemple:
Capital: $50,000
Risk: 2% = $1,000
Entry: $452.00
Stop Loss: $451.50
Distance: $0.50

Position = $1,000 / $0.50 = 2,000 shares
```

**Position Sizing (Futures):**
```
Position Size = (Capital × Risk%) / (Distance Points × Multiplier)

Exemple ES:
Capital: $50,000
Risk: 2% = $1,000
Entry: 4520
Stop Loss: 4515
Distance: 5 points
Multiplier: $50/point

Position = $1,000 / (5 × $50) = 4 contracts
```

**R Multiple:**
```
R = (Exit - Entry) / (Entry - Stop Loss)

Exemple:
Entry: $452.00
Exit: $450.50
Stop: $452.50

R = ($452.00 - $450.50) / ($452.50 - $452.00)
R = $1.50 / $0.50 = 3R
```

**Profit Factor:**
```
Profit Factor = Gross Profit / Gross Loss

Exemple:
Wins: $15,000
Losses: $5,000
PF = 15000 / 5000 = 3.0
```

**Sharpe Ratio:**
```
Sharpe = (Return Moyen - Risk Free Rate) / Std Dev Returns

Exemple:
Avg Daily Return: 1.2%
Risk Free: 0.01%
Std Dev: 0.8%

Sharpe = (1.2% - 0.01%) / 0.8% = 1.49
```

---

## CONCLUSION

Ce document constitue la **spécification complète** de DexterioBOT Daily & Scalping, basée strictement sur le corpus de documents fournis (architecture SPY/QQQ, bibles de chandeliers, transcripts TJR, stratégies ICT/TJR/Alex).

**Principes de développement:**
- Respect absolu des concepts documentés
- Pas d'invention hors corpus
- Approche modulaire et extensible
- Testing rigoureux avant passage live
- Amélioration continue basée sur données réelles

**Prochaines étapes:**
1. Validation de cette spécification
2. Début Phase 1.1 (Backend Core)
3. Itérations selon roadmap
4. Tests intensifs avant V2.0 live

Ce bot n'est pas une promesse de richesse rapide, mais un **outil professionnel** pour trader avec discipline, structure et consistance les stratégies éprouvées ICT/TJR/Alex sur les indices US.

---

**Statut:** Document v1.0 - Prêt pour implémentation  
**Auteur:** DexterioBOT Development Team  
**Date:** Janvier 2025
