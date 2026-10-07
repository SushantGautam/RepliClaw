"""Pytest bootstrap: put `src/` on sys.path so `repliclaw` is importable
without installation (the package is `src/`-layout)."""
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
