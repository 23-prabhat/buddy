#!/usr/bin/env python3
"""Convenience launcher from the repository root: python main.py"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ is on path when running without install
_SRC = Path(__file__).resolve().parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from bro.__main__ import main

if __name__ == "__main__":
    main()
