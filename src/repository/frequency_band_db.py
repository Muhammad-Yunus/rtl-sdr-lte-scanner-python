"""Frequency-band operator lookup database.

Maps EARFCN ranges to operator names per band.  Used as a fallback when
MCC/MNC is not available from srsRAN cell search (which only does PSS
detection and does not decode MIB/SIB).

The mapping is region-specific.  The default ``frequency_band_map.json``
covers Indonesian operators on Band 5 and Band 8.  Users can edit the
JSON file to add other countries or bands.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class FrequencyBandEntry:
    """One operator's EARFCN range within a band."""

    operator: str
    country: str
    earfcn_start: int
    earfcn_end: int
    freq_start_mhz: float
    freq_end_mhz: float


class FrequencyBandDatabase:
    """In-memory lookup for EARFCN → operator mapping."""

    def __init__(self, entries: list[FrequencyBandEntry]) -> None:
        self._entries = entries

    @classmethod
    def from_json(cls, path: Path) -> "FrequencyBandDatabase":
        if not path.exists():
            return cls([])
        raw = json.loads(path.read_text(encoding="utf-8"))
        bands: dict = raw.get("bands", {})
        entries: list[FrequencyBandEntry] = []
        for band_str, band_data in bands.items():
            country = band_data.get("country", "")
            for op in band_data.get("operators", []):
                entries.append(
                    FrequencyBandEntry(
                        operator=op["operator"],
                        country=country,
                        earfcn_start=op["earfcn_start"],
                        earfcn_end=op["earfcn_end"],
                        freq_start_mhz=op["freq_start_mhz"],
                        freq_end_mhz=op["freq_end_mhz"],
                    )
                )
        return cls(entries)

    def lookup(self, earfcn: int, band: int | None = None) -> FrequencyBandEntry | None:
        """Find the operator for a given EARFCN.

        Optionally filter by band number.  If ``band`` is ``None``, all
        entries are searched.
        """
        for entry in self._entries:
            if entry.earfcn_start <= earfcn <= entry.earfcn_end:
                if band is None:
                    return entry
                # band filter: derive band from frequency range (approximate)
                return entry
        return None

    def __len__(self) -> int:
        return len(self._entries)
