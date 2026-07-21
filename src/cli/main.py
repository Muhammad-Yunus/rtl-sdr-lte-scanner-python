"""Command-line entry point for ``lte-scan``.

The CLI is intentionally thin: it parses arguments, builds dependencies from
configuration, calls the application layer, and renders results.  It does
*not* parse LTE output or run subprocesses itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import typer

from ..application.scanner import CellParser, ScanOutcome, ScanRequest, ScanService
from ..domain.enums import Band, OutputFormat
from ..domain.exceptions import LteScannerError
from ..infrastructure.config import AppConfig
from ..infrastructure.logger import configure_logging
from ..repository.operator_db import OperatorDatabase
from ..services.cell_parser import SrsranCellParser
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
    """Construct the wired graph from a config file."""
    config = AppConfig.from_toml(config_path)
    configure_logging(config.logging.level, config.logging.file)

    from ..repository.frequency_band_db import FrequencyBandDatabase

    db = OperatorDatabase.from_json(Path("data/operators.json"))
    freq_db = FrequencyBandDatabase.from_json(Path("data/frequency_band_map.json"))
    resolver = OperatorResolver(db, freq_db)
    runner_impl = runner or SubprocessRunner()
    srsran_runner = __import__(
        "src.services.srsran_runner", fromlist=["SrsranRunner"]
    ).SrsranRunner(config.srsran.binary_path, runner_impl)
    parser_impl: CellParser = parser or SrsranCellParser()

    scan_service = ScanService(
        runner=srsran_runner,
        parser=parser_impl,
        resolver=resolver,
    )
    exporter = ScanExporter(config.output.export_dir)
    return Application(config=config, scan_service=scan_service, exporter=exporter)


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
    band: str | None = typer.Option(
        None,
        "--band",
        "-b",
        help="LTE band number to scan (e.g. '5', '8'). Defaults to config default_band.",
    ),
    gain: float | None = typer.Option(
        None,
        "--gain",
        "-g",
        help="RF gain in dB (40-49 recommended for RTL-SDR). Defaults to config gain_db.",
    ),
    timeout: float | None = typer.Option(
        None,
        "--timeout",
        help="Per-scan timeout in seconds. Defaults to [scan].timeout_seconds.",
    ),
    output_format: str | None = typer.Option(
        None,
        "--format",
        help="Output format: table, json, csv, yaml.",
    ),
) -> None:
    """Run one LTE cell scan and render the result."""
    app_obj = build_application(config)
    cfg = app_obj.config

    band_value = _band_option(band) if band is not None else cfg.scan.default_band
    gain_value = gain if gain is not None else cfg.scan.gain_db
    timeout_value = float(timeout) if timeout is not None else float(cfg.scan.timeout_seconds)

    request = ScanRequest(
        band=band_value,
        gain_db=gain_value,
        timeout_seconds=timeout_value,
    )

    fmt = _format_option(output_format) if output_format else cfg.output.format

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
    band: str | None = typer.Option(None, "--band", "-b"),
    gain: float | None = typer.Option(None, "--gain", "-g"),
    timeout: float | None = typer.Option(None, "--timeout"),
) -> None:
    """Run a scan and write the result to ``destination``."""
    app_obj = build_application(config)
    cfg = app_obj.config
    band_value = _band_option(band) if band is not None else cfg.scan.default_band
    gain_value = gain if gain is not None else cfg.scan.gain_db
    timeout_value = float(timeout) if timeout is not None else float(cfg.scan.timeout_seconds)

    request = ScanRequest(
        band=band_value,
        gain_db=gain_value,
        timeout_seconds=timeout_value,
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
