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

from dataclasses import dataclass, replace as dataclass_replace

from ..domain.models import LTECell, OperatorEntry
from ..repository.frequency_band_db import FrequencyBandDatabase
from ..repository.operator_db import OperatorDatabase


# Map operator names (Indonesia) to their MCC/MNC values.
# Used to fill in MCC/MNC when detected via EARCFN/frequency-band lookup.
_OPERATOR_MNC_MAP: dict[str, tuple[int, int]] = {
    "Telkomsel": (510, 10),
    "XL Axiata": (510, 21),
    "Indosat Ooredoo Hutchison": (510, 1),
    "Smartfren": (510, 11),
    "Three Indonesia": (510, 7),
    "Axis": (510, 9),
}


@dataclass(frozen=True, slots=True)
class ResolvedOperator:
    """Result of resolving an operator identity."""

    operator: str
    country: str
    mcc: int | None = None
    mnc: int | None = None


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
        return ResolvedOperator(
            operator=entry.operator,
            country=entry.country,
            mcc=entry.mcc,
            mnc=entry.mnc,
        )

    def resolve_by_frequency(
        self, earfcn: int, band: int
    ) -> ResolvedOperator | None:
        entry = self._freq_db.lookup(earfcn, band)
        if entry is None:
            return None
        # Try to get MCC/MNC from operator name based on the found operator
        mcc: int | None = None
        mnc: int | None = None
        op_name = entry.operator
        if op_name in _OPERATOR_MNC_MAP:
            mcc, mnc = _OPERATOR_MNC_MAP[op_name]
        return ResolvedOperator(
            operator=entry.operator,
            country=entry.country,
            mcc=mcc,
            mnc=mnc,
        )

    def enrich(self, cell: LTECell) -> LTECell:
        """Return a copy of ``cell`` with operator, country, mcc, and mnc filled in.

        Strategy:
        1. If operator/country already set, return unchanged.
        2. Try MCC/MNC lookup — if found, populate both operator and MCC/MNC.
        3. Fallback to EARCFN/frequency-based lookup — populates operator + MCC/MNC from mapping.
        """
        if cell.operator is not None and cell.country is not None:
            return cell

        # Strategy 1: MCC/MNC lookup (when available from srsRAN output)
        if cell.mcc is not None and cell.mnc is not None:
            resolved = self.resolve(cell.mcc, cell.mnc)
            if resolved is not None:
                new_cell = cell.with_operator(resolved.operator, resolved.country)
                if resolved.mcc is not None and resolved.mnc is not None:
                    new_cell = dataclass_replace(new_cell, mcc=resolved.mcc, mnc=resolved.mnc)
                return new_cell

        # Strategy 2: Frequency-band EARCFN lookup
        resolved = self.resolve_by_frequency(
            cell.earfcn, int(cell.band.value)
        )
        if resolved is not None:
            new_cell = cell.with_operator(resolved.operator, resolved.country)
            if resolved.mcc is not None and resolved.mnc is not None:
                new_cell = dataclass_replace(new_cell, mcc=resolved.mcc, mnc=resolved.mnc)
            return new_cell

        return cell
