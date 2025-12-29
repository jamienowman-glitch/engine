#!/usr/bin/env python3
"""
Test runner for Gate 1 integration: ModeCTX + EventEnvelope.
Runs both test suites and reports results.
"""

import subprocess
import sys

def run_tests(test_path, description):
    """Run pytest on a path and report results."""
    print(f"\n{'='*70}")
    print(f"Running: {description}")
    print(f"Path: {test_path}")
    print('='*70)
    
    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short"],
        cwd="/Users/jaynowman/dev/northstar-engines/northstar-engines"
    )
    return result.returncode == 0

def main():
    print("\n" + "="*70)
    print("GATE 1 INTEGRATION TEST SUITE (ModeCTX + EventEnvelope)")
    print("="*70)
    
    all_passed = True
    
    # Test Suite 1: ModeCTX
    print("\n[SUITE 1: ModeCTX (Mode-only RequestContext)]")
    if not run_tests("tests/context/test_mode_headers.py", "ModeCTX tests"):
        all_passed = False
    
    # Test Suite 2: Event Contract
    print("\n[SUITE 2: EventEnvelope (Event Contract)]")
    if not run_tests("tests/logs/test_event_contract.py", "Event contract tests"):
        all_passed = False
    
    # Test Suite 3: Integration
    print("\n[SUITE 3: ModeCTX + EventEnvelope Integration]")
    if not run_tests("tests/logs/test_integration_modectx_envelope.py", "Integration tests"):
        all_passed = False
    
    # Summary
    print("\n" + "="*70)
    if all_passed:
        print("✅ ALL TEST SUITES PASSED")
        print("="*70)
        print("\nGate 1 integration baseline is ready for merge!")
        return 0
    else:
        print("❌ SOME TEST SUITES FAILED")
        print("="*70)
        return 1

if __name__ == "__main__":
    sys.exit(main())
