#!/usr/bin/env python3
import requests
import time
import json

API_URL = "https://dexteriobot.preview.emergentagent.com"

# Run backtest
request = {
    "symbols": ["SPY"],
    "start_date": "2025-08-01",
    "end_date": "2025-08-01",
    "trading_mode": "AGGRESSIVE",
    "trade_types": ["DAILY"],
    "htf_warmup_days": 40
}

print("🚀 Starting backtest...")
resp = requests.post(f"{API_URL}/api/backtests/run", json=request)
print(f"Response: {resp.status_code}")
data = resp.json()
job_id = data["job_id"]
print(f"Job ID: {job_id}")

# Poll status
print("\n⏳ Waiting for job to complete...")
for i in range(30):
    time.sleep(2)
    resp = requests.get(f"{API_URL}/api/backtests/{job_id}")
    status_data = resp.json()
    status = status_data["status"]
    print(f"  [{i*2}s] Status: {status}")
    
    if status in ["done", "failed"]:
        print(f"\n✅ Job {status}!")
        print(json.dumps(status_data, indent=2))
        break
