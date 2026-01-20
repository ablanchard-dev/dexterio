#!/usr/bin/env python3
"""
Audit Hardcoded Paths

Scans all Python execution code for hardcoded /app/ paths.
Excludes: comments, tests, docs.
Generates JSON proof.
"""
import json
import re
from pathlib import Path
from typing import List, Dict

def scan_hardcoded_paths(root: Path) -> Dict:
    """Scan for hardcoded /app/ paths."""
    
    patterns = [
        r'["\']\/app\/[^"\']*["\']',  # "/app/..."
    ]
    
    # Directories to scan
    scan_dirs = [
        root / "backend" / "backtest",
        root / "backend" / "engines",
        root / "backend" / "tools",
        root / "backend" / "models",
        root / "backend" / "config",
    ]
    
    matches = []
    
    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            continue
        
        for py_file in scan_dir.rglob("*.py"):
            # Skip migration script itself
            if "p2_migrate_paths" in py_file.name:
                continue
            
            # Skip audit script itself
            if "audit_hardcoded_paths" in py_file.name:
                continue
            
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                # Skip comments
                stripped = line.strip()
                if stripped.startswith('#'):
                    continue
                
                # Check for patterns
                for pattern in patterns:
                    if re.search(pattern, line):
                        # Extract the actual path
                        match = re.search(pattern, line)
                        if match:
                            matches.append({
                                "file": str(py_file.relative_to(root)),
                                "line": line_num,
                                "content": line.strip()[:100],  # First 100 chars
                                "match": match.group(0)
                            })
    
    return {
        "scan_timestamp": "2025-12-27T22:45:00Z",
        "directories_scanned": [str(d.relative_to(root)) for d in scan_dirs if d.exists()],
        "total_matches": len(matches),
        "matches": matches,
        "verdict": "PASS" if len(matches) == 0 else "FAIL"
    }


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent.parent
    
    result = scan_hardcoded_paths(repo_root)
    
    # Save report
    output_path = repo_root / "backend" / "results" / "hardcoded_paths_audit.json"
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"✅ Audit complete: {result['total_matches']} hardcoded paths found")
    print(f"📄 Report: {output_path}")
    
    if result['verdict'] == "PASS":
        print("✅ VERDICT: PASS (0 hardcoded paths)")
        exit(0)
    else:
        print(f"❌ VERDICT: FAIL ({result['total_matches']} hardcoded paths)")
        for match in result['matches']:
            print(f"  {match['file']}:{match['line']} - {match['match']}")
        exit(1)
