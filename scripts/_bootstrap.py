"""Locate repository packages for checkout-based command entry points."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT, ROOT / "src"):
    value = str(directory)
    if value not in sys.path:
        sys.path.insert(0, value)
