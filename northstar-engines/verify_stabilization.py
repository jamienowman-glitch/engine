#!/usr/bin/env python3
"""
Verification script for Gate 1 ModeCTX stabilization.
Checks that all files are in place and tests pass.
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a shell command and report results."""
    print(f"\n{'='*70}")
    print(f"✓ {description}")
    print(f"{'='*70}")
    result = subprocess.run(cmd, shell=True, cwd="/Users/jaynowman/dev/northstar-engines/northstar-engines")
    if result.returncode != 0:
        print(f"✗ FAILED: {description}")
        return False
    return True

def check_file(path, description):
    """Check if a file exists."""
    p = Path(path)
    if p.exists():
        size = p.stat().st_size
        print(f"✓ {description} ({size} bytes)")
        return True
    else:
        print(f"✗ MISSING: {description}")
        return False

def main():
    print("\n" + "="*70)
    print("GATE 1 MODECTX STABILIZATION VERIFICATION")
    print("="*70)
    
    all_good = True
    
    # Check files exist
    print("\n[FILE STRUCTURE]")
    files_to_check = [
        ("engines/__init__.py", "Package marker: engines/"),
        ("engines/common/__init__.py", "Package marker: engines/common/"),
        ("engines/common/identity.py", "Core: RequestContext + RequestContextBuilder"),
        ("tests/__init__.py", "Package marker: tests/"),
        ("tests/context/__init__.py", "Package marker: tests/context/"),
        ("tests/context/test_mode_headers.py", "Tests: 30+ test cases"),
        ("conftest.py", "Pytest config"),
        ("pytest.ini", "Test discovery"),
        ("pyproject.toml", "Project metadata"),
        ("docs/foundational/PHASE_0_2_STATUS_UPDATE.md", "Status update doc"),
        ("docs/ModeCTX_Entrypoints.md", "Integration guide"),
        ("MERGE_CHECKLIST.md", "Merge strategy"),
        ("STABILIZATION_SUMMARY.md", "This summary"),
    ]
    
    for filepath, description in files_to_check:
        if not check_file(filepath, description):
            all_good = False
    
    # Check imports work
    print("\n[IMPORT VERIFICATION]")
    if run_command(
        'python3 -c "from engines.common.identity import RequestContext, RequestContextBuilder, get_request_context; print(\'✓ All imports successful\')"',
        "Test imports from engines.common.identity"
    ):
        print("✓ All imports successful")
    else:
        all_good = False
    
    # Run tests
    print("\n[TEST EXECUTION]")
    if run_command(
        "python3 -m pytest tests/context/test_mode_headers.py -v --tb=short",
        "Run all ModeCTX tests"
    ):
        print("✓ All tests passed")
    else:
        all_good = False
    
    # Summary
    print("\n" + "="*70)
    if all_good:
        print("✓✓✓ GATE 1 MODECTX STABILIZATION COMPLETE ✓✓✓")
        print("="*70)
        print("\nReady for merge!")
        print("\nNext steps:")
        print("1. Review MERGE_CHECKLIST.md for integration steps")
        print("2. Run: git add <files>")
        print("3. Run: git commit -F COMMIT_MESSAGE.txt")
        print("4. Run: git push")
        return 0
    else:
        print("✗✗✗ VERIFICATION FAILED ✗✗✗")
        print("="*70)
        print("\nPlease fix the issues above and try again.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
