"""Tests for src/infrastructure/config.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.domain.enums import OutputFormat
from src.domain.exceptions import ConfigError
from src.infrastructure.config import AppConfig

FIXTURE = Path(__file__).parent / "fixtures" / "config.toml"


def test_load_fixture_matches_values() -> None:
    cfg = AppConfig.from_toml(FIXTURE)
    assert cfg.device.index == 1
    assert cfg.scan.default_frequency_mhz == 942.5
    assert cfg.scan.default_band == 8
    assert cfg.scan.gain_db == 42.0
    assert cfg.scan.timeout_seconds == 45
    assert cfg.scan.retry_count == 1
    assert cfg.scan.allowed_bands == [3, 5, 8]
    assert cfg.output.format is OutputFormat.JSON
    assert cfg.logging.level == "DEBUG"


def test_load_real_project_config() -> None:
    cfg = AppConfig.from_toml(Path("configs/config.toml"))
    assert cfg.device.index == 0
    assert cfg.scan.default_frequency_mhz == 869.5
    assert cfg.scan.default_band == 8
    assert cfg.scan.gain_db == 42.0
    assert cfg.srsran.binary_path == Path("/home/pi/srsRAN_4G/build/lib/examples/cell_search")


def test_missing_file_raises_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        AppConfig.from_toml(tmp_path / "nope.toml")


def test_invalid_toml_raises_config_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.toml"
    bad.write_text("this is = not = valid toml = [[", encoding="utf-8")
    with pytest.raises(ConfigError, match="not valid TOML"):
        AppConfig.from_toml(bad)


def test_invalid_scan_default_frequency_rejected(tmp_path: Path) -> None:
    bad = tmp_path / "bad_freq.toml"
    bad.write_text(
        "[scan]\ndefault_frequency_mhz = 50.0\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="Invalid configuration"):
        AppConfig.from_toml(bad)


def test_invalid_output_format_rejected(tmp_path: Path) -> None:
    bad = tmp_path / "bad_fmt.toml"
    bad.write_text('[output]\nformat = "xml"\n', encoding="utf-8")
    with pytest.raises(ConfigError, match="Invalid configuration"):
        AppConfig.from_toml(bad)


def test_negative_device_index_rejected(tmp_path: Path) -> None:
    bad = tmp_path / "bad_dev.toml"
    bad.write_text("[device]\nindex = -1\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="Invalid configuration"):
        AppConfig.from_toml(bad)
