# 🗺️ ROADMAP COMPLÈTE — DEXTERIOBOT (ZIP8 → PRODUCTION)

**Objectif final** : Bot IBKR Live avec UI cockpit + VPS sécurisé + backtest réaliste

---

## 📊 VUE D'ENSEMBLE

```
PHASE A (Windows Fix)        ━━━━━━━━━━ 95% ✅ BLOQUANT
PHASE B (Net-of-costs)       ━━━━━━━━░░ 0%  🔴 BLOQUANT  
PHASE C (UI Backtest)        ━━━━░░░░░░ 0%  🟡 PARALLÈLE
PHASE D (IBKR Paper)         ━░░░░░░░░░ 0%  🟡 APRÈS B
PHASE E (VPS Deployment)     ░░░░░░░░░░ 0%  🟡 FINAL
```

**Durée totale estimée** : 20-30h de dev + tests

---

## 🎯 PHASE A — FIX WINDOWS + SMOKE SUITE ✅

### Status : 95% TERMINÉ

### Fichiers modifiés

| Fichier | Status | Changement |
|---------|--------|------------|
| `backend/tools/debug_paths_windows.py` | ✅ Créé | Diagnostic complet paths |
| `backend/utils/path_resolver.py` | ✅ Patché | Détection Docker forte (`/.dockerenv`) |
| `backend/tools/smoke_suite.py` | ✅ Patché | Auto-detect `tests/` directory |

### Validation Windows

```powershell
cd C:\bots\dexterio1-main\backend
python tools\debug_paths_windows.py   # Expected: repo_root = C:\bots\...
python tools\smoke_suite.py            # Expected: ALL TESTS PASSED
```

### Artefacts attendus

- `backend/results/windows_path_debug.json`
- `backend/results/P2_smoke_suite_report.json`

### Critères de succès

- ✅ `repo_root()` pointe vers repo local Windows
- ✅ Smoke suite passe (syntax + backtest 1d/5d)
- ✅ Données `data/historical/1m/SPY.parquet` trouvées

---

## 🎯 PHASE B — BACKTEST NET-OF-COSTS 🔴

### Objectif

Backtest **réaliste** avec commissions IBKR + fees + slippage + spread.

### Durée estimée : 2-3h

---

### B.1 — Modèle de coûts (CORE)

#### B.1.1 Créer `backend/backtest/costs.py`

**Fonctions pures** :
- `calculate_ibkr_commission(shares, price, model)` → IBKR fixed/tiered
- `calculate_regulatory_fees(shares, price, side)` → SEC + FINRA (sell only)
- `calculate_slippage(shares, price, model)` → pct ou ticks
- `calculate_spread_cost(shares, price, model)` → bid-ask implicit
- `calculate_total_execution_costs()` → entry + exit costs

**Modèles supportés** :
- Commission : `"ibkr_fixed"`, `"ibkr_tiered"`, `"none"`
- Slippage : `"pct"`, `"ticks"`, `"none"`
- Spread : `"fixed_bps"`, `"none"`

---

#### B.1.2 Étendre `BacktestConfig`

**Ajout dans `backend/models/backtest.py`** :

```python
class BacktestConfig(BaseModel):
    # ... existing fields ...
    
    # PHASE B: Execution costs model
    commission_model: str = "ibkr_fixed"  # ibkr_fixed, ibkr_tiered, none
    enable_reg_fees: bool = True
    slippage_model: str = "pct"           # pct, ticks, none
    slippage_pct: float = 0.0005          # 0.05% default
    slippage_ticks: int = 1
    spread_model: str = "fixed_bps"       # fixed_bps, none
    spread_bps: float = 2.0               # 2 bps = 0.02%
```

---

#### B.1.3 Étendre `TradeResult`

**Ajout colonnes costs** :

```python
class TradeResult(BaseModel):
    # ... existing fields ...
    
    # PHASE B: Cost breakdown
    entry_commission: float = 0.0
    entry_reg_fees: float = 0.0
    entry_slippage: float = 0.0
    entry_spread_cost: float = 0.0
    entry_total_cost: float = 0.0
    
    exit_commission: float = 0.0
    exit_reg_fees: float = 0.0
    exit_slippage: float = 0.0
    exit_spread_cost: float = 0.0
    exit_total_cost: float = 0.0
    
    total_costs: float = 0.0
    
    # PnL (gross vs net)
    pnl_gross_dollars: float = 0.0
    pnl_net_dollars: float = 0.0
    pnl_gross_R: float = 0.0
    pnl_net_R: float = 0.0
```

---

### B.2 — Intégration dans `engine.py`

**Modifier `backend/backtest/engine.py`** :

