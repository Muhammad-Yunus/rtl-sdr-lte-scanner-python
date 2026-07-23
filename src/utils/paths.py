"""Path resolution for both normal Python and PyInstaller bundled mode."""

from __future__ import annotations

import sys
from pathlib import Path


def get_data_dir() -> Path:
    """Return the directory containing data files (operators.json, etc.)."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "data"
    return Path(__file__).resolve().parent.parent.parent / "data"


def get_config_dir() -> Path:
    """Return the directory containing config files."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "configs"
    return Path(__file__).resolve().parent.parent.parent / "configs"
