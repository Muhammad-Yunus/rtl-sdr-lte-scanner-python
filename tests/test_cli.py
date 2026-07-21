"""Tests for src/cli/main.py."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from src.cli.main import _band_option, _format_option, app
from src.domain.enums import OutputFormat

FIXTURE_CONFIG = Path("tests/fixtures/config.toml")
runner = CliRunner()


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "lte-scan" in result.stdout


def test_help_lists_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "scan" in result.stdout
    assert "export" in result.stdout
    assert "version" in result.stdout


def test_scan_with_unknown_dongle_shows_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When srsRAN is not on PATH, exit code must be non-zero."""
    monkeypatch.setattr("shutil.which", lambda _name: None)
    import tempfile
    import textwrap

    with tempfile.TemporaryDirectory() as tmp:
        import shutil
        data_dir = Path(tmp) / "data"
        data_dir.mkdir()
        shutil.copy2(Path("data/operators.json"), data_dir / "operators.json")
        config = Path(tmp) / "cfg.toml"
        config.write_text(
            textwrap.dedent(
                """
                [device]
                index = 0
                [scan]
                default_frequency_mhz = 869.5
                default_band = 8
                gain_db = 42.0
                timeout_seconds = 1
                retry_count = 0
                [output]
                format = "table"
                export_dir = "./out"
                [logging]
                level = "INFO"
                file = ""
                [srsran]
                binary_path = ""
                """
            ),
            encoding="utf-8",
        )
        cwd = __import__("os").getcwd()
        try:
            __import__("os").chdir(tmp)
            result = runner.invoke(app, ["scan", "--config", str(config)])
        finally:
            __import__("os").chdir(cwd)
    assert result.exit_code != 0
    combined = (
        (result.stdout or "")
        + (result.stderr or "")
        + (getattr(result, "output", "") or "")
    )
    assert "srsran" in combined.lower() or "binary" in combined.lower()


def test_scan_with_pending_parser_emits_table(monkeypatch: pytest.MonkeyPatch) -> None:
    """Substitute the parser so we can assert on the rendered output."""
    from src.domain.enums import Band, BandwidthMHz
    from src.domain.models import LTECell
    from src.services.srsran_runner import SrsranResult

    class _CapturingParser:
        def parse(self, stdout):  # noqa: ARG002
            return [
                LTECell(
                    frequency_mhz=869.5,
                    earfcn=2405,
                    band=Band.BAND_5,
                    bandwidth_mhz=BandwidthMHz.BW_10,
                    pci=42,
                    cell_id=12345,
                    tac=1,
                    mcc=510,
                    mnc=10,
                )
            ]

    def _fake_run(self, *, band, gain_db, timeout_seconds):
        return SrsranResult(
            returncode=0,
            stdout="raw",
            stderr="",
            command=("cell_search", "-b", "8"),
        )

    monkeypatch.setattr(
        "src.services.srsran_runner.SrsranRunner.run_cell_search",
        _fake_run,
    )

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        import shutil
        data_dir = Path(tmp) / "data"
        data_dir.mkdir()
        shutil.copy2(Path("data/operators.json"), data_dir / "operators.json")
        config = Path(tmp) / "cfg.toml"
        export_dir = (Path(tmp) / "out").as_posix()
        config.write_text(
            f"""
[device]
index = 0
[scan]
default_frequency_mhz = 869.5
default_band = 8
gain_db = 42.0
timeout_seconds = 1
retry_count = 0
[output]
format = "table"
export_dir = "{export_dir}"
[logging]
level = "WARNING"
file = ""
[srsran]
binary_path = ""
""",
            encoding="utf-8",
        )
        import os
        cwd = os.getcwd()
        try:
            os.chdir(tmp)
            result = runner.invoke(
                app, ["scan", "--config", str(config)],
            )
        finally:
            os.chdir(cwd)
    assert result.exit_code == 0, (result.stdout or "") + (result.stderr or "")
    assert "LTE Cell Discovery" in result.stdout


def test_export_writes_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """End-to-end-ish: parser provides a cell, exporter writes JSON."""
    from src.application.scanner import ScanOutcome
    from src.domain.enums import Band, BandwidthMHz
    from src.domain.models import LTECell

    monkeypatch.setattr(
        "src.application.scanner.ScanService.run",
        lambda self, request: ScanOutcome(cells=[
            LTECell(
                frequency_mhz=869.5,
                earfcn=2405,
                band=Band.BAND_5,
                bandwidth_mhz=BandwidthMHz.BW_10,
                pci=1,
                cell_id=1,
                tac=1,
                mcc=510,
                mnc=10,
            )
        ], raw_stdout="raw", raw_stderr="", returncode=0),
    )

    import shutil
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    shutil.copy2(Path("data/operators.json"), data_dir / "operators.json")
    config = tmp_path / "cfg.toml"
    export_dir = (tmp_path / "exports").as_posix()
    config.write_text(
        f"""
[device]
index = 0
[scan]
default_frequency_mhz = 869.5
default_band = 8
gain_db = 42.0
timeout_seconds = 1
retry_count = 0
[output]
format = "json"
export_dir = "{export_dir}"
[logging]
level = "WARNING"
file = ""
[srsran]
binary_path = ""
""",
        encoding="utf-8",
    )
    import os
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = runner.invoke(
            app,
            [
                "export",
                "--config",
                str(config),
                "result.json",
            ],
        )
    finally:
        os.chdir(cwd)
    assert result.exit_code == 0, (result.stdout or "") + (result.stderr or "")
    assert "Wrote" in result.stdout
    exported = tmp_path / "exports" / "result.json"
    assert exported.exists()
    assert "869.5" in exported.read_text(encoding="utf-8")


def test_export_rejects_unknown_suffix(tmp_path: Path) -> None:
    config = tmp_path / "cfg.toml"
    config.write_text("""[scan]
default_frequency_mhz = 869.5
default_band = 8
gain_db = 42.0
timeout_seconds = 1
""", encoding="utf-8")
    result = runner.invoke(
        app,
        ["export", "--config", str(config), "out.xml"],
    )
    assert result.exit_code != 0


# ---- option helpers ----------------------------------------------------------


def test_band_option_accepts_known_band() -> None:
    assert _band_option("5") == 5
    assert _band_option("Band 5") == 5


def test_band_option_rejects_unknown() -> None:
    import typer

    with pytest.raises(typer.BadParameter, match="Unsupported band"):
        _band_option("999")


def test_format_option_returns_enum() -> None:
    assert _format_option("json") is OutputFormat.JSON
    assert _format_option("CSV") is OutputFormat.CSV


def test_format_option_rejects_unknown() -> None:
    import typer

    with pytest.raises(typer.BadParameter, match="Unsupported format"):
        _format_option("xml")
