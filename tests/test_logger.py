"""Tests for src/infrastructure/logger.py."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from src.domain.exceptions import ConfigError
from src.infrastructure.logger import _LOGGER_NAME, configure_logging, get_logger


@pytest.fixture(autouse=True)
def _reset_logger() -> None:
    logger = logging.getLogger(_LOGGER_NAME)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
    yield
    logger.setLevel(logging.NOTSET)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)


def test_configure_invalid_level_raises() -> None:
    with pytest.raises(ConfigError, match="Invalid logging level"):
        configure_logging("verbose", Path(""))


def test_configure_writes_to_file(tmp_path: Path) -> None:
    log_file = tmp_path / "sub" / "app.log"
    logger = configure_logging("INFO", log_file)
    logger.info("hello world")
    for handler in logger.handlers:
        handler.flush()
    contents = log_file.read_text(encoding="utf-8")
    assert "hello world" in contents
    assert _LOGGER_NAME in contents


def test_configure_is_idempotent() -> None:
    logger = configure_logging("INFO", Path(""))
    first_handlers = list(logger.handlers)
    configure_logging("DEBUG", Path(""))
    second_handlers = list(logger.handlers)
    assert len(first_handlers) == len(second_handlers)
    assert logger.level == logging.DEBUG


def test_get_logger_returns_configured_instance() -> None:
    logger = get_logger()
    assert logger.name == _LOGGER_NAME
    assert logger.handlers  # configured lazily if not already