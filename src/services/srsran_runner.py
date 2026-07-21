"""Subprocess wrapper around the srsRAN binary.

This module does *not* interpret srsRAN output. Its job is to launch the
process with the right arguments and capture stdout/stderr for the parser
to consume later.

Argument construction lives in :func:`build_cell_search_args` so it can be
swapped without touching process management once the real srsRAN CLI is
known.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol, Sequence

from ..domain.enums import BandwidthMHz
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
    frequency_mhz: float,
    bandwidth: BandwidthMHz,
    device_index: int,
    extra: Sequence[str] = (),
) -> list[str]:
    """Compose the argv for an srsRAN cell-search invocation.

    The exact flag set is intentionally generic; callers may append
    ``extra`` for vendor-specific flags. Update this function once the real
    srsRAN CLI is wired up against a real device.
    """
    return [
        binary,
        "cell_search",
        "--freq",
        f"{frequency_mhz:.3f}",
        "--bw",
        str(int(bandwidth.value)),
        "--device",
        str(device_index),
        *extra,
    ]


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
    """High-level helper that resolves the binary path and runs srsRAN.

    Pass ``binary_path=""`` to defer to ``shutil.which`` (the production
    behaviour). Tests can pass an existing fake binary string to skip
    resolution entirely.
    """

    def __init__(
        self,
        configured_binary: Path,
        process_runner: ProcessRunner,
        *,
        trust_resolved_binary: bool = False,
    ) -> None:
        self._configured_binary = configured_binary
        self._runner = process_runner
        # When True, ``resolve_binary`` skips existence/PATH lookup and
        # uses ``configured_binary`` verbatim. Intended for tests.
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
        frequency_mhz: float,
        bandwidth: BandwidthMHz,
        device_index: int,
        timeout_seconds: float,
    ) -> SrsranResult:
        binary = self.resolve_binary()
        argv = build_cell_search_args(
            binary,
            frequency_mhz=frequency_mhz,
            bandwidth=bandwidth,
            device_index=device_index,
        )
        return self._runner.run(argv, timeout_seconds=timeout_seconds)

    def with_resolved_binary(self, binary: str) -> "SrsranRunner":
        """Return a copy that uses ``binary`` directly, skipping PATH lookup.

        Intended for tests and for callers that have already verified the
        binary location out-of-band.
        """
        clone = SrsranRunner(self._configured_binary, self._runner)
        object.__setattr__(clone, "_configured_binary", Path(binary))
        object.__setattr__(clone, "_trust_resolved_binary", True)
        return clone


__all__ = [
    "BandwidthMHz",
    "ProcessRunner",
    "SrsranResult",
    "SrsranRunner",
    "SubprocessRunner",
    "build_cell_search_args",
]
