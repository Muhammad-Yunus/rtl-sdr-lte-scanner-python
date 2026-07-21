"""Filesystem helpers.

All exporters and the application layer funnel their writes through these
functions so that atomicity and directory creation live in one place.
"""

from __future__ import annotations

import os
from pathlib import Path

from ..domain.exceptions import ConfigError


def ensure_directory(path: Path) -> Path:
    """Create ``path`` (and parents) if it does not exist. Return the path."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ConfigError(f"Cannot create directory {path}: {exc}") from exc
    return path


def write_text_atomic(path: Path, content: str) -> Path:
    """Write ``content`` to ``path`` atomically via a sibling temp file."""
    ensure_directory(path.parent)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(content, encoding="utf-8")
        os.replace(tmp, path)
    except OSError as exc:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise ConfigError(f"Cannot write {path}: {exc}") from exc
    return path