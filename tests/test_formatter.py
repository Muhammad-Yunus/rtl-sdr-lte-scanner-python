"""Tests for src/services/formatter.py."""

from __future__ import annotations

import json

import pytest

from src.domain.enums import Band, BandwidthMHz, OutputFormat
from src.domain.models import LTECell
from src.services.formatter import (
    cell_to_dict,
    render,
    render_csv,
    render_json,
    render_table,
    render_yaml,
)


def _cell() -> LTECell:
    return LTECell(
        frequency_mhz=869.53,
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


def test_cell_to_dict_stringifies_enums_and_timestamp() -> None:
    d = cell_to_dict(_cell())
    assert d["band"] == "5"
    assert d["bandwidth_mhz"] == 10
    assert isinstance(d["timestamp"], str)
    assert d["mcc"] == 510


def test_render_json_round_trip() -> None:
    payload = json.loads(render_json([_cell()]))
    assert isinstance(payload, list) and len(payload) == 1
    assert payload[0]["mcc"] == 510
    assert payload[0]["band"] == "5"


def test_render_csv_has_header_and_one_row() -> None:
    out = render_csv([_cell()])
    lines = out.strip().splitlines()
    assert len(lines) == 2
    header = lines[0].split(",")
    assert header[0] == "frequency_mhz"
    assert "earfcn" in header


def test_render_csv_empty() -> None:
    out = render_csv([])
    # Empty input still emits a header row so consumers can inspect the schema.
    assert "frequency_mhz" in out
    assert out.strip().count("\n") == 0  # header only


def test_render_yaml_contains_payload() -> None:
    out = render_yaml([_cell().with_operator("Telkomsel", "Indonesia")])
    assert "mcc: 510" in out
    assert "Telkomsel" in out


def test_render_table_includes_headers() -> None:
    cell = _cell().with_operator("Telkomsel", "Indonesia")
    out = render_table([cell])
    assert "LTE Cell Discovery" in out
    assert "Frequency" in out
    assert "Telkomsel" in out


def test_render_table_handles_optional_signals() -> None:
    sparse = LTECell(
        frequency_mhz=869.53,
        earfcn=2405,
        band=Band.BAND_5,
        bandwidth_mhz=BandwidthMHz.BW_10,
        pci=42,
        cell_id=12345,
        tac=4321,
        mcc=510,
        mnc=10,
    )
    out = render_table([sparse])
    assert "LTE Cell Discovery" in out
    # Dashes appear for missing signal values.
    assert "-" in out


def test_render_dispatches_by_format() -> None:
    for fmt in OutputFormat:
        out = render([_cell()], fmt)
        assert isinstance(out, str)
        assert out  # never empty


def test_render_unknown_format_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported output format"):
        render([_cell()], "xml")  # type: ignore[arg-type]