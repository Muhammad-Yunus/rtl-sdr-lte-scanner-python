"""Domain-level exceptions.

These are raised by all layers (services, infrastructure, parser) and carry
actionable messages so the CLI can surface them without further annotation.
"""

from __future__ import annotations


class LteScannerError(Exception):
    """Base class for every error this application may raise."""


# -- Hardware & external process ---------------------------------------------


class SdrNotFoundError(LteScannerError):
    """No RTL-SDR dongle was reachable on the requested device index."""


class SrsranMissingError(LteScannerError):
    """The srsRAN binary could not be located on PATH or the configured path."""


class ScanTimeoutError(LteScannerError):
    """The srsRAN process did not finish within the configured timeout."""


# -- Parsing -----------------------------------------------------------------


class ParseError(LteScannerError):
    """srsRAN output did not match the expected structure."""


# -- Configuration & data ---------------------------------------------------


class ConfigError(LteScannerError):
    """Configuration file is missing, unreadable, or invalid."""


class OperatorLookupError(LteScannerError):
    """The operator database could not be loaded from disk."""