1. Import `costs.py`
2. Dans `_execute_trade()` :
   - Calculer costs entry/exit via `calculate_total_execution_costs()`
   - Stocker gross PnL (actuel)
   - Calculer net PnL = gross - total_costs
   - Populer tous les champs costs du `TradeResult`

3. Dans `_export_results()` :
   - Export Parquet avec toutes colonnes costs
   - Summary JSON avec métriques gross + net séparées

---

### B.3 — Metrics net vs gross

**Modifier `backend/backtest/metrics.py`** :

```python
def calculate_metrics(trades_df: pd.DataFrame, mode: str = "net") -> dict:
    """
    Calculate metrics on net (default) or gross PnL
    
    Args:
        mode: "net" (with costs) or "gross" (without costs)
    """
    if mode == "net":
        pnl_col = "pnl_net_R"
    else:
        pnl_col = "pnl_gross_R"
    
    # ... existing logic using pnl_col ...
```

**Export** :
- `total_R_gross`
- `total_R_net`
- `profit_factor_gross`
- `profit_factor_net`
- `expectancy_gross`
- `expectancy_net`

---

### B.4 — Validation (runs 1d/5d max)

#### Test 1 : 1 jour (2025-08-01)

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

print(f'Total R Gross: {result.total_pnl_r_gross:.2f}R')
print(f'Total R Net:   {result.total_pnl_r_net:.2f}R')
"
```

#### Test 2 : 5 jours

```powershell
# Même config, start='2025-08-01', end='2025-08-07'
```

#### Artefacts attendus

- `trades_costs_test_1d_AGGRESSIVE_DAILY.parquet` avec colonnes costs
- `summary_costs_test_1d_AGGRESSIVE_DAILY.json` avec gross + net
- `costs_sanity_proof.json` :

```json
{
  "run": "costs_test_1d",
  "trades": 4,
  "total_R_gross": 2.5,
  "total_R_net": 2.1,
  "net_less_than_gross": true,
  "avg_cost_per_trade_dollars": 12.5,
  "avg_cost_pct_of_trade_value": 0.08
}
```

---

## 🎯 PHASE C — UI BACKTEST (COCKPIT) 🟡

### Objectif

Lancer backtests depuis UI au lieu de 1000 commandes terminal.

### Durée estimée : 4-6h

---

### C.1 — Backend API (Jobs)

#### C.1.1 Modèles jobs

**Créer `backend/models/jobs.py`** :

```python
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime

class BacktestJobRequest(BaseModel):
    """Request pour lancer un backtest"""
    symbols: list[str]
    start_date: str  # YYYY-MM-DD
    end_date: str
    trading_mode: Literal["SAFE", "AGGRESSIVE"]
    trade_types: list[str]
    htf_warmup_days: int = 40
    
    # Costs config
    commission_model: str = "ibkr_fixed"
    slippage_model: str = "pct"
    spread_model: str = "fixed_bps"

class BacktestJobStatus(BaseModel):
    """Status d'un job backtest"""
    job_id: str
    status: Literal["pending", "running", "completed", "failed"]
    progress: float  # 0.0 - 1.0
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error: Optional[str]
```

---

#### C.1.2 Job Queue (simple)

**Créer `backend/jobs/backtest_runner.py`** :

```python
import asyncio
from concurrent.futures import ProcessPoolExecutor
from typing import Dict
import uuid

class BacktestJobRunner:
    def __init__(self):
        self.jobs: Dict[str, BacktestJobStatus] = {}
        self.executor = ProcessPoolExecutor(max_workers=2)
    
    def submit_job(self, request: BacktestJobRequest) -> str:
        job_id = str(uuid.uuid4())
        # ... store job, submit to executor ...
        return job_id
    
    def get_status(self, job_id: str) -> BacktestJobStatus:
        return self.jobs.get(job_id)
    
    def get_results(self, job_id: str) -> dict:
        # Return paths + summary
        pass
```

---

#### C.1.3 Endpoints FastAPI

**Ajouter dans `backend/routes/backtests.py`** (NOUVEAU) :

```python
from fastapi import APIRouter, HTTPException
from models.jobs import BacktestJobRequest, BacktestJobStatus
from jobs.backtest_runner import BacktestJobRunner

router = APIRouter(prefix="/api/backtests", tags=["backtests"])
runner = BacktestJobRunner()

@router.post("/run")
async def run_backtest(request: BacktestJobRequest):
    """Lance un backtest en arrière-plan"""
    # Validation: max 1 mois
    # ...
    job_id = runner.submit_job(request)
    return {"job_id": job_id}

@router.get("/{job_id}")
async def get_job_status(job_id: str):
    """Status d'un job"""
    status = runner.get_status(job_id)
    if not status:
        raise HTTPException(404, "Job not found")
    return status

@router.get("/{job_id}/results")
async def get_job_results(job_id: str):
    """Résultats complets"""
    results = runner.get_results(job_id)
    if not results:
        raise HTTPException(404, "Results not found")
    return results
