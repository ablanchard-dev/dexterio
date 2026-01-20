#!/usr/bin/env python3
"""
P2 Phase 1 - Automated Path Migration Script

Ce script remplace automatiquement les hardcoded paths /app/... 
par des appels à path_resolver dans tous les fichiers Python.

Usage:
    python backend/tools/p2_migrate_paths.py --dry-run
    python backend/tools/p2_migrate_paths.py --execute
"""
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Patterns to replace
REPLACEMENTS = [
    # Historical data paths
    (r"['\"]\/app\/data\/historical\/1m\/", "str(historical_data_path('1m')) + '/"),
    (r"['\"]\/app\/data\/historical\/([^'\"]+)['\"]", r"str(historical_data_path('\1'))"),
    
    # Results paths
    (r"['\"]\/app\/backend\/results\/([^'\"]*)['\"]", r"str(results_path('\1'))"),
    (r"['\"]\/app\/backend\/results['\"]", "str(results_path())"),
    
    # Backtest results
    (r"['\"]\/app\/data\/backtest_results\/([^'\"]*)['\"]", r"str(backtest_results_path('\1'))"),
    (r"['\"]\/app\/data\/backtest_results['\"]", "str(backtest_results_path())"),
    
    # Data paths general
    (r"['\"]\/app\/data\/([^'\"]+)['\"]", r"str(data_path('\1'))"),
]

IMPORT_LINE = "from utils.path_resolver import historical_data_path, results_path, data_path, backtest_results_path\n"


def add_import_if_needed(content: str) -> str:
    """Add path_resolver import if not present and if replacements were made."""
    if "from utils.path_resolver import" in content:
        return content  # Already has import
    
    # Check if any /app/ paths exist
    if "/app/" not in content:
        return content  # No need for import
    
    # Find where to insert (after other imports)
    lines = content.split('\n')
    insert_idx = 0
    
    # Find last import or last docstring
    in_docstring = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Track docstrings
        if stripped.startswith('"""') or stripped.startswith("'''"):
            if in_docstring:
                in_docstring = False
                insert_idx = i + 1
            else:
                in_docstring = True
        
        # Track imports
        if not in_docstring and (stripped.startswith('import ') or stripped.startswith('from ')):
            insert_idx = i + 1
    
    # Insert import after last import
    lines.insert(insert_idx, IMPORT_LINE.rstrip())
    return '\n'.join(lines)


def migrate_file(filepath: Path, dry_run: bool = True) -> Tuple[bool, int]:
    """
    Migrates a single file.
    
    Returns:
        (was_modified, num_replacements)
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    num_replacements = 0
    
    # Apply replacements
    for pattern, replacement in REPLACEMENTS:
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            matches = len(re.findall(pattern, content))
            num_replacements += matches
            content = new_content
    
    # Add import if needed
    if num_replacements > 0:
        content = add_import_if_needed(content)
    
    modified = (content != original)
    
    if modified and not dry_run:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return modified, num_replacements


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Migrate hardcoded /app/ paths to path_resolver")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without modifying files")
    parser.add_argument("--execute", action="store_true", help="Actually modify files")
    args = parser.parse_args()
    
    if not (args.dry_run or args.execute):
        print("ERROR: Must specify --dry-run or --execute")
        sys.exit(1)
    
    # Files to migrate
    backend_root = Path(__file__).parent.parent
    patterns = [
        "backtest/*.py",
        "tools/*.py",
        "engines/*.py",
        "config/*.py",
    ]
    
    files_to_check = []
    for pattern in patterns:
        files_to_check.extend(backend_root.glob(pattern))
    
    # Exclude this migration script itself
    files_to_check = [f for f in files_to_check if f.name != "p2_migrate_paths.py"]
    
    print(f"{'=' * 80}")
    print(f"P2 PATH MIGRATION - {'DRY RUN' if args.dry_run else 'EXECUTING'}")
    print(f"{'=' * 80}")
    print(f"Checking {len(files_to_check)} files...")
    print()
    
    total_modified = 0
    total_replacements = 0
    
    for filepath in sorted(files_to_check):
        modified, num_repl = migrate_file(filepath, dry_run=args.dry_run)
        
        if modified:
            total_modified += 1
            total_replacements += num_repl
            rel_path = filepath.relative_to(backend_root.parent)
            status = "✏️  WOULD MODIFY" if args.dry_run else "✅ MODIFIED"
            print(f"{status}: {rel_path} ({num_repl} replacements)")
    
    print()
    print(f"{'=' * 80}")
    print(f"Summary:")
    print(f"  Files modified: {total_modified}")
    print(f"  Total replacements: {total_replacements}")
    
    if args.dry_run:
        print()
        print("ℹ️  This was a DRY RUN. Re-run with --execute to apply changes.")
    else:
        print()
        print("✅ Migration complete!")
    
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
