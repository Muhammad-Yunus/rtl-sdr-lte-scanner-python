"""Loader for ``configs/config.toml``.

The configuration model is intentionally explicit (pydantic) so that bad
values are caught at startup with a clear message instead of failing
silently halfway through a scan.
"""

from __future__ import annotations

from pathlib import Path
from typing import Self

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - 3.12+ only project
    import tomli as tomllib  # type: ignore[no-redef]

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..domain.enums import OutputFormat
from ..domain.exceptions import ConfigError


class DeviceConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    index: int = Field(0, ge=0, le=31)


class ScanConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    default_frequency_mhz: float = 869.5
    default_band: int = Field(8, ge=1, le=100)
    gain_db: float = Field(42.0, ge=0.0, le=49.0)
    timeout_seconds: int = Field(30, gt=0)
    retry_count: int = Field(0, ge=0)
    allowed_bands: list[int] = Field(default_factory=list)

    @field_validator("default_frequency_mhz")
    @classmethod
    def _plausible_default_freq(cls, value: float) -> float:
        if not (300.0 <= value <= 6000.0):
            raise ValueError(
                f"default_frequency_mhz {value} is outside the plausible LTE "
                f"range [300, 6000] MHz."
            )
        return value


class OutputConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    format: OutputFormat = OutputFormat.TABLE
    export_dir: Path = Path("./exports")


class LoggingConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    level: str = "INFO"
    file: Path = Path()


class SrsranConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    binary_path: Path = Path()


class AppConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    device: DeviceConfig = Field(default_factory=DeviceConfig)
    scan: ScanConfig = Field(default_factory=ScanConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    srsran: SrsranConfig = Field(default_factory=SrsranConfig)

    @classmethod
    def from_toml(cls, path: Path) -> Self:
        """Load a configuration from a TOML file.

        Raises :class:`ConfigError` with an actionable message on any problem.
        """
        if not path.exists():
            raise ConfigError(f"Configuration file not found: {path}")
        try:
            raw = tomllib.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ConfigError(f"Cannot read configuration {path}: {exc}") from exc
        except tomllib.TOMLDecodeError as exc:
            raise ConfigError(f"Configuration {path} is not valid TOML: {exc}") from exc
        try:
            return cls.model_validate(raw)
        except Exception as exc:  # pydantic ValidationError
            raise ConfigError(f"Invalid configuration in {path}: {exc}") from exc
