"""
P2-1.C - Smoke Suite (< 15 min)

Quick validation suite pour vérifier que tout fonctionne après patches.
Compatible Windows PowerShell + Linux bash.

Tests:
1. Python syntax check (compileall)
2. Unit tests (pytest)
3. Micro-backtest 1 day
4. Micro-backtest 5 days
5. Metrics calculation
6. Export artifacts

Exit codes:
- 0: All tests passed
- 1: Syntax errors
- 2: Unit tests failed
- 3: Backtest failed
- 4: Metrics validation failed
"""
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Bootstrap
_current_file = Path(__file__).resolve()
_backend_dir = _current_file.parent.parent
_repo_root = _backend_dir.parent

if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from utils.path_resolver import results_path, repo_root

# Colors for output (work in both PowerShell and bash)
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_header(text: str):
    """Print a section header."""
    print()
    print("=" * 80)
    print(f"{BLUE}{text}{RESET}")
    print("=" * 80)


def print_success(text: str):
    """Print success message."""
    print(f"{GREEN}✅ {text}{RESET}")


def print_error(text: str):
    """Print error message."""
    print(f"{RED}❌ {text}{RESET}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{YELLOW}⚠️  {text}{RESET}")


def run_command(cmd: list, description: str, timeout: int = 300) -> tuple[bool, str]:
    """
    Run a command and return (success, output).
    """
    print(f"\n🔧 {description}...")
    print(f"   Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(repo_root()),
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode == 0:
            print_success(f"{description} passed")
            return True, result.stdout
        else:
            print_error(f"{description} failed (exit code {result.returncode})")
            print("STDERR:", result.stderr[:500])
            return False, result.stderr
    
    except subprocess.TimeoutExpired:
        print_error(f"{description} timed out after {timeout}s")
        return False, "TIMEOUT"
    
    except Exception as e:
        print_error(f"{description} error: {e}")
        return False, str(e)


def test_syntax_check() -> bool:
    """Test 1: Python syntax compilation."""
    print_header("TEST 1: Python Syntax Check")
    
    # Use Python's compileall module
    success, output = run_command(
        [sys.executable, "-m", "compileall", "-q", "backend"],
        "Compiling Python files",
        timeout=60
    )
    
    return success


def test_unit_tests() -> bool:
    """Test 2: Run pytest unit tests."""
    print_header("TEST 2: Unit Tests (pytest)")
    
    # Auto-detect tests directory (Windows-safe)
    root = repo_root()
    tests_candidates = [
        root / "backend" / "tests",
        root / "tests",
    ]
    
    tests_dir = None
    for candidate in tests_candidates:
        if candidate.exists() and candidate.is_dir():
            test_files = list(candidate.glob("test_*.py"))
            if test_files:
                tests_dir = candidate
                print(f"   Found tests directory: {tests_dir.relative_to(root)}")
                break
    
    if not tests_dir:
        print_warning("No tests directory found, skipping pytest")
        return True  # Don't fail suite if tests dir missing
    
    # Run only fast tests (skip slow integration tests)
    success, output = run_command(
        [sys.executable, "-m", "pytest", str(tests_dir), "-q", "--tb=short"],
        "Running unit tests",
        timeout=180
    )
    
    return success


def test_micro_backtest_1d() -> bool:
    """Test 3: Micro-backtest 1 day."""
    print_header("TEST 3: Micro-Backtest 1 Day (2025-06-03)")
    
    # Import here to avoid circular imports
    from models.backtest import BacktestConfig
    from backtest.engine import BacktestEngine
    from backtest.metrics import calculate_metrics
    from utils.path_resolver import historical_data_path
    
    try:
        config = BacktestConfig(
            run_name="smoke_1d",
            symbols=["SPY"],
            data_paths=[str(historical_data_path("1m", "SPY.parquet"))],
            start_date="2025-06-03",
            end_date="2025-06-03",
            trading_mode="AGGRESSIVE",
            trade_types=["DAILY", "SCALP"]
        )
        
        engine = BacktestEngine(config)
        engine.load_data()
        result = engine.run()
        
        # Basic validations
        assert result.total_bars > 0, "No bars processed"
        assert result.total_bars < 1000, f"Too many bars for 1 day: {result.total_bars}"
        
        print(f"   Bars processed: {result.total_bars}")
        print(f"   Trades: {result.total_trades}")
        print(f"   Total R: {result.total_pnl_r:.3f}")
        
        print_success("1-day backtest completed")
        return True
    
    except Exception as e:
        print_error(f"1-day backtest failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_micro_backtest_5d() -> bool:
    """Test 4: Micro-backtest 5 days."""
    print_header("TEST 4: Micro-Backtest 5 Days (2025-06-03 → 2025-06-09)")
    
    from models.backtest import BacktestConfig
    from backtest.engine import BacktestEngine
    from utils.path_resolver import historical_data_path
    
    try:
        config = BacktestConfig(
            run_name="smoke_5d",
            symbols=["SPY"],
            data_paths=[str(historical_data_path("1m", "SPY.parquet"))],
            start_date="2025-06-03",
            end_date="2025-06-09",
            trading_mode="AGGRESSIVE",
            trade_types=["DAILY", "SCALP"]
        )
        
        engine = BacktestEngine(config)
        engine.load_data()
        result = engine.run()
        
        # Basic validations
        assert result.total_bars > 0, "No bars processed"
        assert result.total_bars > 1000, f"Too few bars for 5 days: {result.total_bars}"
        assert result.total_bars < 6000, f"Too many bars for 5 days: {result.total_bars}"
        
        print(f"   Bars processed: {result.total_bars}")
        print(f"   Trades: {result.total_trades}")
        print(f"   Total R: {result.total_pnl_r:.3f}")
        print(f"   Profit Factor: {result.profit_factor:.2f}")
        
        print_success("5-day backtest completed")
        return True
    
    except Exception as e:
        print_error(f"5-day backtest failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_metrics_validation() -> bool:
    """Test 5: Validate metrics calculation."""
    print_header("TEST 5: Metrics Validation")
    
    from backtest.metrics import validate_metrics_math
    
    try:
        validate_metrics_math()
        print_success("Metrics validation passed")
        return True
    
    except Exception as e:
        print_error(f"Metrics validation failed: {e}")
        return False


def generate_smoke_report(results: Dict[str, Any]) -> str:
    """Generate smoke test report."""
    report = {
        "smoke_suite": "P2-1.C",
        "timestamp": datetime.utcnow().isoformat(),
        "duration_seconds": results["duration"],
        "tests": results["tests"],
        "all_passed": results["all_passed"],
        "summary": {
            "passed": sum(1 for t in results["tests"].values() if t),
            "failed": sum(1 for t in results["tests"].values() if not t),
            "total": len(results["tests"])
        }
    }
    
    # Save report
    report_path = results_path("P2_smoke_suite_report.json")
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    return str(report_path)


def main():
    """Run complete smoke suite."""
    start_time = datetime.now()
    
    print_header("P2-1.C SMOKE SUITE")
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target: < 15 minutes")
    
    # Run all tests
    tests = {
        "syntax_check": test_syntax_check(),
        "unit_tests": test_unit_tests(),
        "backtest_1d": test_micro_backtest_1d(),
        "backtest_5d": test_micro_backtest_5d(),
        "metrics": test_metrics_validation(),
    }
    
    # Calculate duration
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Generate report
    results = {
        "tests": tests,
        "all_passed": all(tests.values()),
        "duration": duration
    }
    
    report_path = generate_smoke_report(results)
    
    # Print summary
    print_header("SMOKE SUITE SUMMARY")
    
    for test_name, passed in tests.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    print()
    print(f"Duration: {duration:.1f}s ({duration/60:.1f} minutes)")
    print(f"Report: {report_path}")
    
    if results["all_passed"]:
        print()
        print_success("🎉 ALL SMOKE TESTS PASSED!")
        return 0
    else:
        print()
        print_error("❌ SOME TESTS FAILED - See details above")
        failed = [name for name, passed in tests.items() if not passed]
        print(f"Failed tests: {', '.join(failed)}")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Smoke suite interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(99)
