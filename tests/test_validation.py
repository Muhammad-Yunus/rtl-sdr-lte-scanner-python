"""Unit tests for src/utils/validation.py."""

from __future__ import annotations

import pytest

from src.utils.validation import (
    validate_earfcn,
    validate_frequency_mhz,
    validate_mcc,
    validate_mnc,
)


@pytest.mark.parametrize("value", [0, 1, 510, 999])
def test_validate_mcc_accepts(value: int) -> None:
    assert validate_mcc(value) == value


@pytest.mark.parametrize("value", [-1, 1000, 10000])
def test_validate_mcc_rejects(value: int) -> None:
    with pytest.raises(ValueError, match="outside the valid range"):
        validate_mcc(value)


def test_validate_mcc_rejects_non_int() -> None:
    with pytest.raises(TypeError, match="must be an int"):
        validate_mcc("510")  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [0, 1, 10, 999])
def test_validate_mnc_accepts(value: int) -> None:
    assert validate_mnc(value) == value


@pytest.mark.parametrize("value", [-1, 1000])
def test_validate_mnc_rejects(value: int) -> None:
    with pytest.raises(ValueError, match="outside the valid range"):
        validate_mnc(value)


@pytest.mark.parametrize("value", [300.0, 869.5, 2655.0, 3800.0, 6000.0])
def test_validate_frequency_mhz_accepts(value: float) -> None:
    assert validate_frequency_mhz(value) == value


@pytest.mark.parametrize("value", [-1.0, 100.0, 7000.0])
def test_validate_frequency_mhz_rejects(value: float) -> None:
    with pytest.raises(ValueError, match="outside the plausible LTE range"):
        validate_frequency_mhz(value)


def test_validate_frequency_mhz_rejects_non_numeric() -> None:
    with pytest.raises(TypeError, match="must be numeric"):
        validate_frequency_mhz("869.5")  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [0, 1, 2400, 65535])
def test_validate_earfcn_accepts(value: int) -> None:
    assert validate_earfcn(value) == value


@pytest.mark.parametrize("value", [-1, 65536])
def test_validate_earfcn_rejects(value: int) -> None:
    with pytest.raises(ValueError, match="outside the valid range"):
        validate_earfcn(value)