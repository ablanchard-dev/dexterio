# DexterioBot - Windows Setup Guide

**Platform:** Windows 10/11 + PowerShell + VSCode  
**Python:** 3.11+  
**Last Updated:** 2025-12-27 (P2 Phase 1)

---

## Prerequisites

1. **Python 3.11+**
   ```powershell
   python --version  # Should show 3.11 or higher
   ```

2. **Git** (optional, for cloning)

3. **VSCode** (recommended)

---

## Installation

### 1. Clone or Extract Repository

```powershell
# If cloning
git clone <repo-url>
cd dexteriobot

# Or extract ZIP and navigate
cd dexteriobot-main
```

### 2. Create Virtual Environment

```powershell
# Create venv
python -m venv .venv

# Activate (PowerShell)
.\.venv\Scripts\Activate.ps1

# If you get execution policy error:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 3. Install Dependencies

```powershell
pip install -r backend\requirements.txt
```

### 4. Verify Installation

```powershell
# Test path resolver
python backend\utils\path_resolver.py

# Should output:
# ✅ Path Resolver OK
# repo_root: C:\Users\...\dexteriobot
# SPY.parquet: Found (or Not found if no data yet)
```

---

## Data Setup

Place your historical data in `data/historical/1m/`:

```
data/
  historical/
    1m/
      SPY.parquet
      QQQ.parquet
```

**Data format:** Parquet files with columns: `datetime`, `open`, `high`, `low`, `close`, `volume`

---

## Running Backtests

### Quick Smoke Test (63 seconds)

```powershell
python backend\tools\smoke_suite.py
```

Expected output:
```
✅ PASS: syntax_check
✅ PASS: unit_tests
✅ PASS: backtest_1d
✅ PASS: backtest_5d
✅ PASS: metrics
Duration: ~63s
```

### Micro-Backtest (1 Day)

```powershell
# Programmatic example
python -c "
from models.backtest import BacktestConfig
from backtest.engine import BacktestEngine

config = BacktestConfig(
    symbols=['SPY'],
    data_paths=['data/historical/1m/SPY.parquet'],
    start_date='2025-06-03',
    end_date='2025-06-03',
    trading_mode='AGGRESSIVE'
)

engine = BacktestEngine(config)
result = engine.run()
print(f'Trades: {result.total_trades}, R: {result.total_pnl_r:.3f}')
"
```

### Full Month Backtest

```powershell
python backend\backtest\run_rolling_30d.py --month 2025-06
```

---

## Running Tests

### Unit Tests (pytest)

```powershell
pytest backend\tests -v
```

### Date Slicing Test

```powershell
python backend\tests\test_date_slicing.py
```

Expected:
```
✅ ALL DATE SLICING TESTS PASSED
  Full dataset:  105,822 bars
  1-day slice:   836 bars
  5-day slice:   4,148 bars
  Speedup: 126x for 1-day
```

---

## Environment Variables

No environment variables required! The `path_resolver` module auto-detects:
- Docker: `/app`
- Windows: Auto-detects repo root from current directory

All paths are resolved automatically.

---

## Results & Artifacts

After running backtests, results are saved in:

```
backend/
  results/
    baseline_reference.json         # Baseline metrics
    P2_smoke_suite_report.json      # Smoke test results
    date_slicing_proof.json         # Date slicing proof
    hardcoded_paths_audit.json      # Paths audit

data/
  backtest_results/
    equity_*.parquet                # Equity curves
    trades_*.parquet                # Trade logs
    summary_*.json                  # Run summaries
```

---

## Troubleshooting

### Issue: "Module not found"

**Solution:** Make sure you activated the venv:
```powershell
.\.venv\Scripts\Activate.ps1
```

### Issue: "File not found" errors

**Solution:** The `path_resolver` should handle this automatically. Verify:
```powershell
python backend\utils\path_resolver.py
```

### Issue: Backtest very slow

**Solution:** Use date slicing for faster micro-tests:
```python
config = BacktestConfig(
    start_date="2025-06-03",
    end_date="2025-06-03",  # 1 day = 126x faster
    ...
)
```

### Issue: PowerShell execution policy

**Solution:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## VSCode Integration

### Recommended Extensions

- Python (Microsoft)
- Pylance
- Jupyter (for notebooks if needed)

### Launch Configuration (.vscode/launch.json)

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Smoke Suite",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/backend/tools/smoke_suite.py",
      "console": "integratedTerminal"
    },
    {
      "name": "Python: Date Slicing Test",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/backend/tests/test_date_slicing.py",
      "console": "integratedTerminal"
    }
  ]
}
```

---

## Quick Commands Reference

```powershell
# Activate venv
.\.venv\Scripts\Activate.ps1

# Smoke tests
python backend\tools\smoke_suite.py

# Path audit
python backend\tools\audit_hardcoded_paths.py

# Unit tests
pytest backend\tests

# Backtest 1 day
# (see "Running Backtests" section above)
```

---

## Performance Expectations

| Test | Duration | Bars Processed |
|------|----------|----------------|
| Smoke suite | ~63s | 836 + 4,148 |
| 1-day backtest | ~10s | 836 |
| 5-day backtest | ~40s | 4,148 |
| Full month | ~5-10min | 105,822 |

---

## Next Steps

1. ✅ Verify installation with smoke suite
2. ✅ Run date slicing tests
3. ✅ Generate baseline metrics
4. 🔄 Start developing/testing locally

---

**Questions?** Check:
- `backend/results/P2_PHASE1_COMPLETE.md` - Full Phase 1 documentation
- `DEXTERIOBOT_SPECIFICATION.md` - System architecture & trading rules

---

_Last updated: 2025-12-27 (P2 Phase 1 Complete)_
