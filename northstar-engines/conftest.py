"""Pytest configuration for nested northstar-engines tests."""

import sys
from pathlib import Path

workspace_root = Path(__file__).parent.resolve()
repo_root = workspace_root.parent

# Prefer repo root to ensure we test real runtime engines code.
clean_path = []
for entry in sys.path:
    resolved = Path(entry or ".").resolve()
    if resolved == workspace_root or workspace_root in resolved.parents:
        continue
    clean_path.append(entry)
sys.path[:] = [str(repo_root)] + clean_path
