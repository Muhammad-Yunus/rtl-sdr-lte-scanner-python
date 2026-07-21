"""Input validators for fields coming from CLI or srsRAN.

Each helper raises :class:`ValueError` with a message that tells the caller
what went wrong and what range to use.
"""


def validate_mcc(mcc: int) -> int:
    """MCC must be a 3-digit integer between 000 and 999."""
    if not isinstance(mcc, int) or isinstance(mcc, bool):
        raise TypeError(f"MCC must be an int, got {type(mcc).__name__}")
    if not (0 <= mcc <= 999):
        raise ValueError(f"MCC {mcc} is outside the valid range [0, 999].")
    return mcc


def validate_mnc(mnc: int) -> int:
    """MNC may be 2 or 3 digits, accepted here as 0..999."""
    if not isinstance(mnc, int) or isinstance(mnc, bool):
        raise TypeError(f"MNC must be an int, got {type(mnc).__name__}")
    if not (0 <= mnc <= 999):
        raise ValueError(f"MNC {mnc} is outside the valid range [0, 999].")
    return mnc


def validate_frequency_mhz(frequency_mhz: float) -> float:
    """LTE DL frequencies fall roughly in 700 MHz–3.8 GHz."""
    if not isinstance(frequency_mhz, (int, float)) or isinstance(frequency_mhz, bool):
        raise TypeError(
            f"frequency_mhz must be numeric, got {type(frequency_mhz).__name__}"
        )
    if not (300.0 <= frequency_mhz <= 6000.0):
        raise ValueError(
            f"frequency_mhz {frequency_mhz} is outside the plausible LTE range "
            f"[300, 6000] MHz."
        )
    return float(frequency_mhz)


def validate_earfcn(earfcn: int) -> int:
    """EARFCN is at most 5 digits for FDD bands and up to ~65535 for TDD."""
    if not isinstance(earfcn, int) or isinstance(earfcn, bool):
        raise TypeError(f"EARFCN must be an int, got {type(earfcn).__name__}")
    if not (0 <= earfcn <= 65535):
        raise ValueError(f"EARFCN {earfcn} is outside the valid range [0, 65535].")
    return earfcn