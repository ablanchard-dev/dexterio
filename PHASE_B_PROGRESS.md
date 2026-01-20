# 📊 PHASE B — BACKTEST NET-OF-COSTS (EN COURS)

## Status : 60% complété

---

## ✅ Fichiers créés/modifiés

### 1. Modèle de coûts (DONE ✅)

**Fichier** : `backend/backtest/costs.py`  
**Status** : ✅ Créé et testé

**Fonctions** :
- `calculate_ibkr_commission()` — IBKR fixed/tiered models
- `calculate_regulatory_fees()` — SEC + FINRA (sell only)
- `calculate_slippage()` — pct ou ticks
- `calculate_spread_cost()` — bid-ask implicit cost
- `calculate_total_execution_costs()` — entry + exit costs complets

**Test** :
```bash
cd /app/backend
python backtest/costs.py
```

---

### 2. Modèles étendus (DONE ✅)

**Fichier** : `backend/models/backtest.py`  
**Status** : ✅ Modifié

**Changements** :

#### BacktestConfig (nouveaux champs)
```python
commission_model: str = "ibkr_fixed"
enable_reg_fees: bool = True
slippage_model: str = "pct"
slippage_cost_pct: float = 0.0005
slippage_ticks: int = 1
spread_model: str = "fixed_bps"
spread_bps: float = 2.0
```

#### TradeResult (nouveaux champs)
```python
# Cost breakdown
entry_commission: float
entry_reg_fees: float
entry_slippage: float
entry_spread_cost: float
entry_total_cost: float

exit_commission: float
exit_reg_fees: float
exit_slippage: float
exit_spread_cost: float
exit_total_cost: float

total_costs: float

# PnL gross vs net
pnl_gross_dollars: float
pnl_net_dollars: float
pnl_gross_R: float
pnl_net_R: float
```

#### BacktestResult (nouveaux champs)
```python
total_pnl_gross_dollars: float
total_pnl_net_dollars: float
total_pnl_gross_R: float
total_pnl_net_R: float
total_costs_dollars: float
```

---

## 🔄 Fichiers à modifier (EN ATTENTE)

### 3. Intégration dans engine.py (TODO 🔴)

**Fichier** : `backend/backtest/engine.py`  
**Status** : ⏳ En attente

**Changements requis** :

#### A. Import costs module

```python
from backtest.costs import calculate_total_execution_costs
```

#### B. Modifier `_execute_trade()` (ligne ~800-900)

**Localiser** :
```python
def _execute_trade(self, setup, timestamp, candle):
    # ... existing logic ...
    
    # Calculate PnL
    pnl_dollars = ...
    pnl_r = pnl_dollars / risk_amount
```

**Ajouter APRÈS le calcul du PnL** :

```python
    # PHASE B: Calculate execution costs
    entry_costs, exit_costs = calculate_total_execution_costs(
        shares=position_size,
        entry_price=entry_price,
        exit_price=exit_price,
        commission_model=self.config.commission_model,
        enable_reg_fees=self.config.enable_reg_fees,
        slippage_model=self.config.slippage_model,
        slippage_pct=self.config.slippage_cost_pct,
        slippage_ticks=self.config.slippage_ticks,
        spread_model=self.config.spread_model,
        spread_bps=self.config.spread_bps
    )
    
    total_costs = entry_costs.total + exit_costs.total
    
    # Calculate gross and net PnL
    pnl_gross_dollars = pnl_dollars  # Original calculation
    pnl_net_dollars = pnl_gross_dollars - total_costs
    pnl_gross_R = pnl_gross_dollars / risk_amount
    pnl_net_R = pnl_net_dollars / risk_amount
```

#### C. Modifier création TradeResult

**Ajouter champs** :

```python
    trade_result = TradeResult(
        # ... existing fields ...
        
        # PHASE B: Cost breakdown
        entry_commission=entry_costs.commission,
        entry_reg_fees=entry_costs.regulatory_fees,
        entry_slippage=entry_costs.slippage,
        entry_spread_cost=entry_costs.spread_cost,
        entry_total_cost=entry_costs.total,
        
        exit_commission=exit_costs.commission,
        exit_reg_fees=exit_costs.regulatory_fees,
        exit_slippage=exit_costs.slippage,
        exit_spread_cost=exit_costs.spread_cost,
        exit_total_cost=exit_costs.total,
        
        total_costs=total_costs,
        
        # PnL gross vs net
        pnl_gross_dollars=pnl_gross_dollars,
        pnl_net_dollars=pnl_net_dollars,
        pnl_gross_R=pnl_gross_R,
        pnl_net_R=pnl_net_R,
        
        # Legacy (backward compat)
        pnl_dollars=pnl_net_dollars,  # Use net as default
        pnl_r=pnl_net_R
    )
```

---

