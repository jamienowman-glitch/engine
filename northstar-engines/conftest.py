"""
Pytest configuration for northstar-engines tests.
"""

import sys
from pathlib import Path

# Add workspace root to sys.path so imports work
workspace_root = Path(__file__).parent
sys.path.insert(0, str(workspace_root))
