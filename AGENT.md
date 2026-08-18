# AGENT.md

# LTE Cell Scanner (Python CLI)

## Mission

Develop a modern, fully local, command-line LTE cell scanner that utilizes **RTL-SDR V3** together with **srsRAN** to discover and identify LTE cells.

The application is **not** an SDR implementation. SDR processing, synchronization, OFDM demodulation, and LTE decoding are delegated entirely to **srsRAN**.

The application is responsible for:

- Executing scans
- Managing scan workflow
- Parsing srsRAN output
- Normalizing discovered cells
- Mapping MCC/MNC to operators
- Presenting results
- Exporting scan results
- Logging
- Configuration
- Future extensibility

No cloud services.

No external APIs.

Everything must work completely offline.

---

# Design Goals

The project must always prioritize:

- Simplicity
- Readability
- Testability
- Maintainability
- Deterministic behavior
- Loose coupling
- Small modules
- Explicit dependencies
- Strong typing
- Minimal magic
- Future extensibility

Never optimize for cleverness.

Always optimize for code that is easy to understand.

---

# High Level Architecture

```
CLI
 │
 ▼
Application
 │
 ├── Scan Service
 │
 ├── srsRAN Runner
 │
 ├── Parser
 │
 ├── Cell Repository
 │
 ├── Operator Resolver
 │
 ├── Formatter
 │
 └── Exporter
```

Each layer has one responsibility.

---

# Project Structure

```
src/

    cli/
        main.py
        commands.py

    application/
        scanner.py
        workflow.py

    domain/
        models.py
        enums.py

    services/
        srsran_runner.py
        parser.py
        operator_resolver.py
        exporter.py
        formatter.py

    infrastructure/
        config.py
        filesystem.py
        logger.py

    repository/
        operator_db.py

    utils/
        frequency.py
        validation.py

tests/

configs/

data/

docs/
```

---

# Responsibilities

## CLI

Responsible only for:

- argument parsing
- validation
- invoking application

No business logic.

---

## Application

Coordinates scanning workflow.

Never parses LTE.

Never formats output.

Never reads files directly.

---

## srsRAN Runner

Single responsibility:

Launch srsRAN process.

Example:

- configure frequency
- configure bandwidth
- configure RTL-SDR
- capture stdout
- capture stderr
- return raw output

Nothing else.

---

## Parser

Converts raw srsRAN output into structured objects.

Input:

Raw text

Output:

```
LTECell
```

Never performs operator lookup.

---

## Operator Resolver

Maps

```
MCC
MNC
```

into

```
Operator Name
Country
```

Uses local database only.

No internet lookup.

---

## Formatter

Responsible for displaying data.

Support:

- table
- json
- csv
- yaml

No scan logic.

---

## Exporter

Writes results.

Supported:

- JSON
- CSV

Future:

- SQLite
- Parquet

---

# Domain Model

```
LTECell

frequency_mhz

earfcn

band

bandwidth_mhz

pci

cell_id

tac

mcc

mnc

operator

country

rsrp

rsrq

snr

timestamp
```

Domain models should remain immutable whenever practical.

---

# Configuration

Configuration must be stored in

```
configs/config.toml
```

No hardcoded values.

Example:

- RTL device index
- scan timeout
- retry count
- output format
- logging level

---

# Operator Database

Use a fully local database.

Example:

```
data/operators.json
```

Contains:

- MCC
- MNC
- Operator
- Country

No internet dependency.

---

# Logging

Use Python logging.

Support:

- INFO
- WARNING
- ERROR
- DEBUG

Never print debugging directly.

---

# Error Handling

Never silently ignore failures.

Use explicit exceptions.

Examples:

- SDR not found
- srsRAN missing
- Timeout
- Invalid configuration
- Parse failure

Every exception should contain actionable information.

---

# Testing

Testing is mandatory.

Unit tests:

- parser
- formatter
- operator resolver
- frequency helpers

Integration tests:

- srsRAN runner
- CLI

Mock external processes whenever possible.

---

# Code Style

Use:

- Python 3.12+
- dataclasses
- pathlib
- typing
- enums

Avoid:

- global state
- mutable shared objects
- circular imports
- wildcard imports

Every public function should have type hints.

---

# Dependencies

Preferred:

- typer
- rich
- pydantic
- pytest

Avoid unnecessary dependencies.

---

# CLI Commands

Example:

```
lte-scan scan
```

```
lte-scan scan --band 5
```

```
lte-scan scan --band 8
```

```
lte-scan scan --freq 869.5
```

```
lte-scan export results.json
```

```
lte-scan export results.csv
```

```
lte-scan version
```

---

# Output Example

```
LTE CELL DISCOVERY

---------------------------------------------------------------

Frequency : 869.530 MHz

Band : LTE Band 5

EARFCN : xxxx

PCI : xx

Cell ID : xxxxx

TAC : xxxx

Bandwidth : 10 MHz

MCC : 510

MNC : 10

Operator : Telkomsel

Country : Indonesia

RSRP : -81 dBm

RSRQ : -9 dB

SNR : 22 dB

---------------------------------------------------------------
```

---

# Non-Goals

