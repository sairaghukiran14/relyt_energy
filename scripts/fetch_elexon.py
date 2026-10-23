#!/usr/bin/env python
"""Entry point for downloading and loading Elexon data. Run from the backend venv:

    cd backend && uv run python ../scripts/fetch_elexon.py
"""

import sys
from pathlib import Path

# Make the backend package importable regardless of the current directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.ingest.elexon import run  # noqa: E402

if __name__ == "__main__":
    run()
