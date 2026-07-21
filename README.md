<div align="center">

# LTE Cell Scanner

### Local RF cell discovery with RTL-SDR and srsRAN

[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi%205-c51244)](https://www.raspberrypi.com/)
[![srsRAN](https://img.shields.io/badge/srsRAN-4G-blue.svg)](https://www.srsran.com/)
[![RTL-SDR](https://img.shields.io/badge/RTL--SDR-V3-orange.svg)](https://www.rtl-sdr.com/)
[![Tests](https://img.shields.io/badge/Tests-147%20passed-brightgreen)](#testing)

<br>

A fully local, offline CLI tool that scans and identifies LTE cells using a cheap RTL-SDR dongle.
No cloud. No API. No tracking. Just RF.

</div>

---

## Overview

`lte-scan` discovers nearby LTE cell towers by delegating all RF and PHY processing to
[srsRAN](https://www.srsran.com/), then parses, enriches, and presents the results in a
clean format.

**What it does:**

- Scans LTE bands (8, 5, 3) via `lte_cell_search` binary
- Parses raw srsRAN output into structured cell data
- Resolves MCC/MNC to operator names from a local database
- Outputs in table, JSON, CSV, or YAML

**What it does NOT do:**

- Implement SDR drivers or OFDM demodulation
- Decode PDSCH or user data
- Make any network requests
- Require internet access

> This project is a **Python wrapper** around srsRAN, not an SDR implementation itself.

---

## Hardware Requirements

| Component | Status | Notes |
|-----------|--------|-------|
| Raspberry Pi 5 | Required | ARM64, any Pi 4/5 works |
| RTL-SDR V3 dongle | Required | R820T/R820T2 tuner |
| Antenna | Required | 800-1000 MHz for Band 8 |
| MicroSD card | Required | 16GB+ recommended |

> **RTL-SDR is receive-only.** You can scan and identify cells, but not transmit.

---

## Software Requirements

| Software | Version | Purpose |
|----------|---------|---------|
| Raspberry Pi OS | Bookworm/Bullseye | Base OS |
| Python | 3.12+ | Runtime |
| srsRAN | 4G (built from source) | Cell search binary |
| SoapySDR | Latest | RF abstraction layer |

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/Muhammad-Yunus/rtl-sdr-lte-scanner-python.git
cd rtl-sdr-lte-scanner-python

# 2. Install dependencies
sudo apt install python3-pip python3-venv
python3 -m pip install pydantic typer rich pyyaml

# 3. Configure binary path (edit configs/config.toml)
#    Set [srsran].binary_path to your cell_search binary

# 4. Scan!
python3 -m src.cli.main scan --band 8
```

---

## Building srsRAN

If you haven't built srsRAN yet, follow these steps:

```bash
# Install build dependencies
sudo apt install cmake g++ libfftw3-dev libmbedtls-dev \
  libsoapysdr-dev libboost-program-options-dev

# Clone and build
cd /home/pi
git clone https://github.com/srsran/srsRAN_4G.git
cd srsRAN_4G
mkdir build && cd build
cmake ..
make -j$(nproc)

# Verify
ls -la build/lib/examples/cell_search
# Expected: /home/pi/srsRAN_4G/build/lib/examples/cell_search
```

---

## Installation

```bash
# Install Python packages
python3 -m pip install pydantic typer rich pyyaml

# (Optional) For development
python3 -m pip install pytest pytest-cov ruff

# Verify RTL-SDR is detected
lsusb | grep -i rtl
# Expected: Bus 003 Device 002: ID 0bda:2838 Realtek Semiconductor Corp. RTL2838 DVB-T

# Verify SoapySDR can see the device
SoapySDRUtil --find
# Expected: Found Rafael Micro R820T tuner
```

---

## Configuration

All settings live in `configs/config.toml`. No values are hardcoded.

```toml
[device]
index = 0

[scan]
default_band = 8
gain_db = 42.0
timeout_seconds = 30
multi_pass = false
quick_frames = 10
deep_frames = 500

[output]
format = "table"
export_dir = "./exports"

[logging]
level = "INFO"
file = ""

[srsran]
binary_path = "/home/pi/srsRAN_4G/build/lib/examples/cell_search"
```

### Key Settings

| Key | Default | Description |
|-----|---------|-------------|
| `default_band` | `8` | LTE band to scan (3, 5, 8) |
| `gain_db` | `42.0` | RF gain in dB (40-49 optimal for R820T) |
| `timeout_seconds` | `30` | Max scan duration per band |
| `multi_pass` | `false` | Enable two-pass scan (quick → deep) |
| `quick_frames` | `10` | Frames for quick discovery pass |
| `deep_frames` | `500` | Frames for deep accuracy pass |
| `binary_path` | - | Absolute path to `cell_search` binary |
| `format` | `table` | Default output format (table/json/csv/yaml) |

---

## Usage

### Scan a band

```bash
# Scan Band 8 (default, 925-960 MHz) — best for RTL-SDR
python3 -m src.cli.main scan

# Scan Band 5 (869-894 MHz)
python3 -m src.cli.main scan --band 5

# Scan with custom gain
python3 -m src.cli.main scan --band 8 --gain 45

# Scan with JSON output
python3 -m src.cli.main scan --band 8 --format json

# Scan with longer timeout
python3 -m src.cli.main scan --band 8 --timeout 600
```

### Multi-pass scan

Two-pass scan: quick discovery (10 frames) then deep accuracy scan (500 frames).
Faster than full deep scan while still getting accurate RSRP measurements.

```bash
# Multi-pass scan on Band 8
python3 -m src.cli.main scan --band 8 --multi-pass

# Multi-pass with custom deep frames
python3 -m src.cli.main scan --band 8 --multi-pass --frames 1000
```

### Band sweep

Scan multiple bands sequentially in one command.

```bash
# Sweep Band 8 and 5 (default)
python3 -m src.cli.main sweep

# Sweep specific bands
python3 -m src.cli.main sweep --bands 8,5,3

# Sweep with multi-pass per band
python3 -m src.cli.main sweep --bands 8,5 --multi-pass

# Sweep with JSON output
python3 -m src.cli.main sweep --bands 8,5 --format json
```

### Export results

```bash
# Export to JSON
python3 -m src.cli.main export result.json --band 8

# Export to CSV
python3 -m src.cli.main export result.csv --band 5
```

### Other commands

```bash
# Show version
python3 -m src.cli.main version

# Show help
python3 -m src.cli.main --help
python3 -m src.cli.main scan --help
```

---

## Scan Results

### Table Output

```
                                               LTE Cell Discovery
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━┳━━━━━┳━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━┳━━━━━━┳━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━┳━━━━┓
┃ Frequency   ┃ Band       ┃ EARFCN ┃ PCI ┃ Cell ID ┃ TAC  ┃ Bandwidth ┃ MCC  ┃ MNC  ┃ Operator  ┃ RSRP    ┃ RSRQ ┃ S… ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━╇━━━━━╇━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━╇━━━━━━╇━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━╇━━━━┩
│ 930.100 MHz │ LTE Band 8 │ 3501   │ 243 │ None    │ None │ 10 MHz    │ None │ None │ Telkomsel │ -26 dBm │ -    │ -  │
│ 930.100 MHz │ LTE Band 8 │ 3501   │ 416 │ None    │ None │ 20 MHz    │ None │ None │ Telkomsel │ -24 dBm │ -    │ -  │
│ 930.200 MHz │ LTE Band 8 │ 3502   │ 2   │ None    │ None │ 5 MHz     │ None │ None │ Telkomsel │ -25 dBm │ -    │ -  │
│ 930.400 MHz │ LTE Band 8 │ 3504   │ 2   │ None    │ None │ 3 MHz     │ None │ None │ Telkomsel │ -26 dBm │ -    │ -  │
│ 930.600 MHz │ LTE Band 8 │ 3506   │ 0   │ None    │ None │ 20 MHz    │ None │ None │ Telkomsel │ -31 dBm │ -    │ -  │
│ 945.300 MHz │ LTE Band 8 │ 3653   │ 112 │ None    │ None │ 10 MHz    │ None │ None │ XL Axiata │ -28 dBm │ -    │ -  │
└─────────────┴────────────┴────────┴─────┴─────────┴──────┴───────────┴──────┴──────┴───────────┴─────────┴──────┴────┘
```

### JSON Output

```json
[
  {
    "frequency_mhz": 930.1,
    "earfcn": 3501,
    "band": "8",
    "bandwidth_mhz": 10,
    "pci": 243,
    "cell_id": null,
    "tac": null,
    "mcc": null,
    "mnc": null,
    "rsrp": -26,
    "rsrq": null,
    "snr": null,
    "operator": "Telkomsel",
    "country": "Indonesia",
    "timestamp": "2026-07-21T08:58:05.435715+00:00"
  },
  {
    "frequency_mhz": 945.3,
    "earfcn": 3653,
    "band": "8",
    "bandwidth_mhz": 10,
    "pci": 112,
    "cell_id": null,
    "tac": null,
    "mcc": null,
    "mnc": null,
    "rsrp": -28,
    "rsrq": null,
    "snr": null,
    "operator": "XL Axiata",
    "country": "Indonesia",
    "timestamp": "2026-07-21T08:58:05.435755+00:00"
  }
]
```

> **Note:** `cell_id`, `tac`, `mcc`, `mnc` are `null` because `lte_cell_search` only performs
> PSS detection (Physical Layer). These fields require a MIB/SIB decoder which is not yet implemented.
> **Operator names** are resolved via EARFCN-to-frequency mapping from public spectrum allocations.

### Field Glossary

| Field | Description |
|-------|------------|
| **Frequency** | Downlink frequency in MHz. This is the frequency the RTL-SDR listens on. |
| **Band** | LTE operating band. Band 8 = 925–960 MHz. Determines the frequency range. |
| **EARFCN** | *E-UTRA Absolute Radio Frequency Channel Number*. A unique numeric ID for each channel within a band. Formula: `freq = 925 + 0.1 × (EARFCN - 3450)` for Band 8. |
| **PCI** | *Physical Cell ID*. Physical layer identifier (0–503). Used to distinguish cells on the same frequency. PCI is **not** a globally unique ID — it can be reused across different cell sites. |
| **Cell ID** | Unique cell identity within the operator's network. **Null** — requires MIB/SIB decode which `lte_cell_search` does not perform. |
| **TAC** | *Tracking Area Code*. Geographic area where the cell is located. **Null** — requires MIB/SIB decode. |
| **Bandwidth** | Channel bandwidth in MHz (3/5/10/15/20). Derived from the number of Physical Resource Blocks (PRB). |
| **MCC** | *Mobile Country Code*. Country identifier (e.g. 510 = Indonesia). **Null** — requires MIB/SIB decode. |
| **MNC** | *Mobile Network Code*. Operator identifier within a country (e.g. 10 = Telkomsel). **Null** — requires MIB/SIB decode. |
| **Operator** | Operator name. Resolved via **EARFCN → frequency → known spectrum allocation** (not from MIB/SIB). |
| **RSRP** | *Reference Signal Received Power*. Signal strength in dBm. More negative = weaker. -26 dBm = very strong, -100 dBm = weak. |
| **RSRQ** | *Reference Signal Received Quality*. Signal quality in dB. **Null** — not provided by `lte_cell_search`. |
| **SNR** | *Signal-to-Noise Ratio*. Signal quality in dB. **Null** — not available from cell search. |

---

## Architecture

```
CLI (Typer)
    │
    ▼
Application Layer
    │
    ├── ScanService ──────── Orchestrates the full workflow
    │
    ├── srsRAN Runner ────── Launches lte_cell_search subprocess
    │
    ├── Cell Parser ──────── Parses raw stdout into LTECell objects
    │
    ├── Operator Resolver ── MCC/MNC → Operator/Country lookup
    │
    ├── Formatter ────────── Render as table, JSON, CSV, or YAML
    │
    └── Exporter ─────────── Write results to disk
```

### Design Principles

- **Clean Architecture** — domain logic isolated from infrastructure
- **Immutable models** — `LTECell` is a frozen dataclass
- **Protocol-based DI** — every dependency is swappable for testing
- **No global state** — all configuration flows through `config.toml`
- **Fully offline** — zero network calls, zero cloud dependencies

---

## Project Structure

```
rtl-sdr-lte-scanner-python/
├── configs/
│   └── config.toml                # Runtime configuration
├── data/
│   ├── operators.json             # MCC/MNC → operator lookup
│   └── frequency_band_map.json    # EARFCN → operator spectrum mapping
├── src/
│   ├── cli/
│   │   └── main.py                # Typer CLI entry point
│   ├── application/
│   │   └── scanner.py             # ScanService + multi-pass + band sweep
│   ├── domain/
│   │   ├── models.py              # LTECell, OperatorEntry dataclasses
│   │   ├── enums.py               # Band, BandwidthMHz, OutputFormat
│   │   └── exceptions.py          # Domain-level exceptions
│   ├── services/
│   │   ├── srsran_runner.py       # Subprocess wrapper for cell_search
│   │   ├── cell_parser.py         # Regex parser for srsRAN output
│   │   ├── operator_resolver.py   # MCC/MNC + EARFCN enrichment
│   │   ├── formatter.py           # Table/JSON/CSV/YAML renderers
│   │   └── exporter.py            # File writer
│   ├── infrastructure/
│   │   ├── config.py              # Pydantic config loader
│   │   ├── logger.py              # Python logging setup
│   │   └── filesystem.py          # File/dir helpers
│   ├── repository/
│   │   ├── operator_db.py         # Operator database loader
│   │   └── frequency_band_db.py   # Frequency band map loader
│   └── utils/
│       ├── frequency.py           # EARFCN ↔ MHz converter
│       └── validation.py          # Input validators
├── tests/
│   ├── test_cell_parser.py        # Parser tests (17 cases)
│   ├── test_cli.py                # CLI integration tests
│   ├── test_scanner.py            # ScanService + multi-pass + sweep tests
│   ├── test_srsran_runner.py      # Runner tests
│   └── ...                        # 147 tests total
├── pyproject.toml                 # Project config & dependencies
└── README.md
```

---

## Supported Bands

| Band | Frequency Range | EARFCN Range | RTL-SDR Support | Notes |
|------|-----------------|--------------|-----------------|-------|
| **Band 8** | 925–960 MHz | 3450–3799 | Recommended | Most stable for R820T |
| **Band 5** | 869–894 MHz | 2400–2649 | Good | Common in Indonesia |
| **Band 3** | 1805–1880 MHz | 1200–1949 | Unstable | PLL often fails to lock |
| **Band 7** | 2620–2700 MHz | 2750–3449 | Poor | Too high for R820T |
| **Band 20** | 791–862 MHz | 6150–6449 | Partial | Below optimal range |
| **Band 28** | 758–803 MHz | 7030–7739 | Partial | Below optimal range |

> **Tip:** Start with **Band 8** for the best results on RTL-SDR.

---

## Scan Time Estimates

| Band | EARFCNs | Estimated Time (n=100) | Estimated Time (n=10) |
|------|---------|------------------------|----------------------|
| Band 8 | 349 | 5–15 min | 1–3 min |
| Band 5 | 249 | 4–10 min | 1–2 min |
| Band 3 | 749 | 10–25 min | 2–5 min |

> Scan time depends on `-n` (frames per EARFCN) and USB bus speed.
> Lower `-n` = faster but less accurate.

---

## Testing

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run with coverage
python3 -m pytest tests/ --cov=src --cov-report=term-missing

# Run specific test file
python3 -m pytest tests/test_cell_parser.py -v
```

All **147 tests** pass on Raspberry Pi 5.

---

## Operator Database

`data/operators.json` maps MCC/MNC pairs to operator names and countries.
Currently includes:

| MCC | MNC | Operator | Country |
|-----|-----|----------|---------|
| 510 | 01 | Indosat Ooredoo Hutchison | Indonesia |
| 510 | 10 | Telkomsel | Indonesia |

Add more entries to expand the lookup database. Format:

```json
{
  "entries": [
    {"mcc": 510, "mnc": 21, "operator": "XL Axiata", "country": "Indonesia"}
  ]
}
```

---

## Troubleshooting

### RTL-SDR not detected

```bash
# Check USB
lsusb | grep -i rtl

# Check SoapySDR
SoapySDRUtil --find

# If not found, set udev rules
sudo bash -c 'cat > /etc/udev/rules.d/20-rtlsdr.rules << EOF
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2838", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2832", MODE="0666"
EOF'
sudo udevadm control --reload-rules && sudo udevadm trigger
```

### PLL not locked

```
[R82XX] PLL not locked!
```

This is normal during initial tuning. If persistent, try:
- Lower the gain (`--gain 40`)
- Use a better antenna
- Move closer to a cell tower

### Binary not found

```
error: srsRAN binary not found
```

Set the correct path in `configs/config.toml`:

```toml
[srsran]
binary_path = "/home/pi/srsRAN_4G/build/lib/examples/cell_search"
```

---

## Roadmap

- [x] Cell search via srsRAN
- [x] Parse srsRAN output
- [x] Operator enrichment (MCC/MNC)
- [x] Multi-format output (table, JSON, CSV, YAML)
- [x] CLI with Typer
- [x] Multi-pass scan (quick → deep)
- [x] Multi-band sweep
- [ ] MIB/SIB decoder for Cell ID, TAC, MCC, MNC
- [ ] Continuous monitoring mode
- [ ] SQLite result database
- [ ] Neighbor cell tracking
- [ ] Spectrum occupancy stats

---

## License

MIT

---

<div align="center">

**Built with [srsRAN](https://www.srsran.com/), [RTL-SDR](https://www.rtl-sdr.com/), and [Python](https://www.python.org/)**

</div>