```

**Enregistrer router dans `server_extended.py`** :

```python
from routes import backtests
app.include_router(backtests.router)
```

---

### C.2 — Frontend (Page Backtests)

#### C.2.1 Créer `frontend/src/pages/Backtests.jsx`

**Composants** :
- `BacktestForm` : formulaire params
- `JobsList` : liste jobs (pending/running/completed)
- `ResultsViewer` : affichage metrics + trades table

**Features** :
- Progress bar (polling status)
- Table trades (Parquet → JSON endpoint)
- Equity curve (Chart.js ou Recharts)

---

#### C.2.2 Endpoints pour données visualisation

**Ajouter dans `backend/routes/backtests.py`** :

```python
@router.get("/{job_id}/trades")
async def get_trades(job_id: str, limit: int = 100):
    """Return trades as JSON for table display"""
    # Load parquet, convert to JSON
    pass

@router.get("/{job_id}/equity")
async def get_equity_curve(job_id: str):
    """Return equity curve data points"""
    pass
```

---

### C.3 — Validation

**Test curl** :

```powershell
# 1. Lancer job
curl -X POST http://localhost:8001/api/backtests/run `
  -H "Content-Type: application/json" `
  -d '{
    "symbols": ["SPY"],
    "start_date": "2025-08-01",
    "end_date": "2025-08-01",
    "trading_mode": "AGGRESSIVE",
    "trade_types": ["DAILY"],
    "htf_warmup_days": 40
  }'

# Response: {"job_id": "abc-123"}

# 2. Check status
curl http://localhost:8001/api/backtests/abc-123

# 3. Get results
curl http://localhost:8001/api/backtests/abc-123/results
```

---

## 🎯 PHASE D — IBKR PAPER 🟡

### Objectif

Exécution réelle via IBKR Paper (TWS/Gateway).

### Durée estimée : 6-8h

---

### D.1 — Interface BrokerAdapter

**Créer `backend/brokers/adapter.py`** :

```python
from abc import ABC, abstractmethod
from typing import Optional
from models.orders import Order, Fill, Position

class BrokerAdapter(ABC):
    """Interface abstraite pour brokers"""
    
    @abstractmethod
    async def connect(self) -> bool:
        pass
    
    @abstractmethod
    async def disconnect(self):
        pass
    
    @abstractmethod
    async def submit_order(self, order: Order) -> str:
        """Returns order_id"""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        pass
    
    @abstractmethod
    async def get_positions(self) -> list[Position]:
        pass
    
    @abstractmethod
    async def get_fills(self) -> list[Fill]:
        pass
```

---

### D.2 — IBKR Adapter (ib_insync)

**Créer `backend/brokers/ibkr_adapter.py`** :

```python
from ib_insync import IB, Stock, MarketOrder, LimitOrder
from brokers.adapter import BrokerAdapter

class IBKRAdapter(BrokerAdapter):
    def __init__(self, mode: str = "paper"):
        self.ib = IB()
        self.mode = mode
        self.port = 7497 if mode == "paper" else 7496
    
    async def connect(self) -> bool:
        self.ib.connect('127.0.0.1', self.port, clientId=1)
        return self.ib.isConnected()
    
    async def submit_order(self, order: Order) -> str:
        # Convert Order model to IB order
        contract = Stock(order.symbol, 'SMART', 'USD')
        ib_order = MarketOrder(order.action, order.quantity)
        trade = self.ib.placeOrder(contract, ib_order)
        return trade.order.orderId
    
    # ... other methods ...
```

**Dependencies** :

```txt
ib_insync==0.9.86
```

---

### D.3 — Paper Trading Mode

**Modifier `backend/backtest/engine.py`** :

```python
class BacktestEngine:
    def __init__(self, config: BacktestConfig, broker: Optional[BrokerAdapter] = None):
        self.config = config
        self.broker = broker  # If set, use live execution
        self.execution_mode = "paper" if broker else "backtest"
```

**Dans `_execute_trade()`** :

```python
if self.broker:
    # Paper/Live execution
    order_id = await self.broker.submit_order(order)
    # Wait for fill, log commission from broker
else:
    # Backtest simulation
    # ... existing logic ...
```

---

### D.4 — Paper Trades Export

**Format identique** : `paper_trades_YYYYMMDD.parquet`

Colonnes :
- Toutes celles du backtest
- + `broker_order_id`
- + `broker_fill_time`
- + `broker_commission` (réel)

---

### D.5 — Sécurité

**Créer `.env.paper`** (NON commité) :

```env
IBKR_MODE=paper
IBKR_HOST=127.0.0.1
IBKR_PORT=7497
IBKR_CLIENT_ID=1
```

**Doc** : `docs/IBKR_PAPER_SETUP.md`

