# rtl-sdr-lte-scanner-python

A fully local, command-line LTE cell scanner built around an **RTL-SDR V3** dongle and **srsRAN**.

This project wraps `srsRAN`; it does **not** implement OFDM, PHY, or SDR drivers.
See [`AGENT.md`](./AGENT.md) for the full mission statement and engineering rules.

## Status

Scaffold-only. Domain model, parser, formatter, and operator resolver land in
subsequent increments.

## Requirements

- Python 3.12+
- An RTL-SDR V3 dongle with working drivers
- A local build of `srsRAN` reachable via `PATH` (or `configs/config.toml`)

## Installation (editable)

```bash
pip install -e ".[dev]"
```

## CLI entry point

```bash
lte-scan --help
```

The `scan`, `export`, and `version` commands will be wired up in later increments.

## Project layout

```
src/
  cli/               # typer app — argument parsing only
  application/       # scan workflow coordinator
  domain/            # LTECell model + enums
  services/          # srsRAN runner, parser, operator resolver, formatter, exporter
  infrastructure/    # config, filesystem, logger
  repository/        # operator database loader
  utils/             # frequency, validation helpers
tests/
configs/             # config.toml — all runtime values
data/                # operators.json — local operator lookup
docs/                # design notes
```

## Configuration

All runtime values live in `configs/config.toml`. Nothing is hardcoded in source.

## Operator database

`data/operators.json` maps `(MCC, MNC)` to `(Operator, Country)`. Lookups are
strictly local — no network calls are ever made.

## Testing

```bash
pytest
```

## License

MIT.
