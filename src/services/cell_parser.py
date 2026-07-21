"""Parser untuk output teks dari ``lte_cell_search`` binary.

Format output yang diharapkan::

    Found CELL 930.0 MHz, EARFCN=3500, PHYID=2, 50 PRB, 1 ports, PSS power=-21.3 dBm
    Found CELL 945.5 MHz, EARFCN=3655, PHYID=0, 75 PRB, 2 ports, PSS power=-26.6 dBm

Baris yang diawali ``Found CELL ID`` (tanpa frekuensi) diabaikan karena
hanya berisi PSS detection tanpa informasi frekuensi/EARFCN.
"""

from __future__ import annotations

import logging
import re

from ..domain.enums import Band, BandwidthMHz
from ..domain.exceptions import ParseError
from ..domain.models import LTECell
from ..utils.frequency import earfcn_to_mhz

logger = logging.getLogger(__name__)

# Regex untuk baris "Found CELL <freq> MHz, EARFCN=<earfcn>, PHYID=<pci>,
# <prb> PRB, <ports> ports, PSS power=<power> dBm"
_CELL_RE = re.compile(
    r"Found\s+CELL\s+"
    r"(?P<freq>[\d.]+)\s+MHz,"
    r"\s+EARFCN=(?P<earfcn>\d+),"
    r"\s+PHYID=(?P<pci>\d+),"
    r"\s+(?P<prb>\d+)\s+PRB,"
    r"\s+(?P<ports>\d+)\s+ports,"
    r"\s+PSS\s+power=(?P<power>[+-]?[\d.]+)\s+dBm"
)

# PRB → BandwidthMHz mapping berdasarkan 3GPP TS 36.101 Table 5.5-1.
# catatan: enum BandwidthMHz menggunakan value integer (1,3,5,10,15,20).
_PRB_TO_BW: dict[int, BandwidthMHz] = {
    6: BandwidthMHz.BW_1_4,
    15: BandwidthMHz.BW_3,
    25: BandwidthMHz.BW_5,
    50: BandwidthMHz.BW_10,
    75: BandwidthMHz.BW_15,
    100: BandwidthMHz.BW_20,
}


def _band_for_earfcn(earfcn: int) -> Band | None:
    """Determine the LTE band from an EARFCN value.

    Returns ``None`` when the EARFCN falls outside every known band range.
    """
    for band in Band:
        try:
            _ = earfcn_to_mhz(earfcn, band)
            return band
        except (ValueError, TypeError):
            continue
    return None


def _band_for_frequency(freq_mhz: float) -> Band | None:
    """Determine the LTE band from a downlink frequency in MHz.

    Returns ``None`` when the frequency falls outside every known band range.
    """
    for band in Band:
        from ..utils.frequency import _EARFCN_TABLE

        rng = _EARFCN_TABLE.get(int(band))
        if rng is None:
            continue
        if rng.base_mhz <= freq_mhz <= rng.base_mhz + 0.1 * (rng.max_earfcn - rng.offset_earfcn):
            return band
    return None


class SrsranCellParser:
    """Parse output dari ``lte_cell_search`` menjadi list :class:`LTECell`."""

    def parse(self, stdout: str) -> list[LTECell]:
        cells: list[LTECell] = []
        for line in stdout.splitlines():
            line = line.strip()
            m = _CELL_RE.match(line)
            if m is None:
                continue
            cell = _parse_matched_line(m)
            if cell is not None:
                cells.append(cell)
        logger.info("Parsed %d cell(s) from srsRAN output", len(cells))
        return cells


def _parse_matched_line(m: re.Match[str]) -> LTECell | None:
    """Convert a regex match into an :class:`LTECell`, or ``None`` on error."""
    try:
        freq_mhz = float(m.group("freq"))
        earfcn = int(m.group("earfcn"))
        pci = int(m.group("pci"))
        prb = int(m.group("prb"))
        power = float(m.group("power"))
    except (ValueError, TypeError) as exc:
        logger.warning("Failed to parse cell fields: %s", exc)
        raise ParseError(f"Invalid cell data in srsRAN output: {exc}") from exc

    bandwidth = _PRB_TO_BW.get(prb)
    if bandwidth is None:
        if prb > 100:
            logger.info("PRB %d exceeds 3GPP max (100), clamping to BW_20", prb)
            bandwidth = BandwidthMHz.BW_20
        else:
            logger.warning("Unknown PRB count %d, defaulting to BW_10", prb)
            bandwidth = BandwidthMHz.BW_10

    # Prefer band dari EARFCN, fallback ke frequency.
    band = _band_for_earfcn(earfcn) or _band_for_frequency(freq_mhz)
    if band is None:
        logger.warning(
            "Cannot determine band for EARFCN=%d, freq=%.1f MHz — defaulting to Band 8",
            earfcn,
            freq_mhz,
        )
        band = Band.BAND_8

    rsrp = int(round(power)) if power != 0 else None

    return LTECell(
        frequency_mhz=freq_mhz,
        earfcn=earfcn,
        band=band,
        bandwidth_mhz=bandwidth,
        pci=pci,
        rsrp=rsrp,
    )


__all__ = ["SrsranCellParser"]
