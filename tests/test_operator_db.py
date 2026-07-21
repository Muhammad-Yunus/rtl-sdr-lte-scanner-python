"""Tests for src/repository/operator_db.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.domain.exceptions import OperatorLookupError
from src.domain.models import OperatorEntry
from src.repository.operator_db import OperatorDatabase

FIXTURE = Path(__file__).parent / "fixtures" / "operators.json"


def test_load_fixture_db() -> None:
    db = OperatorDatabase.from_json(FIXTURE)
    assert len(db) == 2


def test_lookup_hit_and_miss() -> None:
    db = OperatorDatabase.from_json(FIXTURE)
    entry = db.lookup(510, 10)
    assert entry == OperatorEntry(
        mcc=510, mnc=10, operator="Telkomsel", country="Indonesia"
    )
    assert db.lookup(999, 99) is None


def test_contains_operator_key() -> None:
    db = OperatorDatabase.from_json(FIXTURE)
    assert (510, 10) in db
    assert (510, 11) not in db


def test_load_real_project_database() -> None:
    db = OperatorDatabase.from_json(Path("data/operators.json"))
    assert len(db) >= 2


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(OperatorLookupError, match="not found"):
        OperatorDatabase.from_json(tmp_path / "nope.json")


def test_invalid_json_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(OperatorLookupError, match="not valid JSON"):
        OperatorDatabase.from_json(bad)


def test_schema_violation_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad_schema.json"
    bad.write_text(
        json.dumps({"entries": [{"mcc": 9999, "mnc": 0, "operator": "x", "country": "y"}]}),
        encoding="utf-8",
    )
    with pytest.raises(OperatorLookupError, match="invalid schema"):
        OperatorDatabase.from_json(bad)


def test_missing_required_field_raises(tmp_path: Path) -> None:
    bad = tmp_path / "missing.json"
    bad.write_text(json.dumps({"entries": [{"mcc": 510, "mnc": 1}]}), encoding="utf-8")
    with pytest.raises(OperatorLookupError, match="invalid schema"):
        OperatorDatabase.from_json(bad)