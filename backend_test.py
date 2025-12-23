#!/usr/bin/env python3
"""
Backend Testing for P0.6.3 - Windowed Downloader 1m + Quality Gates + Polygon Integration
Testing Agent - DexterioBOT Trading Bot

This script tests:
1. P0.6.3 - Windowed Downloader 1m + Quality Gates (yfinance)
2. P0.6.3 - Polygon provider integration (rate limit + pagination)
3. P0.6.3 - Data discovery plug-and-play (single-file)
"""

import os
import sys
import json
import subprocess
import logging
from pathlib import Path
from datetime import datetime, date

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class P063Tester:
    def __init__(self):
        self.app_root = Path("/app")
        self.backend_root = Path("/app/backend")
        self.data_dir = Path("/app/data/historical/1m")
        self.results = {}
        
        # Check for Polygon API key
        self.polygon_api_key = os.environ.get("POLYGON_API_KEY")
        if self.polygon_api_key:
            logger.info("✅ POLYGON_API_KEY found in environment")
        else:
            logger.warning("⚠️ POLYGON_API_KEY not found in environment")
        
    def test_module_invocation(self):
        """Test 1: Verify module can be invoked from /app root with --provider polygon option"""
        logger.info("=== TEST 1: Module Invocation ===")
        
        try:
            # Change to app root directory
            os.chdir(self.app_root)
            
            # Test help command
            result = subprocess.run(
                [sys.executable, "-m", "scripts.download_intraday_windowed", "--help"],
                cwd=self.app_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Check if --provider option includes polygon
                help_output = result.stdout
                if "--provider" in help_output and "polygon" in help_output:
                    logger.info("✅ Module invocation successful with polygon provider option")
                    logger.info("Help output preview: %s", result.stdout[:200] + "...")
                    self.results["module_invocation"] = {"status": "PASS", "details": "Help command executed successfully with polygon provider option"}
                    return True
                else:
                    logger.error("❌ --provider polygon option not found in help")
                    self.results["module_invocation"] = {"status": "FAIL", "details": "--provider polygon option not found in help output"}
                    return False
            else:
                logger.error("❌ Module invocation failed")
                logger.error("STDERR: %s", result.stderr)
                self.results["module_invocation"] = {"status": "FAIL", "details": f"Return code: {result.returncode}, Error: {result.stderr}"}
                return False
                
        except Exception as e:
            logger.error("❌ Exception during module invocation: %s", str(e))
            self.results["module_invocation"] = {"status": "FAIL", "details": f"Exception: {str(e)}"}
            return False
    
    def test_short_download_run(self):
        """Test 2: Execute SHORT run within 30-day window"""
        logger.info("=== TEST 2: Short Download Run ===")
        
        try:
            # Ensure data directory exists
            self.data_dir.mkdir(parents=True, exist_ok=True)
            
            # Change to app root directory
            os.chdir(self.app_root)
            
            # Define test parameters (within 30-day window to avoid yfinance limits)
            symbol = "SPY"
            start_date = "2025-11-20"
            end_date = "2025-11-22"
            window_days = 2
            output_file = self.data_dir / "SPY_TEST30.parquet"
            
            # Remove existing test files
            if output_file.exists():
                output_file.unlink()
            
            quality_report = self.data_dir / f"data_quality_{symbol}.json"
            if quality_report.exists():
                quality_report.unlink()
            
            # Execute download command
            cmd = [
                sys.executable, "-m", "scripts.download_intraday_windowed",
                "--symbol", symbol,
                "--start", start_date,
                "--end", end_date,
                "--window-days", str(window_days),
                "--out", str(output_file),
                "--retries", "2",
                "--request-delay-seconds", "0.5",
                "--backoff-seconds", "1"
            ]
            
            logger.info("Executing command: %s", " ".join(cmd))
            
            result = subprocess.run(
                cmd,
                cwd=self.app_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            logger.info("Command output: %s", result.stdout)
            if result.stderr:
                logger.warning("Command stderr: %s", result.stderr)
            
            # Check if command succeeded
            if result.returncode != 0:
                # Check if it's the expected yfinance 30-day limit error
                if "30 days" in result.stderr or "requested range must be within" in result.stderr:
                    logger.warning("⚠️ Expected yfinance 30-day limit error encountered")
                    self.results["short_download"] = {
                        "status": "EXPECTED_FAIL", 
                        "details": f"yfinance 30-day limit error: {result.stderr}",
                        "yfinance_error": result.stderr
                    }
                    return "expected_fail"
                else:
                    logger.error("❌ Download failed with unexpected error")
                    self.results["short_download"] = {
                        "status": "FAIL", 
                        "details": f"Unexpected error: {result.stderr}"
                    }
                    return False
            
            # Check if parquet file was created
            if not output_file.exists():
                logger.error("❌ Parquet file was not created: %s", output_file)
                self.results["short_download"] = {"status": "FAIL", "details": "Parquet file not created"}
                return False
            
            # Check if quality report was created
            if not quality_report.exists():
                logger.error("❌ Quality report was not created: %s", quality_report)
                self.results["short_download"] = {"status": "FAIL", "details": "Quality report not created"}
                return False
            
            # Validate quality report content
            try:
                with open(quality_report, 'r') as f:
                    quality_data = json.load(f)
                
                # Check required fields
                required_gates = ["timezone_utc", "no_duplicate_timestamps"]
                gates_passed = True
                
                for gate in required_gates:
                    if gate not in quality_data.get("gates", {}):
                        logger.error("❌ Missing gate: %s", gate)
                        gates_passed = False
                    elif not quality_data["gates"][gate].get("passed", False):
                        logger.warning("⚠️ Gate failed: %s", gate)
                        gates_passed = False
                    else:
                        logger.info("✅ Gate passed: %s", gate)
                
                # Check for daily_missing and corrupted_days
                has_daily_missing = "daily_missing" in quality_data
                has_corrupted_days = "corrupted_days" in quality_data
                
                logger.info("Quality report summary:")
                logger.info("  - timezone_utc.passed: %s", quality_data.get("gates", {}).get("timezone_utc", {}).get("passed"))
                logger.info("  - no_duplicate_timestamps.passed: %s", quality_data.get("gates", {}).get("no_duplicate_timestamps", {}).get("passed"))
                logger.info("  - daily_missing present: %s", has_daily_missing)
                logger.info("  - corrupted_days present: %s", has_corrupted_days)
                logger.info("  - corrupted_days count: %d", len(quality_data.get("corrupted_days", [])))
                
                if gates_passed and has_daily_missing and has_corrupted_days:
                    logger.info("✅ Short download run successful")
                    self.results["short_download"] = {
                        "status": "PASS", 
                        "details": "Parquet and quality report created successfully",
                        "quality_summary": {
                            "timezone_utc_passed": quality_data.get("gates", {}).get("timezone_utc", {}).get("passed"),
                            "no_duplicates_passed": quality_data.get("gates", {}).get("no_duplicate_timestamps", {}).get("passed"),
                            "corrupted_days_count": len(quality_data.get("corrupted_days", []))
                        }
                    }
                    return True
                else:
                    logger.error("❌ Quality report validation failed")
                    self.results["short_download"] = {"status": "FAIL", "details": "Quality report validation failed"}
                    return False
                    
            except Exception as e:
                logger.error("❌ Error reading quality report: %s", str(e))
                self.results["short_download"] = {"status": "FAIL", "details": f"Error reading quality report: {str(e)}"}
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Download command timed out")
            self.results["short_download"] = {"status": "FAIL", "details": "Command timed out"}
            return False
        except Exception as e:
            logger.error("❌ Exception during download: %s", str(e))
            self.results["short_download"] = {"status": "FAIL", "details": f"Exception: {str(e)}"}
            return False
    
    def test_data_discovery_patch(self):
        """Test 3: Test micro-patch of discovery in backtest/run.py"""
        logger.info("=== TEST 3: Data Discovery Patch ===")
        
        try:
            # Ensure data directory exists
            self.data_dir.mkdir(parents=True, exist_ok=True)
            
            # Create minimal SPY.parquet file if it doesn't exist
            spy_file = self.data_dir / "SPY.parquet"
            if not spy_file.exists():
                logger.info("Creating minimal SPY.parquet file for testing")
                import pandas as pd
                from datetime import datetime, timezone
                
                # Create minimal test data
                test_data = pd.DataFrame({
                    'datetime': [datetime.now(timezone.utc)],
                    'open': [400.0],
                    'high': [401.0],
                    'low': [399.0],
                    'close': [400.5],
                    'volume': [1000000]
                })
                test_data.to_parquet(spy_file, index=False)
                logger.info("✅ Created minimal SPY.parquet file")
            
            # Change to backend directory
            os.chdir(self.backend_root)
            
            # Test discovery function
            test_code = """
from backtest.run import discover_data_paths
result = discover_data_paths('/app/data/historical/1m', ['SPY'])
print(result)
"""
            
            result = subprocess.run(
                [sys.executable, "-c", test_code],
                cwd=self.backend_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                logger.info("Discovery function output: %s", output)
                
                # Check if SPY.parquet path is returned
                expected_path = "/app/data/historical/1m/SPY.parquet"
                if expected_path in output:
                    logger.info("✅ Data discovery patch working correctly")
                    self.results["data_discovery"] = {
                        "status": "PASS", 
                        "details": f"Correctly discovered: {output}",
                        "discovered_paths": output
                    }
                    return True
                else:
                    logger.error("❌ Expected path not found in discovery output")
                    self.results["data_discovery"] = {
                        "status": "FAIL", 
                        "details": f"Expected {expected_path} but got: {output}"
                    }
                    return False
            else:
                logger.error("❌ Discovery function failed")
                logger.error("STDERR: %s", result.stderr)
                self.results["data_discovery"] = {
                    "status": "FAIL", 
                    "details": f"Discovery function error: {result.stderr}"
                }
                return False
                
        except Exception as e:
            logger.error("❌ Exception during data discovery test: %s", str(e))
            self.results["data_discovery"] = {"status": "FAIL", "details": f"Exception: {str(e)}"}
            return False
    
    def test_polygon_minimal_download(self):
        """Test 4: Polygon minimal download (2 days)"""
        logger.info("=== TEST 4: Polygon Minimal Download ===")
        
        if not self.polygon_api_key:
            logger.warning("⚠️ Skipping Polygon test - no API key")
            self.results["polygon_minimal"] = {"status": "SKIP", "details": "No POLYGON_API_KEY environment variable"}
            return "skip"
        
        try:
            # Ensure data directory exists
            self.data_dir.mkdir(parents=True, exist_ok=True)
            
            # Change to app root directory
            os.chdir(self.app_root)
            
            # Define test parameters
            symbol = "SPY"
            start_date = "2025-11-20"
            end_date = "2025-11-22"
            window_days = 7
            output_file = self.data_dir / "SPY_POLY_TEST.parquet"
            
            # Remove existing test files
            if output_file.exists():
                output_file.unlink()
            
            quality_report = self.data_dir / f"data_quality_{symbol}.json"
            if quality_report.exists():
                quality_report.unlink()
            
            # Set environment variable for the test
            env = os.environ.copy()
            env["POLYGON_API_KEY"] = self.polygon_api_key
            
            # Execute Polygon download command
            cmd = [
                sys.executable, "-m", "scripts.download_intraday_windowed",
                "--provider", "polygon",
                "--symbol", symbol,
                "--start", start_date,
                "--end", end_date,
                "--window-days", str(window_days),
                "--out", str(output_file),
                "--retries", "2",
                "--backoff-seconds", "1",
                "--request-delay-seconds", "0.2",
                "--polygon-rate-limit-sleep-seconds", "5"
            ]
            
            logger.info("Executing Polygon command: %s", " ".join(cmd))
            
            result = subprocess.run(
                cmd,
                cwd=self.app_root,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes timeout
                env=env
            )
            
            logger.info("Command output: %s", result.stdout)
            if result.stderr:
                logger.warning("Command stderr: %s", result.stderr)
            
            # Check if command succeeded
            if result.returncode != 0:
                logger.error("❌ Polygon download failed")
                self.results["polygon_minimal"] = {
                    "status": "FAIL", 
                    "details": f"Polygon download error: {result.stderr}"
                }
                return False
            
            # Check if parquet file was created
            if not output_file.exists():
                logger.error("❌ Polygon parquet file was not created: %s", output_file)
                self.results["polygon_minimal"] = {"status": "FAIL", "details": "Polygon parquet file not created"}
                return False
            
            # Check if quality report was created
            if not quality_report.exists():
                logger.error("❌ Polygon quality report was not created: %s", quality_report)
                self.results["polygon_minimal"] = {"status": "FAIL", "details": "Polygon quality report not created"}
                return False
            
            # Validate quality report content
            try:
                with open(quality_report, 'r') as f:
                    quality_data = json.load(f)
                
                # Check required gates
                required_gates = ["timezone_utc", "no_duplicate_timestamps", "window_download_success_rate"]
                gates_passed = True
                
                for gate in required_gates:
                    if gate not in quality_data.get("gates", {}):
                        logger.error("❌ Missing gate: %s", gate)
                        gates_passed = False
                    elif not quality_data["gates"][gate].get("passed", False):
                        logger.warning("⚠️ Gate failed: %s", gate)
                        gates_passed = False
                    else:
                        logger.info("✅ Gate passed: %s", gate)
                
                logger.info("Polygon quality report summary:")
                logger.info("  - timezone_utc.passed: %s", quality_data.get("gates", {}).get("timezone_utc", {}).get("passed"))
                logger.info("  - no_duplicate_timestamps.passed: %s", quality_data.get("gates", {}).get("no_duplicate_timestamps", {}).get("passed"))
                logger.info("  - window_download_success_rate.passed: %s", quality_data.get("gates", {}).get("window_download_success_rate", {}).get("passed"))
                
                if gates_passed:
                    logger.info("✅ Polygon minimal download successful")
                    self.results["polygon_minimal"] = {
                        "status": "PASS", 
                        "details": "Polygon parquet and quality report created successfully",
                        "quality_summary": {
                            "timezone_utc_passed": quality_data.get("gates", {}).get("timezone_utc", {}).get("passed"),
                            "no_duplicates_passed": quality_data.get("gates", {}).get("no_duplicate_timestamps", {}).get("passed"),
                            "window_success_passed": quality_data.get("gates", {}).get("window_download_success_rate", {}).get("passed")
                        }
                    }
                    return True
                else:
                    logger.error("❌ Polygon quality report validation failed")
                    self.results["polygon_minimal"] = {"status": "FAIL", "details": "Polygon quality report validation failed"}
                    return False
                    
            except Exception as e:
                logger.error("❌ Error reading Polygon quality report: %s", str(e))
                self.results["polygon_minimal"] = {"status": "FAIL", "details": f"Error reading Polygon quality report: {str(e)}"}
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Polygon download command timed out")
            self.results["polygon_minimal"] = {"status": "FAIL", "details": "Polygon command timed out"}
            return False
        except Exception as e:
            logger.error("❌ Exception during Polygon download: %s", str(e))
            self.results["polygon_minimal"] = {"status": "FAIL", "details": f"Exception: {str(e)}"}
            return False
    
    def test_polygon_rate_limit_handling(self):
        """Test 5: Polygon rate-limit handling (6 weeks test)"""
        logger.info("=== TEST 5: Polygon Rate-Limit Handling ===")
        
        if not self.polygon_api_key:
            logger.warning("⚠️ Skipping Polygon rate-limit test - no API key")
            self.results["polygon_rate_limit"] = {"status": "SKIP", "details": "No POLYGON_API_KEY environment variable"}
            return "skip"
        
        try:
            # Ensure data directory exists
            self.data_dir.mkdir(parents=True, exist_ok=True)
            
            # Change to app root directory
            os.chdir(self.app_root)
            
            # Define test parameters (6 weeks)
            symbol = "SPY"
            start_date = "2025-06-01"
            end_date = "2025-07-15"
            window_days = 7
            output_file = self.data_dir / "SPY_POLY_6W_TEST.parquet"
            
            # Remove existing test files
            if output_file.exists():
                output_file.unlink()
            
            quality_report = self.data_dir / f"data_quality_{symbol}.json"
            if quality_report.exists():
                quality_report.unlink()
            
            # Set environment variable for the test
            env = os.environ.copy()
            env["POLYGON_API_KEY"] = self.polygon_api_key
            
            # Execute Polygon download command with longer period
            cmd = [
                sys.executable, "-m", "scripts.download_intraday_windowed",
                "--provider", "polygon",
                "--symbol", symbol,
                "--start", start_date,
                "--end", end_date,
                "--window-days", str(window_days),
                "--out", str(output_file),
                "--retries", "4",
                "--backoff-seconds", "1",
                "--request-delay-seconds", "0.2",
                "--polygon-rate-limit-sleep-seconds", "10"
            ]
            
            logger.info("Executing Polygon 6-week command: %s", " ".join(cmd))
            
            result = subprocess.run(
                cmd,
                cwd=self.app_root,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutes timeout for longer test
                env=env
            )
            
            logger.info("Command output: %s", result.stdout)
            if result.stderr:
                logger.warning("Command stderr: %s", result.stderr)
            
            # Check if command succeeded
            if result.returncode != 0:
                logger.error("❌ Polygon 6-week download failed")
                self.results["polygon_rate_limit"] = {
                    "status": "FAIL", 
                    "details": f"Polygon 6-week download error: {result.stderr}"
                }
                return False
            
            # Check if parquet file was created
            if not output_file.exists():
                logger.error("❌ Polygon 6-week parquet file was not created: %s", output_file)
                self.results["polygon_rate_limit"] = {"status": "FAIL", "details": "Polygon 6-week parquet file not created"}
                return False
            
            # Check if quality report was created
            if not quality_report.exists():
                logger.error("❌ Polygon 6-week quality report was not created: %s", quality_report)
                self.results["polygon_rate_limit"] = {"status": "FAIL", "details": "Polygon 6-week quality report not created"}
                return False
            
            # Validate quality report and check for retry evidence
            try:
                with open(quality_report, 'r') as f:
                    quality_data = json.load(f)
                
                # Check if any windows had retries (evidence of rate limiting)
                windows = quality_data.get("windows", [])
                retry_evidence = any(w.get("attempts", 1) > 1 for w in windows)
                
                # Check if quality passed
                quality_passed = quality_data.get("passed", False)
                
                logger.info("Polygon 6-week test results:")
                logger.info("  - Quality passed: %s", quality_passed)
                logger.info("  - Retry evidence (attempts > 1): %s", retry_evidence)
                logger.info("  - Total windows: %d", len(windows))
                
                if quality_passed:
                    logger.info("✅ Polygon 6-week download successful with rate-limit handling")
                    self.results["polygon_rate_limit"] = {
                        "status": "PASS", 
                        "details": f"Polygon 6-week download successful, retry evidence: {retry_evidence}",
                        "retry_evidence": retry_evidence,
                        "total_windows": len(windows)
                    }
                    return True
                else:
                    logger.error("❌ Polygon 6-week quality gates failed")
                    self.results["polygon_rate_limit"] = {"status": "FAIL", "details": "Polygon 6-week quality gates failed"}
                    return False
                    
            except Exception as e:
                logger.error("❌ Error reading Polygon 6-week quality report: %s", str(e))
                self.results["polygon_rate_limit"] = {"status": "FAIL", "details": f"Error reading Polygon 6-week quality report: {str(e)}"}
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Polygon 6-week download command timed out")
            self.results["polygon_rate_limit"] = {"status": "FAIL", "details": "Polygon 6-week command timed out"}
            return False
        except Exception as e:
            logger.error("❌ Exception during Polygon 6-week download: %s", str(e))
            self.results["polygon_rate_limit"] = {"status": "FAIL", "details": f"Exception: {str(e)}"}
            return False
    
    def run_all_tests(self):
        """Run all P0.6.3 tests including Polygon integration"""
        logger.info("🚀 Starting P0.6.3 Backend Tests (including Polygon)")
        logger.info("=" * 60)
        
        # Test 1: Module invocation (with polygon provider check)
        test1_result = self.test_module_invocation()
        
        # Test 2: Short download run (yfinance)
        test2_result = self.test_short_download_run()
        
        # Test 3: Data discovery patch
        test3_result = self.test_data_discovery_patch()
        
        # Test 4: Polygon minimal download
        test4_result = self.test_polygon_minimal_download()
        
        # Test 5: Polygon rate-limit handling (only if minimal test passed)
        if test4_result == True:
            test5_result = self.test_polygon_rate_limit_handling()
        else:
            logger.warning("⚠️ Skipping Polygon rate-limit test due to minimal test failure")
            self.results["polygon_rate_limit"] = {"status": "SKIP", "details": "Skipped due to minimal test failure"}
        
        # Summary
        logger.info("=" * 60)
        logger.info("🏁 P0.6.3 Test Results Summary (including Polygon)")
        logger.info("=" * 60)
        
        for test_name, result in self.results.items():
            status_emoji = "✅" if result["status"] == "PASS" else "⚠️" if result["status"] in ["EXPECTED_FAIL", "SKIP"] else "❌"
            logger.info("%s %s: %s", status_emoji, test_name, result["status"])
            if result.get("details"):
                logger.info("   Details: %s", result["details"])
        
        return self.results

def main():
    """Main test execution"""
    tester = P063Tester()
    results = tester.run_all_tests()
    
    # Return appropriate exit code
    failed_tests = [name for name, result in results.items() if result["status"] == "FAIL"]
    if failed_tests:
        logger.error("❌ Tests failed: %s", ", ".join(failed_tests))
        return 1
    else:
        logger.info("✅ All tests completed successfully")
        return 0

if __name__ == "__main__":
    exit(main())