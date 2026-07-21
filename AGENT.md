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