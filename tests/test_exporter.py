"""Tests for src/services/exporter.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.domain.enums import Band, BandwidthMHz
from src.domain.models import LTECell
from src.services.exporter import ScanExporter


def _cell() -> LTECell:
    return LTECell(
        frequency_mhz=869.5,
        earfcn=2405,
        band=Band.BAND_5,
        bandwidth_mhz=BandwidthMHz.BW_10,
        pci=1,
        cell_id=1,
        tac=1,
        mcc=510,
        mnc=10,
    ).with_operator("Telkomsel", "Indonesia")


def test_export_json_writes_file(tmp_path: Path) -> None:
    exporter = ScanExporter(tmp_path)
    result = exporter.export_json([_cell()], "out.json")
    assert result.path.exists()
    assert result.cells_written == 1
    payload = json.loads(result.path.read_text(encoding="utf-8"))
    assert payload[0]["operator"] == "Telkomsel"
    assert payload[0]["mcc"] == 510


def test_export_csv_writes_file(tmp_path: Path) -> None:
    exporter = ScanExporter(tmp_path)
    result = exporter.export_csv([_cell()], "out.csv")
    assert result.path.exists()
    text = result.path.read_text(encoding="utf-8")
    assert "Telkomsel" in text
    assert "mcc" in text  # header


def test_export_creates_export_dir(tmp_path: Path) -> None:
    nested = tmp_path / "deep" / "down"
    exporter = ScanExporter(nested)
    result = exporter.export_json([_cell()], "out.json")
    assert result.path.parent == nested
    assert nested.is_dir()


def test_export_empty_cells(tmp_path: Path) -> None:
    exporter = ScanExporter(tmp_path)
    result = exporter.export_json([], "empty.json")
    assert result.path.exists()
    assert json.loads(result.path.read_text(encoding="utf-8")) == []


def test_export_overwrites_existing_file(tmp_path: Path) -> None:
    exporter = ScanExporter(tmp_path)
    exporter.export_json([_cell()], "out.json")
    exporter.export_csv([], "out.json")
    target = tmp_path / "out.json"
    text = target.read_text(encoding="utf-8")
    # csv header only (overwrote the json content)
    assert "frequency_mhz" in text
    assert "{" not in text  # the json content is gone