#!/usr/bin/env python3
"""
Phase C: UI Backtest Smoke Test
Tests le flux complet backend de l'API de backtests
"""
import sys
import os
sys.path.insert(0, '/app/backend')

import time
from jobs.backtest_jobs import BacktestJobRequest, submit_job, get_job_status, list_jobs

def test_create_and_run_job():
    """Test: Créer et exécuter un job de backtest"""
    print("\n=== TEST: Create and Run Job ===")
    
    # Create request
    request = BacktestJobRequest(
        symbols=["SPY"],
        start_date="2025-08-01",
        end_date="2025-08-01",
        trading_mode="AGGRESSIVE",
        trade_types=["DAILY"],
        htf_warmup_days=40,
        commission_model="ibkr_fixed"
    )
    
    # Submit job
    print("📤 Submitting job...")
    job_id = submit_job(request)
    print(f"✓ Job created: {job_id}")
    
    # Poll status
    print("\n⏳ Polling job status...")
    max_wait = 60  # seconds
    elapsed = 0
    
    while elapsed < max_wait:
        time.sleep(2)
        elapsed += 2
        
        status = get_job_status(job_id)
        print(f"  [{elapsed}s] Status: {status.status}")
        
        if status.status == "done":
            print(f"\n✅ Job completed!")
            print(f"  - Trades: {status.metrics.get('total_trades')}")
            print(f"  - Total R Net: {status.metrics.get('total_R_net'):.3f}R")
            print(f"  - Total R Gross: {status.metrics.get('total_R_gross'):.3f}R")
            print(f"  - Costs: ${status.metrics.get('total_costs_dollars'):.2f}")
            print(f"  - Artifacts: {list(status.artifact_paths.keys())}")
            return True
        
        elif status.status == "failed":
            print(f"\n❌ Job failed: {status.error}")
            return False
    
    print(f"\n⏱️  Timeout after {max_wait}s")
    return False

def test_list_jobs():
    """Test: Lister les jobs récents"""
    print("\n=== TEST: List Jobs ===")
    
    jobs = list_jobs(limit=5)
    print(f"✓ Found {len(jobs)} recent jobs")
    
    for job in jobs[:3]:
        print(f"  - {job.job_id}: {job.status} (created: {job.created_at})")
    
    return len(jobs) > 0

def main():
    print("=" * 80)
    print("PHASE C: UI BACKTEST SMOKE TEST")
    print("=" * 80)
    
    tests = [
        ("Create and Run Job", test_create_and_run_job),
        ("List Jobs", test_list_jobs),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_fn in tests:
        try:
            result = test_fn()
            if result:
                passed += 1
                print(f"\n✅ {name}: PASSED")
            else:
                failed += 1
                print(f"\n❌ {name}: FAILED")
        except Exception as e:
            failed += 1
            print(f"\n❌ {name}: ERROR - {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 80)
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
