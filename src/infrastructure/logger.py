"""Logger configuration.

The application has a single named logger (``lte_scan``). Configuration is
read from :class:`infrastructure.config.LoggingConfig`.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from ..domain.exceptions import ConfigError

_LOGGER_NAME = "lte_scan"
_VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def configure_logging(level: str, file: Path) -> logging.Logger:
    """Configure the application logger.

    Idempotent: subsequent calls replace handlers rather than appending.
    """
    upper = level.upper()
    if upper not in _VALID_LEVELS:
        raise ConfigError(
            f"Invalid logging level {level!r}. Expected one of {sorted(_VALID_LEVELS)}."
        )

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(upper)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    stream_handler = logging.StreamHandler(stream=sys.stderr)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    file_str = str(file)
    if file_str and file != Path():
        path = Path(file_str)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.propagate = False
    return logger


def get_logger() -> logging.Logger:
    """Return the configured logger; configure lazily on first access."""
    logger = logging.getLogger(_LOGGER_NAME)
    if not logger.handlers:
        configure_logging("INFO", Path(""))
    return logger