"""Top-level scan workflow.

The application layer owns the *order* of work but delegates each step:

* :class:`SrsranRunner` launches the srsRAN process
* :class:`CellParser` converts raw stdout into :class:`LTECell`
* :class:`OperatorResolver` annotates cells with operator/country

It never reads files, formats output, or parses LTE itself — those belong to
the services layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..domain.enums import BandwidthMHz
from ..domain.models import LTECell
from ..services.operator_resolver import OperatorResolver
from ..services.srsran_runner import SrsranResult, SrsranRunner


class CellParser(Protocol):
    """Anything that can convert raw srsRAN stdout into cells."""

    def parse(self, stdout: str) -> list[LTECell]: ...


@dataclass(frozen=True, slots=True)
class ScanRequest:
    """User intent for one scan run."""

    frequency_mhz: float
    bandwidth: BandwidthMHz
    device_index: int
    timeout_seconds: float


@dataclass(frozen=True, slots=True)
class ScanOutcome:
    """Result of one scan run, ready for the formatter."""

    cells: list[LTECell]
    raw_stdout: str
    raw_stderr: str
    returncode: int


class ScanService:
    """Compose runner + parser + resolver into a single high-level call."""

    def __init__(
        self,
        runner: SrsranRunner,
        parser: CellParser,
        resolver: OperatorResolver,
    ) -> None:
        self._runner = runner
        self._parser = parser
        self._resolver = resolver

    def run(self, request: ScanRequest) -> ScanOutcome:
        result: SrsranResult = self._runner.run_cell_search(
            frequency_mhz=request.frequency_mhz,
            bandwidth=request.bandwidth,
            device_index=request.device_index,
            timeout_seconds=request.timeout_seconds,
        )
        cells = self._parser.parse(result.stdout)
        enriched = [self._resolver.enrich(c) for c in cells]
        return ScanOutcome(
            cells=enriched,
            raw_stdout=result.stdout,
            raw_stderr=result.stderr,
            returncode=result.returncode,
        )


__all__ = ["CellParser", "ScanOutcome", "ScanRequest", "ScanService"]