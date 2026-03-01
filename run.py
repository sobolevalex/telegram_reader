#!/usr/bin/env python3
"""Run telegram_reader from project root (no install required)."""

import sys
from pathlib import Path

# Add src so "telegram_reader" package is found when running from project root
_root = Path(__file__).resolve().parent
_src = _root / "src"
if _src.exists() and str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from telegram_reader.main import main

if __name__ == "__main__":
    main()
