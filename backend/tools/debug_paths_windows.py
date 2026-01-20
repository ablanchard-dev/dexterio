#!/usr/bin/env python3
"""
PHASE A1 - Windows Path Resolution Diagnostic

Prouve exactement où repo_root() pointe et pourquoi.
Produit un artefact JSON falsifiable.

Usage:
    cd C:\bots\dexterio1-main\backend
    python tools\debug_paths_windows.py
"""

import os
import sys
import json
import platform
from pathlib import Path

# Ajouter backend au path pour imports
_backend_dir = Path(__file__).parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from utils.path_resolver import (
    repo_root, 
    historical_data_path, 
    results_path,
    backend_path,
    data_path
)


def check_path_exists(path: Path) -> dict:
    """Vérifie existence + métadonnées d'un chemin"""
    return {
        "path": str(path),
        "exists": path.exists(),
        "is_dir": path.is_dir() if path.exists() else None,
        "is_file": path.is_file() if path.exists() else None,
    }


def main():
    print("=" * 80)
    print("PHASE A1 — WINDOWS PATH RESOLUTION DIAGNOSTIC")
    print("=" * 80)
    
    diagnostic = {
        "timestamp": str(Path(__file__).stat().st_mtime),
        "environment": {},
        "paths": {},
        "file_discovery": {},
        "validation": {}
    }
    
    # === ENVIRONMENT ===
    print("\n📊 ENVIRONMENT")
    print("-" * 80)
    
    env_info = {
        "os_name": os.name,
        "platform_system": platform.system(),
        "platform_release": platform.release(),
        "python_version": platform.python_version(),
        "cwd": str(Path.cwd()),
        "script_location": str(Path(__file__).resolve()),
        "env_DEXTERIO_REPO_ROOT": os.getenv("DEXTERIO_REPO_ROOT"),
        "dockerenv_exists": Path("/.dockerenv").exists(),
        "app_dir_exists": Path("/app").exists(),
    }
    
    for key, value in env_info.items():
        print(f"  {key:30s}: {value}")
    
    diagnostic["environment"] = env_info
    
    # === PATH RESOLUTION ===
    print("\n📁 PATH RESOLUTION")
    print("-" * 80)
    
    try:
        root = repo_root()
        print(f"  repo_root():                   {root}")
        diagnostic["paths"]["repo_root"] = check_path_exists(root)
        
        backend = backend_path()
        print(f"  backend_path():                {backend}")
        diagnostic["paths"]["backend_path"] = check_path_exists(backend)
        
        data = data_path()
        print(f"  data_path():                   {data}")
        diagnostic["paths"]["data_path"] = check_path_exists(data)
        
        hist = historical_data_path("1m")
        print(f"  historical_data_path('1m'):    {hist}")
        diagnostic["paths"]["historical_1m"] = check_path_exists(hist)
        
        results = results_path()
        print(f"  results_path():                {results}")
        diagnostic["paths"]["results_path"] = check_path_exists(results)
        
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        diagnostic["paths"]["error"] = str(e)
    
    # === FILE DISCOVERY ===
    print("\n🔍 FILE DISCOVERY")
    print("-" * 80)
    
    try:
        hist_dir = historical_data_path("1m")
        if hist_dir.exists():
            parquet_files = list(hist_dir.glob("*.parquet"))
            print(f"  Found {len(parquet_files)} Parquet files in historical/1m/:")
            for pf in parquet_files[:5]:  # Max 5
                size_mb = pf.stat().st_size / (1024 * 1024)
                print(f"    - {pf.name} ({size_mb:.1f} MB)")
            
            diagnostic["file_discovery"]["historical_1m"] = {
                "exists": True,
                "parquet_count": len(parquet_files),
                "files": [pf.name for pf in parquet_files]
            }
        else:
            print(f"  ❌ historical/1m/ does not exist: {hist_dir}")
            diagnostic["file_discovery"]["historical_1m"] = {
                "exists": False,
                "path_checked": str(hist_dir)
            }
        
        # Check tests directory
        tests_locations = [
            backend_path("tests"),
            repo_root() / "tests"
        ]
        
        for test_loc in tests_locations:
            if test_loc.exists():
                test_files = list(test_loc.glob("test_*.py"))
                print(f"  Found {len(test_files)} test files in {test_loc.relative_to(repo_root())}/")
                diagnostic["file_discovery"][f"tests_{test_loc.name}"] = {
                    "exists": True,
                    "path": str(test_loc),
                    "test_count": len(test_files)
                }
                break
        
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        diagnostic["file_discovery"]["error"] = str(e)
    
    # === VALIDATION ===
    print("\n✅ VALIDATION")
    print("-" * 80)
    
    validations = {
        "repo_root_is_local": False,
        "repo_root_not_app": False,
        "backend_dir_exists": False,
        "data_dir_exists": False,
        "historical_1m_exists": False,
        "spy_parquet_exists": False,
    }
    
    try:
        root = repo_root()
        
        # Check repo_root is NOT /app or \app
        if str(root) not in ["/app", "\\app", "C:\\app"]:
            validations["repo_root_not_app"] = True
            print(f"  ✅ repo_root is NOT /app: {root}")
        else:
            print(f"  ❌ repo_root IS /app (WRONG on Windows): {root}")
        
        # Check repo_root looks like local path
        if os.name == 'nt':  # Windows
            if ":\\" in str(root) or str(root).startswith("\\"):
                validations["repo_root_is_local"] = True
                print(f"  ✅ repo_root looks like Windows path")
            else:
                print(f"  ❌ repo_root does NOT look like Windows path")
        
        # Check critical dirs exist
        if backend_path().exists():
            validations["backend_dir_exists"] = True
            print(f"  ✅ backend/ exists")
        else:
            print(f"  ❌ backend/ NOT found")
        
        if data_path().exists():
            validations["data_dir_exists"] = True
            print(f"  ✅ data/ exists")
        else:
            print(f"  ❌ data/ NOT found")
        
        if historical_data_path("1m").exists():
            validations["historical_1m_exists"] = True
            print(f"  ✅ historical/1m/ exists")
        else:
            print(f"  ❌ historical/1m/ NOT found")
        
        spy_file = historical_data_path("1m", "SPY.parquet")
        if spy_file.exists():
            validations["spy_parquet_exists"] = True
            print(f"  ✅ SPY.parquet exists")
        else:
            print(f"  ❌ SPY.parquet NOT found")
    
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        validations["error"] = str(e)
    
    diagnostic["validation"] = validations
    
    # === SUMMARY ===
    print("\n" + "=" * 80)
    all_pass = all([
        validations["repo_root_not_app"],
        validations["backend_dir_exists"],
        validations["data_dir_exists"],
    ])
    
    if all_pass:
        print("✅ PATH RESOLUTION OK (Windows compatible)")
    else:
        print("❌ PATH RESOLUTION FAILED")
        print("\nFailed checks:")
        for key, value in validations.items():
            if value is False:
                print(f"  - {key}")
    
    print("=" * 80)
    
    # === SAVE ARTIFACT ===
    output_file = results_path("windows_path_debug.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(diagnostic, f, indent=2)
    
    print(f"\n💾 Diagnostic saved: {output_file}")
    
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
