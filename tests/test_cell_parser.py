"""Tests for src/services/cell_parser.py."""

from __future__ import annotations

from src.domain.enums import Band, BandwidthMHz
from src.services.cell_parser import SrsranCellParser

parser = SrsranCellParser()

# Contoh output nyata dari lte_cell_search
SAMPLE_OUTPUT = """\
Found CELL ID 2. 50 PRB, 1 ports
Found CELL ID 243. 50 PRB, 2 ports
Found CELL ID 416. 50 PRB, 2 ports
Found CELL ID 0. 75 PRB, 2 ports
Found 4 cells
Found CELL 930.0 MHz, EARFCN=3500, PHYID=2, 50 PRB, 1 ports, PSS power=-21.3 dBm
Found CELL 930.1 MHz, EARFCN=3501, PHYID=243, 50 PRB, 2 ports, PSS power=-20.3 dBm
Found CELL 930.1 MHz, EARFCN=3501, PHYID=416, 50 PRB, 2 ports, PSS power=-18.5 dBm
Found CELL 945.5 MHz, EARFCN=3655, PHYID=0, 75 PRB, 2 ports, PSS power=-26.6 dBm
"""


def test_parse_finds_all_cells() -> None:
    cells = parser.parse(SAMPLE_OUTPUT)
    assert len(cells) == 4


def test_parse_extracts_frequency() -> None:
    cells = parser.parse(SAMPLE_OUTPUT)
    assert cells[0].frequency_mhz == 930.0
    assert cells[3].frequency_mhz == 945.5


def test_parse_extracts_earfcn() -> None:
    cells = parser.parse(SAMPLE_OUTPUT)
    assert cells[0].earfcn == 3500
    assert cells[3].earfcn == 3655


def test_parse_extracts_pci() -> None:
    cells = parser.parse(SAMPLE_OUTPUT)
    assert cells[0].pci == 2
    assert cells[1].pci == 243
    assert cells[2].pci == 416
    assert cells[3].pci == 0


def test_parse_extracts_bandwidth_from_prb() -> None:
    cells = parser.parse(SAMPLE_OUTPUT)
    # 50 PRB → BW_10
    assert cells[0].bandwidth_mhz is BandwidthMHz.BW_10
    # 75 PRB → BW_15
    assert cells[3].bandwidth_mhz is BandwidthMHz.BW_15


def test_parse_determines_band_from_earfcn() -> None:
    cells = parser.parse(SAMPLE_OUTPUT)
    # EARFCN 3500 → Band 8
    assert cells[0].band is Band.BAND_8
    # EARFCN 3655 → Band 8
    assert cells[3].band is Band.BAND_8


def test_parse_extracts_rsrp() -> None:
    cells = parser.parse(SAMPLE_OUTPUT)
    assert cells[0].rsrp == -21
    assert cells[3].rsrp == -27


def test_parse_ignores_cell_id_lines() -> None:
    """Lines like 'Found CELL ID 2. 50 PRB, 1 ports' should be ignored."""
    output = "Found CELL ID 42. 50 PRB, 1 ports\n"
    cells = parser.parse(output)
    assert cells == []


def test_parse_ignores_count_line() -> None:
    output = "Found 4 cells\n"
    cells = parser.parse(output)
    assert cells == []


def test_parse_empty_output() -> None:
    cells = parser.parse("")
    assert cells == []


def test_parse_no_match_lines() -> None:
    cells = parser.parse("some random output\nno cells here\n")
    assert cells == []


def test_parse_single_cell() -> None:
    output = "Found CELL 869.5 MHz, EARFCN=2405, PHYID=1, 50 PRB, 2 ports, PSS power=-80.0 dBm\n"
    cells = parser.parse(output)
    assert len(cells) == 1
    cell = cells[0]
    assert cell.frequency_mhz == 869.5
    assert cell.earfcn == 2405
    assert cell.pci == 1
    assert cell.bandwidth_mhz is BandwidthMHz.BW_10
    assert cell.band is Band.BAND_5
    assert cell.rsrp == -80


def test_parse_25_prb_maps_to_bw_5() -> None:
    output = "Found CELL 925.0 MHz, EARFCN=3450, PHYID=5, 25 PRB, 1 ports, PSS power=-90.0 dBm\n"
    cells = parser.parse(output)
    assert cells[0].bandwidth_mhz is BandwidthMHz.BW_5


def test_parse_100_prb_maps_to_bw_20() -> None:
    output = "Found CELL 1800.0 MHz, EARFCN=1200, PHYID=10, 100 PRB, 2 ports, PSS power=-75.0 dBm\n"
    cells = parser.parse(output)
    assert cells[0].bandwidth_mhz is BandwidthMHz.BW_20


def test_parse_6_prb_maps_to_bw_1_4() -> None:
    output = "Found CELL 869.5 MHz, EARFCN=2400, PHYID=3, 6 PRB, 1 ports, PSS power=-85.0 dBm\n"
    cells = parser.parse(output)
    assert cells[0].bandwidth_mhz is BandwidthMHz.BW_1_4


def test_parse_positive_power() -> None:
    output = "Found CELL 869.5 MHz, EARFCN=2400, PHYID=1, 50 PRB, 1 ports, PSS power=0.5 dBm\n"
    cells = parser.parse(output)
    assert cells[0].rsrp == 0  # round(0.5) = 0


def test_parse_cell_id_tac_mcc_mnc_are_none() -> None:
    """srsRAN cell_search does not provide these fields."""
    output = "Found CELL 869.5 MHz, EARFCN=2405, PHYID=1, 50 PRB, 2 ports, PSS power=-80.0 dBm\n"
    cells = parser.parse(output)
    assert cells[0].cell_id is None
    assert cells[0].tac is None
    assert cells[0].mcc is None
    assert cells[0].mnc is None
