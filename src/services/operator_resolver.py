"""Resolve operator identity from cell data.

Two lookup strategies are tried in order:

1. **MCC/MNC** — direct match from the operator database (requires MIB/SIB
   decode, which ``lte_cell_search`` does not provide).
2. **EARFCN range** — maps the cell's EARFCN to a known operator using
   the frequency-band allocation table.  This works because spectrum
   allocations are public and fixed per region.

The resolver is intentionally a thin layer so callers can substitute a
different backend without touching the cell-processing pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..domain.models import LTECell, OperatorEntry
from ..repository.frequency_band_db import FrequencyBandDatabase
from ..repository.operator_db import OperatorDatabase


@dataclass(frozen=True, slots=True)
class ResolvedOperator:
    """Result of resolving an operator identity."""

    operator: str
    country: str


class OperatorResolver:
    def __init__(
        self,
        database: OperatorDatabase,
        frequency_band_db: FrequencyBandDatabase | None = None,
    ) -> None:
        self._db = database
        self._freq_db = frequency_band_db or FrequencyBandDatabase([])

    def resolve(self, mcc: int, mnc: int) -> ResolvedOperator | None:
        entry: OperatorEntry | None = self._db.lookup(mcc, mnc)
        if entry is None:
            return None
        return ResolvedOperator(operator=entry.operator, country=entry.country)

    def resolve_by_frequency(self, earfcn: int, band: int) -> ResolvedOperator | None:
        entry = self._freq_db.lookup(earfcn, band)
        if entry is None:
            return None
        return ResolvedOperator(operator=entry.operator, country=entry.country)

    def enrich(self, cell: LTECell) -> LTECell:
        """Return a copy of ``cell`` with operator and country filled in.

        Strategy:
        1. If operator already set, return unchanged.
        2. Try MCC/MNC lookup.
        3. Fallback to EARFCN/frequency-based lookup.
        """
        if cell.operator is not None and cell.country is not None:
            return cell

        # Strategy 1: MCC/MNC lookup (when available)
        if cell.mcc is not None and cell.mnc is not None:
            resolved = self.resolve(cell.mcc, cell.mnc)
            if resolved is not None:
                return cell.with_operator(resolved.operator, resolved.country)

        # Strategy 2: Frequency-band EARFCN lookup
        resolved = self.resolve_by_frequency(cell.earfcn, int(cell.band.value))
        if resolved is not None:
            return cell.with_operator(resolved.operator, resolved.country)

        return cell
