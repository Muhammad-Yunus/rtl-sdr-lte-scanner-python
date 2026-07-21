"""Tests for src/services/operator_resolver.py."""

from __future__ import annotations

from pathlib import Path

from src.domain.enums import Band, BandwidthMHz
from src.domain.models import LTECell
from src.repository.operator_db import OperatorDatabase
from src.services.operator_resolver import OperatorResolver, ResolvedOperator

FIXTURE = Path(__file__).parent / "fixtures" / "operators.json"


def _make_resolver() -> OperatorResolver:
    return OperatorResolver(OperatorDatabase.from_json(FIXTURE))


def _cell(mcc: int, mnc: int) -> LTECell:
    return LTECell(
        frequency_mhz=869.5,
        earfcn=2405,
        band=Band.BAND_5,
        bandwidth_mhz=BandwidthMHz.BW_10,
        pci=1,
        cell_id=1,
        tac=1,
        mcc=mcc,
        mnc=mnc,
    )


def test_resolve_known_operator() -> None:
    resolver = _make_resolver()
    assert resolver.resolve(510, 10) == ResolvedOperator(
        operator="Telkomsel", country="Indonesia"
    )


def test_resolve_unknown_returns_none() -> None:
    resolver = _make_resolver()
    assert resolver.resolve(999, 99) is None


def test_enrich_fills_operator_and_country() -> None:
    resolver = _make_resolver()
    enriched = resolver.enrich(_cell(510, 10))
    assert enriched.operator == "Telkomsel"
    assert enriched.country == "Indonesia"


def test_enrich_leaves_unknown_cell_untouched() -> None:
    resolver = _make_resolver()
    cell = _cell(999, 99)
    assert resolver.enrich(cell) is cell


def test_enrich_does_not_overwrite_existing() -> None:
    resolver = _make_resolver()
    cell = _cell(510, 10).with_operator("Custom", "Customland")
    assert resolver.enrich(cell) is cell


def test_enrich_returns_new_instance_when_changing() -> None:
    resolver = _make_resolver()
    cell = _cell(510, 10)
    enriched = resolver.enrich(cell)
    assert enriched is not cell
    assert cell.operator is None  # original frozen and unchanged