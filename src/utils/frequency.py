"""LTE frequency helpers.

All conversions follow 3GPP TS 36.101 Table 5.7.3-1. Only the bands declared in
``src.domain.enums.Band`` are supported; out-of-range EARFCN values raise
:class:`ValueError` with actionable messages instead of silently producing a
wrong number.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..domain.enums import Band, BandwidthMHz


@dataclass(frozen=True, slots=True)
class EarfcnRange:
    """Per-band EARFCN window with the offset used to compute DL frequency."""

    min_earfcn: int
    max_earfcn: int
    offset_earfcn: int  # the EARFCN that maps to 0 MHz from the formula base
    base_mhz: float  # frequency in MHz corresponding to offset_earfcn


# Lookup table keyed by LTE Band number.
# References: 3GPP TS 36.101 Table 5.7.3-1.
_EARFCN_TABLE: dict[int, EarfcnRange] = {
    3: EarfcnRange(min_earfcn=1200, max_earfcn=1949, offset_earfcn=1200, base_mhz=1805.0),
    5: EarfcnRange(min_earfcn=2400, max_earfcn=2649, offset_earfcn=2400, base_mhz=869.0),
    7: EarfcnRange(min_earfcn=2750, max_earfcn=3449, offset_earfcn=2750, base_mhz=2620.0),
    8: EarfcnRange(min_earfcn=3450, max_earfcn=3799, offset_earfcn=3450, base_mhz=925.0),
    20: EarfcnRange(min_earfcn=6150, max_earfcn=6449, offset_earfcn=6150, base_mhz=791.0),
    28: EarfcnRange(min_earfcn=7030, max_earfcn=7739, offset_earfcn=7030, base_mhz=758.0),
    38: EarfcnRange(min_earfcn=37750, max_earfcn=38249, offset_earfcn=37750, base_mhz=2570.0),
    40: EarfcnRange(min_earfcn=38650, max_earfcn=39649, offset_earfcn=38650, base_mhz=2300.0),
}


def _range_for(band: Band) -> EarfcnRange:
    try:
        return _EARFCN_TABLE[int(band)]
    except KeyError as exc:
        raise ValueError(
            f"Band {int(band)} is not supported by the frequency helper. "
            "Extend _EARFCN_TABLE in src/utils/frequency.py to add it."
        ) from exc


def earfcn_to_mhz(earfcn: int, band: Band) -> float:
    """Convert a downlink EARFCN to the carrier frequency in MHz."""
    if not isinstance(earfcn, int):
        raise TypeError(f"EARFCN must be an int, got {type(earfcn).__name__}")
    rng = _range_for(band)
    if not (rng.min_earfcn <= earfcn <= rng.max_earfcn):
        raise ValueError(
            f"EARFCN {earfcn} is outside the valid range for {band.label}: "
            f"[{rng.min_earfcn}, {rng.max_earfcn}]"
        )
    return rng.base_mhz + 0.1 * (earfcn - rng.offset_earfcn)


def mhz_to_earfcn(frequency_mhz: float, band: Band) -> int:
    """Convert a downlink frequency in MHz back to its EARFCN."""
    if not isinstance(frequency_mhz, (int, float)):
        raise TypeError(
            f"frequency_mhz must be numeric, got {type(frequency_mhz).__name__}"
        )
    rng = _range_for(band)
    if frequency_mhz < rng.base_mhz:
        raise ValueError(
            f"{frequency_mhz} MHz is below {band.label} downlink start "
            f"({rng.base_mhz} MHz)."
        )
    earfcn = round((frequency_mhz - rng.base_mhz) * 10.0) + rng.offset_earfcn
    if not (rng.min_earfcn <= earfcn <= rng.max_earfcn):
        raise ValueError(
            f"{frequency_mhz} MHz does not map to a valid EARFCN in {band.label}: "
            f"computed {earfcn}, expected [{rng.min_earfcn}, {rng.max_earfcn}]"
        )
    return earfcn


def bandwidth_to_prb(bandwidth: BandwidthMHz) -> int:
    """Return the number of resource blocks for a given channel bandwidth."""
    table: dict[BandwidthMHz, int] = {
        BandwidthMHz.BW_1_4: 6,
        BandwidthMHz.BW_3: 15,
        BandwidthMHz.BW_5: 25,
        BandwidthMHz.BW_10: 50,
        BandwidthMHz.BW_15: 75,
        BandwidthMHz.BW_20: 100,
    }
    return table[bandwidth]