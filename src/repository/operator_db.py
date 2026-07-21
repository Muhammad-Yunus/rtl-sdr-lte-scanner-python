"""Loader for the local operator database (``data/operators.json``)."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..domain.exceptions import OperatorLookupError
from ..domain.models import OperatorEntry


class _OperatorRow(BaseModel):
    """Wire-format representation of a row in operators.json."""

    model_config = ConfigDict(extra="forbid")

    mcc: int = Field(ge=0, le=999)
    mnc: int = Field(ge=0, le=999)
    operator: str = Field(min_length=1)
    country: str = Field(min_length=1)


class _OperatorFile(BaseModel):
    """Outer wrapper around the JSON document."""

    model_config = ConfigDict(extra="ignore")

    entries: list[_OperatorRow]


class OperatorDatabase:
    """In-memory operator lookup table.

    The database is loaded eagerly at construction so the first scan does not
    pay the I/O cost and so that missing-file errors surface immediately.
    """

    def __init__(self, entries: list[OperatorEntry]) -> None:
        self._by_key: dict[tuple[int, int], OperatorEntry] = {
            (e.mcc, e.mnc): e for e in entries
        }

    @classmethod
    def from_json(cls, path: Path) -> "OperatorDatabase":
        if not path.exists():
            raise OperatorLookupError(f"Operator database not found: {path}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise OperatorLookupError(f"Cannot read operator database {path}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise OperatorLookupError(
                f"Operator database {path} is not valid JSON: {exc}"
            ) from exc
        try:
            document = _OperatorFile.model_validate(raw)
        except ValidationError as exc:
            raise OperatorLookupError(
                f"Operator database {path} has invalid schema: {exc}"
            ) from exc
        entries = [
            OperatorEntry(
                mcc=row.mcc,
                mnc=row.mnc,
                operator=row.operator,
                country=row.country,
            )
            for row in document.entries
        ]
        return cls(entries)

    def lookup(self, mcc: int, mnc: int) -> OperatorEntry | None:
        return self._by_key.get((mcc, mnc))

    def __len__(self) -> int:
        return len(self._by_key)

    def __contains__(self, key: tuple[int, int]) -> bool:
        return key in self._by_key
