"""Tests for src/infrastructure/filesystem.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.domain.exceptions import ConfigError
from src.infrastructure.filesystem import ensure_directory, write_text_atomic


def test_ensure_directory_creates_nested(tmp_path: Path) -> None:
    target = tmp_path / "a" / "b" / "c"
    assert ensure_directory(target) == target
    assert target.is_dir()


def test_ensure_directory_idempotent(tmp_path: Path) -> None:
    target = tmp_path / "x"
    ensure_directory(target)
    ensure_directory(target)
    assert target.is_dir()


def test_write_text_atomic_creates_file(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "out.txt"
    write_text_atomic(target, "hello\n")
    assert target.read_text(encoding="utf-8") == "hello\n"
    assert not target.with_suffix(target.suffix + ".tmp").exists()


def test_write_text_atomic_overwrites(tmp_path: Path) -> None:
    target = tmp_path / "out.txt"
    write_text_atomic(target, "first")
    write_text_atomic(target, "second")
    assert target.read_text(encoding="utf-8") == "second"


def test_ensure_directory_invalid_path_raises(tmp_path: Path) -> None:
    # A path under a file cannot be created as a directory.
    blocker = tmp_path / "blocker"
    blocker.write_text("not a dir", encoding="utf-8")
    with pytest.raises(ConfigError, match="Cannot create directory"):
        ensure_directory(blocker / "child")