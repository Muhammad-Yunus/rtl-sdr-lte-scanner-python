"""Resolve MCC/MNC pairs to operator and country.

The resolver is intentionally a thin layer over :class:`OperatorDatabase`.
Keeping the lookup logic separate means callers can substitute a different
backend (e.g. an in-memory cache or a different file format) without touching
the cell-processing pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..domain.models import LTECell, OperatorEntry
from ..repository.operator_db import OperatorDatabase


@dataclass(frozen=True, slots=True)
class ResolvedOperator:
    """Result of resolving a single (mcc, mnc) pair."""

    operator: str
    country: str


class OperatorResolver:
    def __init__(self, database: OperatorDatabase) -> None:
        self._db = database

    def resolve(self, mcc: int, mnc: int) -> ResolvedOperator | None:
        entry: OperatorEntry | None = self._db.lookup(mcc, mnc)
        if entry is None:
            return None
        return ResolvedOperator(operator=entry.operator, country=entry.country)

    def enrich(self, cell: LTECell) -> LTECell:
        """Return a copy of ``cell`` with operator and country filled in.

        If the (mcc, mnc) pair is unknown the original cell is returned
        unchanged — caller decides whether missing data is an error.
        """
        if cell.operator is not None and cell.country is not None:
            return cell
        resolved = self.resolve(cell.mcc, cell.mnc)
        if resolved is None:
            return cell
        return cell.with_operator(resolved.operator, resolved.country)
