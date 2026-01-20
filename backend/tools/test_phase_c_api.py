#!/usr/bin/env python3
"""
PHASE C - E2E API Test Script
Tests the complete backtest API flow end-to-end.

Usage:
    python backend/tools/test_phase_c_api.py [--base-url http://localhost:8001]
"""
import sys
import os
import time
import json
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Default configuration
DEFAULT_BASE_URL = "http://localhost:8001"
API_BASE = "/api/backtests"
TIMEOUT_SECONDS = 60


def get_api_key() -> Optional[str]:
    """Get API key from environment if set"""
    return os.getenv("DEXTERIO_API_KEY")


def get_headers() -> dict:
    """Get request headers with API key if available"""
    api_key = get_api_key()
    headers = {}
    if api_key:
        headers["X-API-KEY"] = api_key
    return headers


def main():
    """Run E2E test"""
    # Parse args
    base_url = DEFAULT_BASE_URL
    if len(sys.argv) > 1:
        if sys.argv[1] == "--base-url" and len(sys.argv) > 2:
            base_url = sys.argv[2]
        elif sys.argv[1] in ["-h", "--help"]:
            print(__doc__)
            sys.exit(0)
    
    print("=" * 80)
    print("PHASE C - E2E API TEST")
    print("=" * 80)
    print(f"Base URL: {base_url}")
    print(f"API Key: {'Set' if get_api_key() else 'Not set (dev mode)'}")
    print("=" * 80)
    
    try:
        # (A) Launch job: POST /api/backtests/run
        print("\n[A] Launching backtest job...")
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        request_data = {
            "symbols": ["SPY"],
            "start_date": yesterday.strftime("%Y-%m-%d"),
            "end_date": yesterday.strftime("%Y-%m-%d"),
            "trading_mode": "SAFE",
            "trade_types": ["DAILY"],
            "htf_warmup_days": 40
        }
        
        print(f"  Request: {json.dumps(request_data, indent=2)}")
        
        response = requests.post(
            f"{base_url}{API_BASE}/run",
            json=request_data,
            headers=get_headers(),
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"  ❌ Failed to create job: {response.status_code}")
            print(f"  Response: {response.text}")
            print("\n❌ TEST FAIL")
            sys.exit(1)
        
        job_data = response.json()
        job_id = job_data.get("job_id")
        
        if not job_id:
            print(f"  ❌ No job_id in response: {job_data}")
            print("\n❌ TEST FAIL")
            sys.exit(1)
        
        print(f"  ✅ Job created: {job_id}")
        
        # (B) Poll status: GET /api/backtests/{job_id} until "done" (timeout 60s)
        print(f"\n[B] Polling job status (timeout: {TIMEOUT_SECONDS}s)...")
        start_time = time.time()
        status = None
        
        while time.time() - start_time < TIMEOUT_SECONDS:
            elapsed = int(time.time() - start_time)
            
            try:
                response = requests.get(
                    f"{base_url}{API_BASE}/{job_id}",
                    headers=get_headers(),
                    timeout=5
                )
                
                if response.status_code != 200:
                    print(f"  ❌ Failed to get job status: {response.status_code}")
                    print(f"  Response: {response.text}")
                    print("\n❌ TEST FAIL")
                    sys.exit(1)
                
                status_data = response.json()
                status = status_data.get("status")
                
                print(f"  [{elapsed}s] Status: {status}")
                
                if status == "done":
                    print(f"  ✅ Job completed!")
                    break
                elif status == "failed":
                    error = status_data.get("error", "Unknown error")
                    print(f"  ❌ Job failed: {error}")
                    print("\n❌ TEST FAIL")
                    sys.exit(1)
                
                time.sleep(2)
                
            except requests.exceptions.RequestException as e:
                print(f"  ⚠️  Request error: {e}")
                time.sleep(2)
                continue
        
        if status != "done":
            print(f"  ⏱️  Timeout after {TIMEOUT_SECONDS}s")
            print("\n❌ TEST FAIL")
            sys.exit(1)
        
        # (C) Download summary.json and verify metrics.total_pnl_net exists
        print(f"\n[C] Downloading and verifying results...")
        
        # Get results endpoint
        response = requests.get(
            f"{base_url}{API_BASE}/{job_id}/results",
            headers=get_headers(),
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"  ❌ Failed to get results: {response.status_code}")
            print(f"  Response: {response.text}")
            print("\n❌ TEST FAIL")
            sys.exit(1)
        
        results_data = response.json()
        metrics = results_data.get("metrics")
        
        if not metrics:
            print(f"  ❌ No metrics in results: {results_data}")
            print("\n❌ TEST FAIL")
            sys.exit(1)
        
        # Verify total_pnl_net exists
        if "total_R_net" not in metrics:
            print(f"  ❌ Missing 'total_R_net' in metrics: {list(metrics.keys())}")
            print("\n❌ TEST FAIL")
            sys.exit(1)
        
        print(f"  ✅ Metrics found: {list(metrics.keys())}")
        print(f"  ✅ total_R_net: {metrics.get('total_R_net')}")
        
        # Also download summary.json file if available
        artifact_paths = results_data.get("artifact_paths", {})
        if "summary" in artifact_paths:
            summary_filename = artifact_paths["summary"]
            print(f"  Downloading summary.json...")
            
            response = requests.get(
                f"{base_url}{API_BASE}/{job_id}/download?file={summary_filename}",
                headers=get_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                try:
                    summary_data = response.json()
                    print(f"  ✅ Summary downloaded ({len(json.dumps(summary_data))} bytes)")
                except json.JSONDecodeError:
                    print(f"  ⚠️  Summary file is not valid JSON")
            else:
                print(f"  ⚠️  Failed to download summary: {response.status_code}")
        
        # (D) Success
        print("\n" + "=" * 80)
        print("✅ TEST PHASE C PASSE")
        print("=" * 80)
        print(f"Job ID: {job_id}")
        print(f"Metrics:")
        for key, value in metrics.items():
            print(f"  {key}: {value}")
        print("=" * 80)
        sys.exit(0)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ TEST FAIL")
        print(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()



