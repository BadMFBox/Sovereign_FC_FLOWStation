# ═══════════════════════════════════════════════════════════════
#  tests/python/conftest.py
#  Shared fixtures for all tests
# ═══════════════════════════════════════════════════════════════

import pytest
import json
import shutil
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock


# ───────────────────────────────────────────────────────────────
#  BASE FIXTURE — Isolated temp workspace
# ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def workspace(tmp_path):
    """
    Fresh isolated workspace for every test.
    No shared state. No leftover files.
    Every test starts clean.
    """
    dirs = [
        "forge/active",
        "forge/locked",
        "forge/versions",
        "splitter/output",
        "sorter/input",
        "sorter/output",
        "integration/input",
        "integration/merge",
        "integration/logic_locks",
        "integration/output/mesh",
        "shared",
        "tests/fixtures",
    ]
    for d in dirs:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)

    # Keep logs dir with .gitkeep
    (tmp_path / "logs").mkdir(exist_ok=True)
    (tmp_path / "logs" / ".gitkeep").touch()

    return tmp_path


@pytest.fixture(scope="function")
def sample_python_file():
    """A clean Python file with classes and functions."""
    return '''"""
Sample module for testing.
"""

import os
from typing import Optional


def process_data(data: list, threshold: float = 0.5) -> dict:
    """
    Process input data against threshold.
    Returns summary dict.
    """
    result = {}
    for i, item in enumerate(data):
        if item > threshold:
            result[i] = item
    return result


def validate_input(value: str) -> bool:
    """Validate string input is not empty."""
    if not value or not isinstance(value, str):
        return False
    return len(value.strip()) > 0


class DataProcessor:
    """Handles data transformation pipeline."""

    def __init__(self, config: dict):
        self.config = config
        self._cache: dict = {}

    def run(self, data: list) -> dict:
        """Execute the processing pipeline."""
        return process_data(data, self.config.get("threshold", 0.5))

    def clear_cache(self) -> None:
        """Clear internal cache."""
        self._cache.clear()


class ConfigManager:
    """Manages configuration state."""

    DEFAULT_CONFIG = {
        "threshold": 0.5,
        "timeout":   30,
        "retries":   3,
    }

    def load(self, path: str) -> dict:
        """Load config from file path."""
        with open(path) as f:
            import json
            return json.load(f)

    def validate(self, config: dict) -> bool:
        """Validate config has required keys."""
        required = ["threshold", "timeout"]
        return all(k in config for k in required)
'''


@pytest.fixture(scope="function")
def sample_room(workspace, sample_python_file):
    """
    A ready-to-use room with Python files.
    Simulates a real forge active workspace.
    """
    room_dir = workspace / "forge" / "active" / "room-test"
    room_dir.mkdir(parents=True, exist_ok=True)

    # Create multiple Python files
    (room_dir / "process.py").write_text(sample_python_file)
    (room_dir / "config.py").write_text('''"""Config utilities."""

def load_config(path: str) -> dict:
    """Load configuration from path."""
    import json
    with open(path) as f:
        return json.load(f)

def get_default() -> dict:
    """Return default configuration."""
    return {"threshold": 0.5, "timeout": 30}
''')
    (room_dir / "utils.py").write_text('''"""Shared utilities."""

def sanitize(value: str) -> str:
    """Strip and lowercase input."""
    return value.strip().lower()

def chunk_list(data: list, size: int) -> list:
    """Split list into chunks of given size."""
    return [data[i:i+size] for i in range(0, len(data), size)]
''')

    return room_dir
