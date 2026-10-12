"""Vendored official HiddenBench import path (unmodified third_party copy)."""
from __future__ import annotations

import sys
from pathlib import Path

HB_SRC = Path(__file__).resolve().parents[4] / "third_party" / "hiddenbench" / "src"


def ensure_path() -> Path:
    """Put the vendored HiddenBench ``src/`` on ``sys.path`` and import it."""
    path = str(HB_SRC)
    if path not in sys.path:
        sys.path.insert(0, path)
    import hiddenbench  # noqa: F401

    return HB_SRC
