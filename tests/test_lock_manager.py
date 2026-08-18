"""Tests for src/services/lock_manager.py."""

from __future__ import annotations

import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from src.services.lock_manager import (
    LOCK_FILE,
    LOCK_TIMEOUT_SECONDS,
    ScanDeviceBusyError,
    acquire_rtl_sdr_lock,
    is_device_busy,
)


@pytest.fixture(autouse=True)
def cleanup_lock_file():
    """Clean up lock file before and after each test."""
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()
    yield
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()


class TestAcquireLock:
    """Tests for acquire_rtl_sdr_lock context manager."""

    def test_acquire_and_release_lock(self):
        """Test basic lock acquisition and release."""
        with acquire_rtl_sdr_lock():
            assert LOCK_FILE.exists()

        assert not LOCK_FILE.exists()

    def test_lock_file_contains_pid(self):
        """Test that lock file contains process information."""
        with acquire_rtl_sdr_lock():
            content = LOCK_FILE.read_text()
            assert str(os.getpid()) in content
            # Should also contain a timestamp
            parts = content.strip().split()
            assert len(parts) == 2
            assert parts[0].isdigit()  # PID
            float(parts[1])  # Timestamp

    def test_lock_released_on_exception(self):
        """Test that lock is released even when exception occurs."""
        try:
            with acquire_rtl_sdr_lock():
                raise ValueError("Test error")
        except ValueError:
            pass

        assert not LOCK_FILE.exists()

    def test_timeout_configurable(self):
        """Test that timeout can be configured."""
        with patch('src.services.lock_manager.LOCK_TIMEOUT_SECONDS', 0.1):
            start = time.time()
            with pytest.raises(ScanDeviceBusyError):
                with acquire_rtl_sdr_lock():
                    with acquire_rtl_sdr_lock():
                        pass
            elapsed = time.time() - start
            
            # Should fail quickly due to short timeout
            assert elapsed < 1.0


class TestIsDeviceBusy:
    """Tests for is_device_busy function."""

    def test_not_busy_when_no_lock(self):
        """Test that device is not busy when no lock exists."""
        assert not is_device_busy()

    def test_busy_when_locked(self):
        """Test that device is busy when locked."""
        with acquire_rtl_sdr_lock():
            assert is_device_busy()

    def test_not_busy_after_release(self):
        """Test that device is not busy after lock is released."""
        with acquire_rtl_sdr_lock():
            pass

        assert not is_device_busy()


class TestScanDeviceBusyError:
    """Tests for ScanDeviceBusyError exception."""

    def test_default_message(self):
        """Test default error message."""
        exc = ScanDeviceBusyError()
        assert "busy" in exc.message.lower()
        assert issubclass(exc.__class__, Exception)

    def test_custom_message(self):
        """Test custom error message."""
        custom_msg = "Custom busy message"
        exc = ScanDeviceBusyError(custom_msg)
        assert exc.message == custom_msg