This project will NOT:

Implement LTE PHY

Implement OFDM

Implement synchronization

Decode IQ manually

Replace srsRAN

Implement SDR drivers

Provide GUI

Provide web services

Depend on cloud APIs

---

# Future Extensions

Possible future modules:

- Multi-device scanning
- Continuous monitoring mode
- Multi-band scheduler
- Historical scan database
- SQLite backend
- Interactive TUI
- Automatic band sweeping
- Cell change detection
- Neighbor cell tracking
- Spectrum occupancy statistics
- GPS integration
- Heatmap generation
- Prometheus metrics
- REST API
- Web dashboard
- Plugin architecture
- Support additional SDR hardware (HackRF, Airspy, LimeSDR, PlutoSDR)

These extensions should be additive and should not require major refactoring of the existing architecture.

---

# Engineering Principles

- Keep functions small.
- Prefer composition over inheritance.
- Favor explicit code over implicit behavior.
- One module, one responsibility.
- Keep dependencies flowing inward.
- Separate domain logic from infrastructure.
- Write code that is easy to delete and replace.
- Refactor only when duplication becomes meaningful.
- Optimize for clarity before performance.
- Every feature should be independently testable.
- Every module should be replaceable without affecting unrelated components.
- Software should remain understandable after years of maintenance.

---

# ⚠️ HARDWARE & DRIVER POLICY - STRICT WARNING

## NEVER ACCESS HARDWARE OR DRIVERS DIRECTLY

**This is a CRITICAL violation boundary that must NEVER be crossed.**

### What I MUST NOT Do:

1. **NO direct device access** - Never use `echo`, `tee`, `cat`, or any command to write to `/dev/bus/usb/*`, `/sys/bus/usb/*`, or any hardware device path
2. **NO driver manipulation** - Never run commands to bind/unbind kernel drivers (`modprobe`, `rmmod`, `echo driver > /sys/bus/.../driver/bind`)
3. **NO USB reconfiguration** - Never attempt to reconfigure USB interfaces or device classes
4. **NO hardware troubleshooting** - If hardware fails, report the error and STOP. Do not attempt to fix it.

### What I MUST Do Instead:

1. **Report hardware errors clearly** - If a scan fails due to hardware issues, state the error and let the human decide next steps
2. **Suggest commands for human execution** - If driver/hardware work is needed, provide the commands as text recommendations that the human can run manually
3. **Focus on code only** - My role is to write, test, and maintain the Python application code. Hardware is out of scope.
4. **Respect system boundaries** - The system has working hardware configurations. Do not touch them.

### Example Violations (NEVER DO THESE):

```bash
# ❌ NEVER RUN - Direct hardware access
echo "something" > /dev/bus/usb/001/002
echo -n "driver" | tee /sys/bus/usb/devices/1-2:1.0/driver/unbind

# ❌ NEVER RUN - Driver manipulation  
sudo modprobe rtl2832u
sudo rmmod dvb_usb_rtl28xxu

# ❌ NEVER RUN - Device probing
lsmod | grep rtl
dmesg | grep -i rtl
```

### Correct Approach:

```bash
# ✅ Report error and stop
echo "ERROR: RTL-SDR device not accessible. Please check hardware connection."

# ✅ Suggest human execution
# Run these commands manually if needed:
# sudo modprobe rtl2832u
# lsusb | grep -i rtl
```

### Hardware is Human Territory

Hardware configuration, driver loading, USB device management, and system-level troubleshooting are **human responsibilities only**. AI assistants must:

- Detect hardware failures through error messages
- Report them clearly
- Stop execution immediately
- Provide diagnostic information as text
- NEVER attempt to fix or manipulate hardware directly

This policy exists to prevent accidental system damage and maintain clear separation between software logic and system infrastructure.

---

## RTL-SDR Detection Architecture

### Important: No Manual Device Detection in CLI

The CLI **does not** detect or configure RTL-SDR devices directly. This is handled entirely by:

1. **srsRAN binary** - receives device parameters from CLI
2. **SoapySDR** - automatically discovers and opens RTL-SDR devices

### Device Discovery Flow

```
CLI passes: -b <band> -g <gain>
    ↓
srsRAN initializes SoapySDR
    ↓
SoapySDR scans USB buses for RTL-SDR devices
    ↓
Auto-discovers: driver=rtlsdr, serial=00000001
    ↓
Opens: /dev/bus/usb/001/002 (NOT ttyUSB)
```

### Key Points

- **RTL-SDR is NOT on ttyUSB** - it's accessed via USB path directly
- **ttyUSB0-2** are typically for USB modems (Huawei, etc.)
- **No config needed** for device selection - SoapySDR auto-detects
- **Timeout issue**: Default 30s is too short for full band scans. Use 90s+ for reliable operation.

### Verification Commands

```bash
# Check RTL-SDR USB detection
lsusb | grep -i rtl
# Expected: ID 0bda:2838 Realtek Semiconductor Corp. RTL2838 DVB-T

# Verify SoapySDR detection
SoapySDRUtil --find="driver=rtlsdr"
# Expected: Found Rafael Micro R820T tuner
```