from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Optional

from .enums import Band, BandwidthMHz


@dataclass(frozen=True, slots=True)
class OperatorEntry:
    """A single row in the local operator database."""

    mcc: int
    mnc: int
    operator: str
    country: str


@dataclass(frozen=True, slots=True)
class LTECell:
    """A single LTE cell as parsed from srsRAN output.

    Immutable; use `dataclasses.replace` to derive a variant.
    """

    frequency_mhz: float
    earfcn: int
    band: Band
    bandwidth_mhz: BandwidthMHz
    pci: int
    cell_id: int
    tac: int
    mcc: int
    mnc: int
    rsrp: Optional[int] = None
    rsrq: Optional[int] = None
    snr: Optional[int] = None
    operator: Optional[str] = None
    country: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def with_operator(self, operator: str, country: str) -> "LTECell":
        """Return a copy with operator/country resolved.

        Kept as a method (not a setter) because the dataclass is frozen.
        """
        return replace(self, operator=operator, country=country)
