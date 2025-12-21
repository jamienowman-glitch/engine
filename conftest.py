import sys
from pathlib import Path

# Ensure repo root on sys.path for imports from anywhere in tests tree.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
