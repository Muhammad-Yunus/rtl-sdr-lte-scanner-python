"""RTL-SDR device access lock manager.

This module provides a file-based lock to ensure exclusive access to the
RTL-SDR device. Only one process can use the device at a time - if another
process (including external services like lte-discovery) already holds the
lock, new scan requests are rejected immediately with an error.

Usage:
    with acquire_rtl_sdr_lock():
        # Only ONE process can execute here at a time
        result = run_cell_search(...)

The lock is automatically released when the context manager exits, even if
an exception occurs. If the locking process crashes, the lock file is cleaned
up on next acquisition attempt.
"""

from __future__ import annotations

import fcntl
import logging
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from ..domain.exceptions import ScanTimeoutError

_LOG = logging.getLogger(__name__)

# Lock file location - shared across all processes
LOCK_FILE = Path("/tmp/rtl_sdr_cell_search.lock")

# Maximum time to wait for lock (5 minutes)
LOCK_TIMEOUT_SECONDS = 300

# Time to wait between lock acquisition attempts (100ms)
LOCK_RETRY_INTERVAL = 0.1


class ScanDeviceBusyError(ScanTimeoutError):
    """The RTL-SDR device is currently in use by another process."""

    def __init__(self, message: str = "RTL-SDR device is busy - another process is using it") -> None:
        super().__init__(message)
        self.message = message


@contextmanager
def acquire_rtl_sdr_lock() -> Iterator[None]:
    """Acquire exclusive lock on RTL-SDR device with timeout.

    This context manager ensures only one process can access the RTL-SDR
    device at a time. If another process already holds the lock:

    1. Wait up to LOCK_TIMEOUT_SECONDS (5 minutes) for the lock to be released
    2. If timeout expires, raise ScanDeviceBusyError immediately

    The lock is automatically released when exiting the context manager,
    even if an exception occurs.

    Example:
        with acquire_rtl_sdr_lock():
            result = runner.run_cell_search(...)

    Raises:
        ScanDeviceBusyError: If the lock cannot be acquired within timeout.
    """
    fd = None
    start_time = time.time()

    try:
        while True:
            try:
                # Try to open and lock the file
                fd = open(LOCK_FILE, 'w')
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

                # Write PID and timestamp for debugging
                fd.write(f"{os.getpid()} {time.time()}\n")
                fd.flush()

                _LOG.debug("Acquired RTL-SDR lock (PID %d)", os.getpid())
                break

            except BlockingIOError:
                # Lock is held by another process
                fd.close()
                fd = None

                # Check if we've waited too long
                elapsed = time.time() - start_time
                if elapsed >= LOCK_TIMEOUT_SECONDS:
                    raise ScanDeviceBusyError(
                        f"RTL-SDR device is busy - another process has held the lock for "
                        f"{int(elapsed)} seconds (timeout: {LOCK_TIMEOUT_SECONDS}s)"
                    ) from None

                # Wait before retrying
                _LOG.debug(
                    "RTL-SDR lock busy, waiting %.1fs/%ds...",
                    elapsed, LOCK_TIMEOUT_SECONDS
                )
                time.sleep(LOCK_RETRY_INTERVAL)

        # Yield control to the caller
        yield

    finally:
        # Always release the lock
        if fd is not None:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
                fd.close()
                _LOG.debug("Released RTL-SDR lock")
            except Exception as e:
                _LOG.warning("Error releasing lock: %s", e)

        # Clean up lock file
        _cleanup_lock_file()


def _cleanup_lock_file() -> None:
    """Remove the lock file if it exists."""
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
            _LOG.debug("Cleaned up lock file: %s", LOCK_FILE)
    except Exception as e:
        _LOG.warning("Error cleaning up lock file: %s", e)


def is_device_busy() -> bool:
    """Check if the RTL-SDR device is currently locked.

    Returns:
        True if another process holds the lock, False otherwise.
    """
    if not LOCK_FILE.exists():
        return False

    try:
        fd = open(LOCK_FILE, 'r')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(fd, fcntl.LOCK_UN)
        fd.close()
        return False
    except BlockingIOError:
        return True
    except Exception:
        return False


__all__ = [
    "acquire_rtl_sdr_lock",
    "is_device_busy",
    "ScanDeviceBusyError",
    "LOCK_FILE",
    "LOCK_TIMEOUT_SECONDS",
]
