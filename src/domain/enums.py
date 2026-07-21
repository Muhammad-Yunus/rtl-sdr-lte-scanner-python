from __future__ import annotations

from enum import Enum


class Band(int, Enum):
    """LTE operating bands most relevant for RTL-SDR scanning.

    Reference: 3GPP TS 36.101 Table 5.5-1.
    Only the bands commonly scanned with a single dongle are listed; extend
    the table when new bands are required.
    """

    BAND_3 = 3
    BAND_5 = 5
    BAND_7 = 7
    BAND_8 = 8
    BAND_20 = 20
    BAND_28 = 28
    BAND_38 = 38
    BAND_40 = 40

    @property
    def label(self) -> str:
        return f"LTE Band {int(self)}"


class BandwidthMHz(int, Enum):
    """Channel bandwidths permitted for LTE."""

    BW_1_4 = 1
    BW_3 = 3
    BW_5 = 5
    BW_10 = 10
    BW_15 = 15
    BW_20 = 20


class OutputFormat(str, Enum):
    """Renderers supported by the formatter layer."""

    TABLE = "table"
    JSON = "json"
    CSV = "csv"
    YAML = "yaml"


class ScanStatus(str, Enum):
    """Lifecycle state of a single scan run."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"