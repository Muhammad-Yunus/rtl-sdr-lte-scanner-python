"""Render :class:`LTECell` lists as text/JSON/CSV/YAML."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict
from typing import Iterable

import yaml
from rich.console import Console
from rich.table import Table

from ..domain.enums import Band, BandwidthMHz, OutputFormat
from ..domain.models import LTECell


def cell_to_dict(cell: LTECell) -> dict:
    """Convert a cell to a JSON-friendly dict.

    Enums become their string values; ``timestamp`` becomes ISO-8601.
    """
    payload = asdict(cell)
    payload["band"] = str(cell.band.value)
    payload["bandwidth_mhz"] = int(cell.bandwidth_mhz.value)
    payload["timestamp"] = cell.timestamp.isoformat()
    return payload


def render_table(cells: Iterable[LTECell]) -> str:
    """Render cells with rich and capture the output as text."""
    console = Console(record=True, width=120, file=io.StringIO())
    table = Table(title="LTE Cell Discovery", show_lines=False)
    for header in (
        "Frequency",
        "Band",
        "EARFCN",
        "PCI",
        "Cell ID",
        "TAC",
        "Bandwidth",
        "MCC",
        "MNC",
        "Operator",
        "RSRP",
        "RSRQ",
        "SNR",
    ):
        table.add_column(header, justify="left", no_wrap=True)

    for cell in cells:
        table.add_row(
            f"{cell.frequency_mhz:.3f} MHz",
            cell.band.label,
            str(cell.earfcn),
            str(cell.pci),
            str(cell.cell_id),
            str(cell.tac),
            f"{int(cell.bandwidth_mhz.value)} MHz",
            str(cell.mcc),
            str(cell.mnc),
            cell.operator or "-",
            f"{cell.rsrp} dBm" if cell.rsrp is not None else "-",
            f"{cell.rsrq} dB" if cell.rsrq is not None else "-",
            f"{cell.snr} dB" if cell.snr is not None else "-",
        )
    console.print(table)
    return console.export_text()


def render_json(cells: Iterable[LTECell]) -> str:
    return json.dumps(
        [cell_to_dict(c) for c in cells],
        indent=2,
        ensure_ascii=False,
    )


def _empty_row_schema() -> list[str]:
    """Return the field names of :class:`LTECell` as serialised by CSV."""
    sample = LTECell(
        frequency_mhz=0.0,
        earfcn=0,
        band=Band.BAND_5,
        bandwidth_mhz=BandwidthMHz.BW_10,
        pci=0,
        cell_id=0,
        tac=0,
        mcc=0,
        mnc=0,
    )
    return list(cell_to_dict(sample).keys())


def render_csv(cells: Iterable[LTECell]) -> str:
    rows = [cell_to_dict(c) for c in cells]
    buffer = io.StringIO()
    if not rows:
        writer = csv.DictWriter(buffer, fieldnames=_empty_row_schema())
        writer.writeheader()
        return buffer.getvalue()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def render_yaml(cells: Iterable[LTECell]) -> str:
    return yaml.safe_dump(
        [cell_to_dict(c) for c in cells],
        sort_keys=False,
        allow_unicode=True,
    )


_RENDERERS = {
    OutputFormat.TABLE: render_table,
    OutputFormat.JSON: render_json,
    OutputFormat.CSV: render_csv,
    OutputFormat.YAML: render_yaml,
}


def render(cells: Iterable[LTECell], output_format: OutputFormat) -> str:
    try:
        renderer = _RENDERERS[output_format]
    except KeyError as exc:
        raise ValueError(f"Unsupported output format: {output_format}") from exc
    return renderer(cells)