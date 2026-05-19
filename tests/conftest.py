"""Pytest config — add pipeline/ to sys.path so the stage modules can be
imported as top-level names from the tests directory."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
