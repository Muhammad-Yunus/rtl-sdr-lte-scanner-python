"""Tests for src/application/scanner.py."""

from __future__ import annotations

import os
from pathlib import Path

from src.application.scanner import ScanRequest, ScanService
from src.domain.enums import Band, BandwidthMHz
from src.domain.models import LTECell
from src.repository.operator_db import OperatorDatabase
from src.services.operator_resolver import OperatorResolver
from src.services.srsran_runner import SrsranResult, SrsranRunner

FIXTURE_DB = Path(__file__).parent / "fixtures" / "operators.json"


class _StubParser:
    """Returns a fixed list of cells regardless of stdout."""

    def __init__(self, cells: list[LTECell]) -> None:
        self._cells = cells
        self.last_stdout: str | None = None

    def parse(self, stdout: str) -> list[LTECell]:
        self.last_stdout = stdout
        return list(self._cells)


class _FakeRunner:
    def __init__(self, stdout: str = "raw", stderr: str = "", returncode: int = 0) -> None:
        self._stdout = stdout
        self._stderr = stderr
        self._returncode = returncode
        self.calls: list[dict] = []

    def run(self, command, *, timeout_seconds, env=None):
        # The runner stores the command we built; we don't introspect it here.
        self.calls.append(
            {
                "command": tuple(command),
                "timeout": timeout_seconds,
            }
        )
        return SrsranResult(
            returncode=self._returncode,
            stdout=self._stdout,
            stderr=self._stderr,
            command=tuple(command),
        )


def _make_service(runner, cells):
    resolver = OperatorResolver(OperatorDatabase.from_json(FIXTURE_DB))
    parser = _StubParser(cells)
    srsran_runner = SrsranRunner(Path("/fake/srsran"), runner)  # type: ignore[arg-type]
    srsran_runner = srsran_runner.with_resolved_binary("/fake/srsran")
    return ScanService(runner=srsran_runner, parser=parser, resolver=resolver)


def _request() -> ScanRequest:
    return ScanRequest(
        frequency_mhz=869.5,
        bandwidth=BandwidthMHz.BW_10,
        device_index=0,
        timeout_seconds=10.0,
    )


def test_run_enriches_cells_with_operator() -> None:
    cells = [
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
    ]
    fake = _FakeRunner(stdout="raw output", stderr="")
    service = _make_service(fake, cells)
    outcome = service.run(_request())
    assert len(outcome.cells) == 1
    assert outcome.cells[0].operator == "Telkomsel"
    assert outcome.cells[0].country == "Indonesia"


def test_run_returns_raw_output() -> None:
    fake = _FakeRunner(stdout="hello", stderr="some error", returncode=1)
    service = _make_service(fake, [])
    outcome = service.run(_request())
    assert outcome.raw_stdout == "hello"
    assert outcome.raw_stderr == "some error"
    assert outcome.returncode == 1


def test_run_passes_through_unknown_mcc() -> None:
    cells = [
        LTECell(
            frequency_mhz=900.0,
            earfcn=3450,
            band=Band.BAND_8,
            bandwidth_mhz=BandwidthMHz.BW_10,
            pci=1,
            cell_id=1,
            tac=1,
            mcc=999,
            mnc=99,
        )
    ]
    fake = _FakeRunner()
    service = _make_service(fake, cells)
    outcome = service.run(_request())
    assert outcome.cells[0].operator is None


def test_run_returns_empty_when_parser_empty() -> None:
    fake = _FakeRunner()
    service = _make_service(fake, [])
    outcome = service.run(_request())
    assert outcome.cells == []


def test_run_invokes_runner_with_correct_request() -> None:
    fake = _FakeRunner()
    service = _make_service(fake, [])
    req = ScanRequest(
        frequency_mhz=1800.0,
        bandwidth=BandwidthMHz.BW_20,
        device_index=1,
        timeout_seconds=42.0,
    )
    service.run(req)
    assert fake.calls, "runner should have been called"
    call = fake.calls[0]
    assert call["timeout"] == 42.0
    assert call["command"][0].endswith("fake" + os.sep + "srsran") or call["command"][0] == "/fake/srsran"