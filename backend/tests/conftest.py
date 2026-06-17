"""Shared test fixtures for backend tests."""

import sys
from pathlib import Path

# Ensure the backend app package is importable in tests
sys.path.insert(0, str(Path(__file__).parent.parent))