- Installation TWS
- Configuration paper account
- Firewall : ne PAS exposer port 7497/7496 au public
- Monitoring : vérifier connexion avant chaque trade

---

## 🎯 PHASE E — VPS DEPLOYMENT + SÉCURITÉ 🟡

### Objectif

Déploiement production sur VPS sécurisé.

### Durée estimée : 4-6h

---

### E.1 — Docker Compose

**Créer `docker-compose.prod.yml`** :

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    env_file: .env.production
    ports:
      - "8001:8001"
    volumes:
      - ./data:/app/data
      - ./backend/results:/app/backend/results
    restart: unless-stopped
  
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
    restart: unless-stopped
  
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - frontend
      - backend
    restart: unless-stopped
  
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    restart: unless-stopped
```

---

### E.2 — Nginx + TLS

**`nginx/nginx.conf`** :

```nginx
server {
    listen 80;
    server_name dexteriobot.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name dexteriobot.yourdomain.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    # Frontend
    location / {
        proxy_pass http://frontend:3000;
    }
    
    # API
    location /api {
        proxy_pass http://backend:8001;
    }
}
```

**Cert** : Let's Encrypt via Certbot

---

### E.3 — Secrets Management

**`.env.production`** (NON commité) :

```env
# Database
MONGO_URL=mongodb://...
DB_NAME=dexteriobot

# IBKR
IBKR_MODE=live
IBKR_HOST=127.0.0.1
IBKR_PORT=7496

# Auth
JWT_SECRET=...
ADMIN_PASSWORD=...

# Alerts
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

**Backup** : Utiliser AWS Secrets Manager ou HashiCorp Vault (futur)

---

### E.4 — Hardening Serveur

**`scripts/hardening.sh`** :

```bash
#!/bin/bash
# VPS Hardening Script

# 1. Firewall (ufw)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH (clé uniquement)
sudo ufw allow 80/tcp    # HTTP (redirect)
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# 2. SSH par clé uniquement
sudo sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart sshd

# 3. Fail2ban
sudo apt install fail2ban -y
sudo systemctl enable fail2ban

# 4. Auto-updates
sudo apt install unattended-upgrades -y

# 5. Monitoring (optional: Prometheus + Grafana)
# ...
```

---

### E.5 — UI Authentication

**Ajouter dans `backend/routes/auth.py`** :

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # JWT validation
    # Role check (admin/read-only)
    pass

@router.get("/protected")
async def protected_route(user = Depends(verify_token)):
    return {"user": user}
```

**Frontend** : Login page + token storage

---

### E.6 — Deployment Guide

**Créer `docs/VPS_DEPLOYMENT.md`** :

1. Setup VPS (Ubuntu 22.04 LTS)
2. Install Docker + Docker Compose
3. Clone repo
4. Config `.env.production`
5. SSL cert (Certbot)
6. Hardening script
7. Deploy : `docker-compose -f docker-compose.prod.yml up -d`
8. Monitoring : logs + health checks

---

## 📊 RÉCAPITULATIF LIVRABLES

### PHASE A ✅
- [x] `backend/tools/debug_paths_windows.py`
- [x] `backend/utils/path_resolver.py` (patched)
- [x] `backend/tools/smoke_suite.py` (patched)

### PHASE B 🔴
- [ ] `backend/backtest/costs.py`
- [ ] `backend/models/backtest.py` (extended)
- [ ] `backend/backtest/engine.py` (costs integration)
- [ ] `backend/backtest/metrics.py` (gross vs net)
- [ ] Artefacts : trades with costs, summary gross+net

### PHASE C 🟡
- [ ] `backend/models/jobs.py`
- [ ] `backend/jobs/backtest_runner.py`
- [ ] `backend/routes/backtests.py`
- [ ] `frontend/src/pages/Backtests.jsx`

### PHASE D 🟡
- [ ] `backend/brokers/adapter.py`
- [ ] `backend/brokers/ibkr_adapter.py`
- [ ] `docs/IBKR_PAPER_SETUP.md`

### PHASE E 🟡
- [ ] `docker-compose.prod.yml`
- [ ] `nginx/nginx.conf`
- [ ] `scripts/hardening.sh`
- [ ] `docs/VPS_DEPLOYMENT.md`

---

## 🚦 RÈGLES D'AVANCEMENT

1. ❌ **PHASE B ne démarre PAS avant validation PHASE A**
2. ❌ **PHASE D ne démarre PAS avant validation PHASE B**
3. ✅ **PHASE C peut être parallèle à B/D** (pas de dépendance technique)
4. ✅ Chaque phase → diff + artefacts + tests
5. ✅ Smoke suite obligatoire avant chaque merge

---

**🎯 PROCHAINE ACTION : Valider PHASE A puis implémenter PHASE B**
