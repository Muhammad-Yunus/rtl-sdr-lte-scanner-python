"""Unit tests for src/domain/models.py."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields

import pytest

from src.domain.enums import Band, BandwidthMHz
from src.domain.models import LTECell


def _sample_cell() -> LTECell:
    return LTECell(
        frequency_mhz=869.5,
        earfcn=2405,
        band=Band.BAND_5,
        bandwidth_mhz=BandwidthMHz.BW_10,
        pci=42,
        cell_id=12345,
        tac=4321,
        mcc=510,
        mnc=10,
        rsrp=-81,
        rsrq=-9,
        snr=22,
    )


def test_ltecell_construction_with_full_payload() -> None:
    cell = _sample_cell()
    assert cell.frequency_mhz == 869.5
    assert cell.earfcn == 2405
    assert cell.band is Band.BAND_5
    assert cell.bandwidth_mhz is BandwidthMHz.BW_10
    assert cell.pci == 42
    assert cell.cell_id == 12345
    assert cell.tac == 4321
    assert cell.mcc == 510
    assert cell.mnc == 10
    assert cell.rsrp == -81
    assert cell.rsrq == -9
    assert cell.snr == 22
    assert cell.operator is None
    assert cell.country is None


def test_ltecell_is_frozen() -> None:
    cell = _sample_cell()
    with pytest.raises(FrozenInstanceError):
        cell.mcc = 999  # type: ignore[misc]


def test_ltecell_timestamp_is_utc_and_recent() -> None:
    cell = _sample_cell()
    from datetime import datetime, timezone

    assert cell.timestamp.tzinfo is timezone.utc
    delta = datetime.now(timezone.utc) - cell.timestamp
    assert delta.total_seconds() < 5


def test_with_operator_returns_new_instance() -> None:
    cell = _sample_cell()
    enriched = cell.with_operator("Telkomsel", "Indonesia")

    assert enriched.operator == "Telkomsel"
    assert enriched.country == "Indonesia"
    assert cell.operator is None  # original is untouched (frozen)
    assert enriched is not cell


def test_ltecell_matches_agent_spec_fields() -> None:
    expected = {
        "frequency_mhz",
        "earfcn",
        "band",
        "bandwidth_mhz",
        "pci",
        "cell_id",
        "tac",
        "mcc",
        "mnc",
        "operator",
        "country",
        "rsrp",
        "rsrq",
        "snr",
        "timestamp",
    }
    assert {f.name for f in fields(LTECell)} == expected