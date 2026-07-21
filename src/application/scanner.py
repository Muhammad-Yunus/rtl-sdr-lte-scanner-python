"""Top-level scan workflow.

The application layer owns the *order* of work but delegates each step:

* :class:`SrsranRunner` launches the srsRAN process
* :class:`CellParser` converts raw stdout into :class:`LTECell`
* :class:`OperatorResolver` annotates cells with operator/country

It never reads files, formats output, or parses LTE itself — those belong to
the services layer.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from ..domain.models import LTECell
from ..services.operator_resolver import OperatorResolver
from ..services.srsran_runner import SrsranResult, SrsranRunner

_LOG = logging.getLogger(__name__)


class CellParser(Protocol):
    """Anything that can convert raw srsRAN stdout into cells."""

    def parse(self, stdout: str) -> list[LTECell]: ...


@dataclass(frozen=True, slots=True)
class ScanRequest:
    """User intent for one scan run."""

    band: int
    gain_db: float
    timeout_seconds: float
    frames: int | None = None
    earfcn_start: int | None = None
    earfcn_end: int | None = None
    multi_pass: bool = False


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
            band=request.band,
            gain_db=request.gain_db,
            timeout_seconds=request.timeout_seconds,
            earfcn_start=request.earfcn_start,
            earfcn_end=request.earfcn_end,
            frames=request.frames,
        )
        cells = self._parser.parse(result.stdout)
        enriched = [self._resolver.enrich(c) for c in cells]
        return ScanOutcome(
            cells=enriched,
            raw_stdout=result.stdout,
            raw_stderr=result.stderr,
            returncode=result.returncode,
        )

    def run_multi_pass(
        self,
        band: int,
        gain_db: float,
        timeout_seconds: float,
        quick_frames: int = 10,
        deep_frames: int = 500,
    ) -> ScanOutcome:
        """Two-pass scan: quick scan → detect cells → deep scan on band.

        Pass 1 (quick): low frame count, finds active EARFCNs fast.
        Pass 2 (deep): full band scan with high frame count for accurate RSRP.
        """
        _LOG.info(
            "Pass 1/2: quick scan band %d (n=%d) ...", band, quick_frames
        )
        quick_result = self._runner.run_cell_search(
            band=band,
            gain_db=gain_db,
            timeout_seconds=timeout_seconds,
            frames=quick_frames,
        )
        quick_cells = self._parser.parse(quick_result.stdout)
        if not quick_cells:
            _LOG.info("Pass 1: no cells found, skipping deep scan.")
            return ScanOutcome(
                cells=[],
                raw_stdout=quick_result.stdout,
                raw_stderr=quick_result.stderr,
                returncode=quick_result.returncode,
            )

        _LOG.info(
            "Pass 1: found %d cell(s). Pass 2/2: deep scan band %d (n=%d) ...",
            len(quick_cells),
            band,
            deep_frames,
        )
        deep_result = self._runner.run_cell_search(
            band=band,
            gain_db=gain_db,
            timeout_seconds=timeout_seconds,
            frames=deep_frames,
        )
        deep_cells = self._parser.parse(deep_result.stdout)
        enriched = [self._resolver.enrich(c) for c in deep_cells]
        _LOG.info("Pass 2: %d cell(s) after deep scan.", len(deep_cells))
        return ScanOutcome(
            cells=enriched,
            raw_stdout=deep_result.stdout,
            raw_stderr=deep_result.stderr,
            returncode=deep_result.returncode,
        )


def run_band_sweep(
    service: ScanService,
    bands: list[int],
    gain_db: float,
    timeout_seconds: float,
    *,
    multi_pass: bool = False,
    quick_frames: int = 10,
    deep_frames: int = 500,
    frames: int | None = None,
) -> dict[int, ScanOutcome]:
    """Scan multiple bands sequentially. Returns band→outcome mapping."""
    outcomes: dict[int, ScanOutcome] = {}
    for band in bands:
        _LOG.info("=== Scanning Band %d ===", band)
        if multi_pass:
            outcome = service.run_multi_pass(
                band=band,
                gain_db=gain_db,
                timeout_seconds=timeout_seconds,
                quick_frames=quick_frames,
                deep_frames=deep_frames,
            )
        else:
            request = ScanRequest(
                band=band,
                gain_db=gain_db,
                timeout_seconds=timeout_seconds,
                frames=frames,
            )
            outcome = service.run(request)
        outcomes[band] = outcome
    return outcomes


__all__ = [
    "CellParser",
    "ScanOutcome",
    "ScanRequest",
    "ScanService",
    "run_band_sweep",
]
