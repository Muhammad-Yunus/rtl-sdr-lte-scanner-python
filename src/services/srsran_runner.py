"""Subprocess wrapper around the srsRAN binary.

This module does *not* interpret srsRAN output.  Its job is to launch the
process with the right arguments and capture stdout/stderr for the parser
to consume later.

The ``cell_search`` binary accepts ``-b <band>``, ``-g <gain>``,
``-s <earfcn_start>``, ``-e <earfcn_end>``, ``-n <frames>`` flags.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol, Sequence

from ..domain.exceptions import ScanTimeoutError, SrsranMissingError


@dataclass(frozen=True, slots=True)
class SrsranResult:
    """Raw output of one srsRAN invocation."""

    returncode: int
    stdout: str
    stderr: str
    command: tuple[str, ...]


class ProcessRunner(Protocol):
    """Anything that can launch a subprocess. Defined for testability."""

    def run(
        self,
        command: Sequence[str],
        *,
        timeout_seconds: float,
        env: Mapping[str, str] | None = None,
    ) -> SrsranResult: ...


def build_cell_search_args(
    binary: str,
    *,
    band: int,
    gain_db: float = 42.0,
    earfcn_start: int | None = None,
    earfcn_end: int | None = None,
    frames: int | None = None,
    extra: Sequence[str] = (),
) -> list[str]:
    """Compose the argv for ``lte_cell_search``.

    Matches the real srsRAN CLI::

        cell_search -b <band> -g <gain> [-s earfcn_start] [-e earfcn_end] [-n frames]
    """
    args = [
        binary,
        "-b",
        str(band),
        "-g",
        f"{gain_db:.1f}",
    ]
    if earfcn_start is not None:
        args.extend(["-s", str(earfcn_start)])
    if earfcn_end is not None:
        args.extend(["-e", str(earfcn_end)])
    if frames is not None:
        args.extend(["-n", str(frames)])
    args.extend(extra)
    return args


class SubprocessRunner:
    """Concrete runner backed by :mod:`subprocess`."""

    def run(
        self,
        command: Sequence[str],
        *,
        timeout_seconds: float,
        env: Mapping[str, str] | None = None,
    ) -> SrsranResult:
        try:
            completed = subprocess.run(
                list(command),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
                env=env,
            )
        except subprocess.TimeoutExpired as exc:
            raise ScanTimeoutError(
                f"srsRAN timed out after {timeout_seconds}s: {exc.cmd!r}"
            ) from exc
        except FileNotFoundError as exc:
            raise SrsranMissingError(
                f"srsRAN binary not found: {exc.filename!r}. "
                "Set [srsran].binary_path in configs/config.toml or add it to PATH."
            ) from exc
        return SrsranResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            command=tuple(command),
        )


class SrsranRunner:
    """High-level helper that resolves the binary path and runs srsRAN."""

    def __init__(
        self,
        configured_binary: Path,
        process_runner: ProcessRunner,
        *,
        trust_resolved_binary: bool = False,
    ) -> None:
        self._configured_binary = configured_binary
        self._runner = process_runner
        self._trust_resolved_binary = trust_resolved_binary

    def resolve_binary(self) -> str:
        if self._trust_resolved_binary:
            if self._configured_binary == Path():
                raise SrsranMissingError(
                    "trust_resolved_binary=True requires a non-empty path."
                )
            return str(self._configured_binary)
        configured = self._configured_binary
        if configured != Path():
            if not configured.exists():
                raise SrsranMissingError(
                    f"Configured srsRAN binary does not exist: {configured}. "
                    "Update configs/config.toml or install srsRAN."
                )
            return str(configured)
        located = shutil.which("srsran") or shutil.which("srslte")
        if located is None:
            raise SrsranMissingError(
                "srsRAN binary not found on PATH. Set [srsran].binary_path in "
                "configs/config.toml or install srsRAN."
            )
        return located

    def run_cell_search(
        self,
        *,
        band: int,
        gain_db: float,
        timeout_seconds: float,
        earfcn_start: int | None = None,
        earfcn_end: int | None = None,
        frames: int | None = None,
    ) -> SrsranResult:
        binary = self.resolve_binary()
        argv = build_cell_search_args(
            binary,
            band=band,
            gain_db=gain_db,
            earfcn_start=earfcn_start,
            earfcn_end=earfcn_end,
            frames=frames,
        )
        return self._runner.run(argv, timeout_seconds=timeout_seconds)

    def with_resolved_binary(self, binary: str) -> "SrsranRunner":
        """Return a copy that uses ``binary`` directly, skipping PATH lookup."""
        clone = SrsranRunner(self._configured_binary, self._runner)
        object.__setattr__(clone, "_configured_binary", Path(binary))
        object.__setattr__(clone, "_trust_resolved_binary", True)
        return clone


__all__ = [
    "ProcessRunner",
    "SrsranResult",
    "SrsranRunner",
    "SubprocessRunner",
    "build_cell_search_args",
]