### 4. Metrics gross vs net (TODO 🔴)

**Fichier** : `backend/backtest/metrics.py`  
**Status** : ⏳ En attente

**Changements requis** :

#### A. Étendre `calculate_metrics()`

```python
def calculate_metrics(
    trades: List[dict],
    initial_capital: float,
    mode: str = "net"  # "net" or "gross"
) -> dict:
    """
    Calculate backtest metrics
    
    Args:
        trades: List of trade dictionaries
        initial_capital: Starting capital
        mode: "net" (with costs) or "gross" (without costs)
    """
    if mode == "net":
        pnl_col = "pnl_net_R"
        pnl_dollars_col = "pnl_net_dollars"
    else:
        pnl_col = "pnl_gross_R"
        pnl_dollars_col = "pnl_gross_dollars"
    
    # ... rest of logic using pnl_col ...
```

#### B. Exporter métriques séparées

```python
    return {
        # Net metrics (default)
        "total_R_net": ...,
        "profit_factor_net": ...,
        "expectancy_net": ...,
        "max_drawdown_net": ...,
        
        # Gross metrics (comparison)
        "total_R_gross": ...,
        "profit_factor_gross": ...,
        "expectancy_gross": ...,
        
        # Costs summary
        "total_costs_dollars": ...,
        "avg_cost_per_trade": ...,
        "cost_pct_of_volume": ...
    }
```

---

## 📊 VALIDATION (après modifications)

### Test 1 : 1 jour (SPY)

```powershell
cd C:\bots\dexterio1-main\backend

python -c "
from models.backtest import BacktestConfig
from backtest.engine import BacktestEngine
from utils.path_resolver import historical_data_path

config = BacktestConfig(
    run_name='costs_test_1d',
    symbols=['SPY'],
    data_paths=[str(historical_data_path('1m', 'SPY.parquet'))],
    start_date='2025-08-01',
    end_date='2025-08-01',
    trading_mode='AGGRESSIVE',
    trade_types=['DAILY'],
    htf_warmup_days=40,
    commission_model='ibkr_fixed',
    enable_reg_fees=True,
    slippage_model='pct',
    spread_model='fixed_bps'
)

engine = BacktestEngine(config)
result = engine.run()

print(f'\n📊 RÉSULTATS:')
print(f'  Total R Gross: {result.total_pnl_gross_R:.2f}R')
print(f'  Total R Net:   {result.total_pnl_net_R:.2f}R')
print(f'  Total Costs:   \${result.total_costs_dollars:.2f}')
print(f'  Cost Impact:   {(result.total_pnl_gross_R - result.total_pnl_net_R):.2f}R')
"
```

**Expected output** :
```
📊 RÉSULTATS:
  Total R Gross: 2.50R
  Total R Net:   2.15R
  Total Costs:   $85.50
  Cost Impact:   0.35R
```

---

### Test 2 : 5 jours

```powershell
# Même config, end_date='2025-08-07'
```

---

### Artefacts attendus

**Fichiers générés** :

1. `backend/results/trades_costs_test_1d_AGGRESSIVE_DAILY.parquet`
   - Toutes colonnes costs présentes
   - `pnl_gross_dollars`, `pnl_net_dollars`, `total_costs`

2. `backend/results/summary_costs_test_1d_AGGRESSIVE_DAILY.json`
   ```json
   {
     "total_R_gross": 2.50,
     "total_R_net": 2.15,
     "total_costs_dollars": 85.50,
     "avg_cost_per_trade": 21.38
   }
   ```

3. `backend/results/costs_sanity_proof.json`
   ```json
   {
     "run": "costs_test_1d",
     "trades": 4,
     "sanity_checks": {
       "net_less_than_gross": true,
       "costs_positive": true,
       "pnl_diff_equals_costs": true
     }
   }
   ```

---

## 🚦 PROCHAINES ÉTAPES

### Étape 3 : Modifier engine.py

**Fichier** : `backend/backtest/engine.py`  
**Action** : Intégrer calcul costs dans `_execute_trade()`

### Étape 4 : Modifier metrics.py

**Fichier** : `backend/backtest/metrics.py`  
**Action** : Supporter mode="net" vs mode="gross"

### Étape 5 : Tests de validation

**Action** : Lancer tests 1d/5d avec artefacts

### Étape 6 : Documentation

**Action** : Créer `docs/COSTS_MODEL.md` avec exemples

---

## 📝 NOTES

- ✅ Backward compat préservée : `pnl_dollars` et `pnl_r` pointent vers net
- ✅ Gross metrics disponibles pour comparaison
- ⚠️ Engine.py et metrics.py nécessitent modifications manuelles
- ⚠️ Tests requis avant passage PHASE C

---

**Status global PHASE B : 60% ✅**

**Bloqueurs** : Modifications engine.py + metrics.py + validation tests
