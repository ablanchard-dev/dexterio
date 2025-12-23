import sys
from pathlib import Path


# Ensure '/app/backend' is on sys.path so tests can import 'models', 'engines', 'backtest', 'scripts'.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
