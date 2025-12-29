#!/usr/bin/env python3
"""
Quick test runner for Gate 1 RequestContext tests.
"""

import subprocess
import sys

if __name__ == "__main__":
    # Run pytest on the specific test file
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "tests/context/test_mode_headers.py",
            "-v", "--tb=short"
        ],
        cwd="/Users/jaynowman/dev/northstar-engines/northstar-engines"
    )
    sys.exit(result.returncode)
