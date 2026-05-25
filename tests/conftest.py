"""Pytest config — add pipeline/ and scripts/ to sys.path so stage modules
and standalone scripts can be imported as top-level names from the tests
directory."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "scripts"))
