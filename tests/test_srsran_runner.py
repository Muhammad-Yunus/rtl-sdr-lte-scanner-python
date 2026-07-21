"""Tests for src/services/srsran_runner.py."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from src.domain.exceptions import ScanTimeoutError, SrsranMissingError
from src.services.srsran_runner import (
    SrsranResult,
    SrsranRunner,
    build_cell_search_args,
)


class _FakeRunner:
    """Captures the command and returns canned output."""

    def __init__(self, *, result: SrsranResult | None = None,
                 exc: Exception | None = None) -> None:
        self.calls: list[tuple[tuple[str, ...], float]] = []
        self._result = result
        self._exc = exc

    def run(
        self,
        command: Sequence[str],
        *,
        timeout_seconds: float,
        env: Mapping[str, str] | None = None,
    ) -> SrsranResult:
        self.calls.append((tuple(command), timeout_seconds))
        if self._exc is not None:
            raise self._exc
        assert self._result is not None
        return self._result


def test_build_cell_search_args() -> None:
    argv = build_cell_search_args(
        "/home/pi/srsRAN_4G/build/lib/examples/cell_search",
        band=8,
        gain_db=42.0,
    )
    assert argv == [
        "/home/pi/srsRAN_4G/build/lib/examples/cell_search",
        "-b",
        "8",
        "-g",
        "42.0",
    ]


def test_build_cell_search_args_with_earfcn_range() -> None:
    argv = build_cell_search_args(
        "cell_search",
        band=8,
        gain_db=42.0,
        earfcn_start=100,
        earfcn_end=200,
    )
    assert argv == [
        "cell_search",
        "-b",
        "8",
        "-g",
        "42.0",
        "-s",
        "100",
        "-e",
        "200",
    ]


def test_build_cell_search_args_with_frames() -> None:
    argv = build_cell_search_args(
        "cell_search",
        band=5,
        gain_db=45.0,
        frames=500,
    )
    assert argv == [
        "cell_search",
        "-b",
        "5",
        "-g",
        "45.0",
        "-n",
        "500",
    ]


def test_build_cell_search_args_all_options() -> None:
    argv = build_cell_search_args(
        "cell_search",
        band=8,
        gain_db=40.0,
        earfcn_start=100,
        earfcn_end=200,
        frames=50,
    )
    assert argv == [
        "cell_search",
        "-b",
        "8",
        "-g",
        "40.0",
        "-s",
        "100",
        "-e",
        "200",
        "-n",
        "50",
    ]


def test_build_cell_search_args_with_extra() -> None:
    argv = build_cell_search_args(
        "cell_search",
        band=5,
        gain_db=45.5,
        extra=["-s", "2400", "-e", "2649"],
    )
    assert argv == [
        "cell_search",
        "-b",
        "5",
        "-g",
        "45.5",
        "-s",
        "2400",
        "-e",
        "2649",
    ]


def test_runner_uses_configured_binary(tmp_path: Path) -> None:
    fake = _FakeRunner(
        result=SrsranResult(0, "found: cell A", "", ("x",)),
    )
    binpath = tmp_path / "fake-srsran"
    binpath.write_text("", encoding="utf-8")
    runner = SrsranRunner(binpath, fake)  # type: ignore[arg-type]
    out = runner.run_cell_search(
        band=8,
        gain_db=42.0,
        timeout_seconds=12.5,
    )
    assert out.stdout == "found: cell A"
    cmd, timeout = fake.calls[0]
    assert cmd[0] == str(binpath)
    assert timeout == 12.5


def test_runner_falls_back_to_path(tmp_path: Path) -> None:
    """When binary_path is empty, runner queries shutil.which."""
    fake = _FakeRunner()
    runner = SrsranRunner(Path(), fake)  # type: ignore[arg-type]
    try:
        resolved = runner.resolve_binary()
    except SrsranMissingError:
        return  # acceptable — no srsRAN on this PATH
    assert resolved  # non-empty string when found


def test_runner_empty_path_raises_when_no_binary_on_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Force shutil.which to return None for both names."""
    fake = _FakeRunner()
    runner = SrsranRunner(Path(), fake)  # type: ignore[arg-type]
    monkeypatch.setattr("shutil.which", lambda _name: None)
    with pytest.raises(SrsranMissingError, match="not found on PATH"):
        runner.run_cell_search(
            band=8,
            gain_db=42.0,
            timeout_seconds=1.0,
        )


def test_runner_missing_configured_binary(tmp_path: Path) -> None:
    fake = _FakeRunner()
    runner = SrsranRunner(tmp_path / "missing-bin", fake)  # type: ignore[arg-type]
    with pytest.raises(SrsranMissingError, match="does not exist"):
        runner.run_cell_search(
            band=8,
            gain_db=42.0,
            timeout_seconds=1.0,
        )


def test_subprocess_runner_succeeds() -> None:
    """Use the system Python as a stand-in binary so no srsRAN is required."""
    runner = _RealSubprocess()
    result = runner.run(
        [sys_executable(), "-c", "print('hello'); import sys; sys.exit(0)"],
        timeout_seconds=5.0,
    )
    assert result.returncode == 0
    assert "hello" in result.stdout


def test_subprocess_runner_times_out() -> None:
    runner = _RealSubprocess()
    with pytest.raises(ScanTimeoutError, match="timed out"):
        runner.run(
            [sys_executable(), "-c", "import time; time.sleep(5)"],
            timeout_seconds=0.1,
        )


def test_subprocess_runner_missing_binary(tmp_path: Path) -> None:
    runner = _RealSubprocess()
    with pytest.raises(SrsranMissingError, match="not found"):
        runner.run([str(tmp_path / "definitely-not-a-binary")], timeout_seconds=1.0)


def sys_executable() -> str:
    import sys as _s
    return _s.executable


class _RealSubprocess:
    """Minimal real runner so we exercise the subprocess error paths."""

    def run(
        self,
        command: Sequence[str],
        *,
        timeout_seconds: float,
        env: Mapping[str, str] | None = None,
    ) -> SrsranResult:
        from src.services.srsran_runner import SubprocessRunner
        return SubprocessRunner().run(command, timeout_seconds=timeout_seconds, env=env)
