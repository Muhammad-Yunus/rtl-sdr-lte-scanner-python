"""Unit tests for src/utils/frequency.py."""

from __future__ import annotations

import pytest

from src.domain.enums import Band, BandwidthMHz
from src.utils.frequency import (
    bandwidth_to_prb,
    earfcn_to_mhz,
    mhz_to_earfcn,
)


@pytest.mark.parametrize(
    "band, earfcn, expected_mhz",
    [
        # Anchor cases pulled directly from the AGENT.md example.
        (Band.BAND_5, 2400, 869.0),
        (Band.BAND_5, 2524, 881.4),
        # Sanity checks for additional bands.
        (Band.BAND_3, 1850, 1870.0),
        (Band.BAND_7, 3100, 2655.0),
        (Band.BAND_8, 3625, 942.5),
        (Band.BAND_20, 6300, 806.0),
    ],
)
def test_earfcn_to_mhz_known_pairs(band: Band, earfcn: int, expected_mhz: float) -> None:
    assert earfcn_to_mhz(earfcn, band) == pytest.approx(expected_mhz)


@pytest.mark.parametrize(
    "band, earfcn",
    [
        (Band.BAND_5, 2399),
        (Band.BAND_5, 2650),
        (Band.BAND_8, 3449),
        (Band.BAND_8, 3800),
    ],
)
def test_earfcn_to_mhz_rejects_out_of_range(band: Band, earfcn: int) -> None:
    with pytest.raises(ValueError, match="outside the valid range"):
        earfcn_to_mhz(earfcn, band)


def test_earfcn_to_mhz_rejects_non_int() -> None:
    with pytest.raises(TypeError, match="EARFCN must be an int"):
        earfcn_to_mhz(869.0, Band.BAND_5)  # type: ignore[arg-type]


def test_mhz_to_earfcn_round_trip() -> None:
    for band, earfcn in [
        (Band.BAND_5, 2400),
        (Band.BAND_5, 2649),
        (Band.BAND_3, 1200),
        (Band.BAND_8, 3799),
    ]:
        mhz = earfcn_to_mhz(earfcn, band)
        assert mhz_to_earfcn(mhz, band) == earfcn


def test_mhz_to_earfcn_below_band_start() -> None:
    with pytest.raises(ValueError, match="below"):
        mhz_to_earfcn(100.0, Band.BAND_5)


def test_mhz_to_earfcn_rejects_non_numeric() -> None:
    with pytest.raises(TypeError, match="must be numeric"):
        mhz_to_earfcn("869.5", Band.BAND_5)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "bandwidth, expected_prb",
    [
        (BandwidthMHz.BW_1_4, 6),
        (BandwidthMHz.BW_3, 15),
        (BandwidthMHz.BW_5, 25),
        (BandwidthMHz.BW_10, 50),
        (BandwidthMHz.BW_15, 75),
        (BandwidthMHz.BW_20, 100),
    ],
)
def test_bandwidth_to_prb_table(bandwidth: BandwidthMHz, expected_prb: int) -> None:
    assert bandwidth_to_prb(bandwidth) == expected_prb