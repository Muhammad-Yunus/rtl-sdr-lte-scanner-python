"""Command-line entry point for ``lte-scan``.

The CLI is intentionally thin: it parses arguments, builds dependencies from
configuration, calls the application layer, and renders results. It does
*not* parse LTE output or run subprocesses itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import typer

from ..application.scanner import CellParser, ScanOutcome, ScanRequest, ScanService
from ..domain.enums import Band, BandwidthMHz, OutputFormat
from ..domain.exceptions import LteScannerError
from ..domain.models import LTECell
from ..infrastructure.config import AppConfig
from ..infrastructure.logger import configure_logging
from ..repository.operator_db import OperatorDatabase
from ..services.exporter import ScanExporter
from ..services.formatter import render
from ..services.operator_resolver import OperatorResolver
from ..services.srsran_runner import SubprocessRunner

__version__ = "0.1.0"

app = typer.Typer(
    name="lte-scan",
    help="Local LTE cell scanner built on RTL-SDR V3 and srsRAN.",
    no_args_is_help=True,
)


@dataclass(frozen=True, slots=True)
class Application:
    """Wired-up dependencies the CLI hands to the application layer."""

    config: AppConfig
    scan_service: ScanService
    exporter: ScanExporter


def build_application(
    config_path: Path,
    *,
    parser: CellParser | None = None,
    runner: SubprocessRunner | None = None,
) -> Application:
    """Construct the wired graph from a config file.

    Both ``parser`` and ``runner`` are injectable so tests can substitute
    them. ``parser`` defaults to a placeholder until the real srsRAN parser
    lands — see :class:`PendingParser`.
    """
    config = AppConfig.from_toml(config_path)
    configure_logging(config.logging.level, config.logging.file)

    db = OperatorDatabase.from_json(Path("data/operators.json"))
    resolver = OperatorResolver(db)
    runner_impl = runner or SubprocessRunner()
    srsran_runner = __import__(
        "src.services.srsran_runner", fromlist=["SrsranRunner"]
    ).SrsranRunner(config.srsran.binary_path, runner_impl)
    parser_impl: CellParser = parser or PendingParser()

    scan_service = ScanService(
        runner=srsran_runner,
        parser=parser_impl,
        resolver=resolver,
    )
    exporter = ScanExporter(config.output.export_dir)
    return Application(config=config, scan_service=scan_service, exporter=exporter)


class PendingParser:
    """Stub parser used until the real srsRAN parser is implemented.

    Returning an empty list keeps the CLI functional for ``--help`` and
    configuration checks without lying about scan results.
    """

    def parse(self, stdout: str) -> list[LTECell]:  # pragma: no cover - trivial
        return []


def _bandwidth_option(value: str) -> BandwidthMHz:
    """Parse ``--bw`` strings like ``"10"`` or ``"10MHz"``."""
    cleaned = value.strip().lower().replace("mhz", "").strip()
    try:
        bw_value = int(cleaned)
    except ValueError as exc:
        raise typer.BadParameter(
            f"Bandwidth must be an integer MHz value, got {value!r}."
        ) from exc
    for member in BandwidthMHz:
        if int(member.value) == bw_value:
            return member
    raise typer.BadParameter(
        f"Unsupported bandwidth: {bw_value} MHz. Choose one of "
        f"{[int(m.value) for m in BandwidthMHz]} MHz."
    )


def _band_option(value: str) -> int:
    cleaned = value.strip().lower().replace("band", "").strip()
    try:
        band_value = int(cleaned)
    except ValueError as exc:
        raise typer.BadParameter(f"Band must be an integer, got {value!r}.") from exc
    if not any(int(b.value) == band_value for b in Band):
        raise typer.BadParameter(
            f"Unsupported band: {band_value}. Supported: "
            f"{[int(b.value) for b in Band]}."
        )
    return band_value


def _format_option(value: str) -> OutputFormat:
    try:
        return OutputFormat(value.strip().lower())
    except ValueError as exc:
        raise typer.BadParameter(
            f"Unsupported format {value!r}. Choose from "
            f"{[m.value for m in OutputFormat]}."
        ) from exc


@app.command()
def scan(
    config: Path = typer.Option(
        Path("configs/config.toml"),
        "--config",
        "-c",
        help="Path to the TOML configuration file.",
    ),
    freq: Optional[float] = typer.Option(
        None,
        "--freq",
        help="Central frequency in MHz. Defaults to [scan].default_frequency_mhz.",
    ),
    bw: Optional[str] = typer.Option(
        None,
        "--bw",
        help="Channel bandwidth (e.g. '10' or '10MHz'). Defaults to 10 MHz.",
    ),
    band: Optional[str] = typer.Option(
        None,
        "--band",
        help="LTE band number (e.g. '5'). Informational only at this stage.",
    ),
    device: Optional[int] = typer.Option(
        None,
        "--device",
        help="RTL-SDR device index. Defaults to [device].index.",
    ),
    timeout: Optional[float] = typer.Option(
        None,
        "--timeout",
        help="Per-scan timeout in seconds. Defaults to [scan].timeout_seconds.",
    ),
    output_format: Optional[str] = typer.Option(
        None,
        "--format",
        help="Output format: table, json, csv, yaml.",
    ),
) -> None:
    """Run one LTE cell scan and render the result."""
    app_obj = build_application(config)
    cfg = app_obj.config

    bandwidth = _bandwidth_option(bw) if bw else BandwidthMHz.BW_10
    request = ScanRequest(
        frequency_mhz=float(freq) if freq is not None else cfg.scan.default_frequency_mhz,
        bandwidth=bandwidth,
        device_index=int(device) if device is not None else cfg.device.index,
        timeout_seconds=float(timeout) if timeout is not None else float(cfg.scan.timeout_seconds),
    )

    fmt = _format_option(output_format) if output_format else cfg.output.format
    if band is not None:
        _ = _band_option(band)  # validates input; value is informational only

    try:
        outcome: ScanOutcome = app_obj.scan_service.run(request)
    except LteScannerError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(render(outcome.cells, fmt), err=False)


@app.command("export")
def export_cmd(
    config: Path = typer.Option(
        Path("configs/config.toml"),
        "--config",
        "-c",
        help="Path to the TOML configuration file.",
    ),
    destination: Path = typer.Argument(
        ...,
        help="Destination filename (suffix determines format: .json or .csv).",
    ),
    freq: Optional[float] = typer.Option(None, "--freq"),
    bw: Optional[str] = typer.Option(None, "--bw"),
    device: Optional[int] = typer.Option(None, "--device"),
    timeout: Optional[float] = typer.Option(None, "--timeout"),
) -> None:
    """Run a scan and write the result to ``destination``."""
    app_obj = build_application(config)
    cfg = app_obj.config
    bandwidth = _bandwidth_option(bw) if bw else BandwidthMHz.BW_10
    request = ScanRequest(
        frequency_mhz=float(freq) if freq is not None else cfg.scan.default_frequency_mhz,
        bandwidth=bandwidth,
        device_index=int(device) if device is not None else cfg.device.index,
        timeout_seconds=float(timeout) if timeout is not None else float(cfg.scan.timeout_seconds),
    )
    try:
        outcome = app_obj.scan_service.run(request)
    except LteScannerError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    suffix = destination.suffix.lower()
    if suffix == ".json":
        exported = app_obj.exporter.export_json(outcome.cells, destination.name)
    elif suffix == ".csv":
        exported = app_obj.exporter.export_csv(outcome.cells, destination.name)
    else:
        raise typer.BadParameter(
            f"Unsupported export suffix {suffix!r}. Use .json or .csv."
        )
    typer.echo(f"Wrote {exported.cells_written} cells to {exported.path}")


@app.command()
def version() -> None:
    """Print the application version."""
    typer.echo(f"lte-scan {__version__}")


if __name__ == "__main__":
    app()