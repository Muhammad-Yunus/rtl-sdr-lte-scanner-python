# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-08-13

### Added
- **Band 8 Operator Scan Script** (`scripts/scan_band8_by_operator.sh`)
  - Scans all 4 Indonesian operators in Band 8
  - Chunked scanning for reliability (20 EARFCN per chunk)
  - JSON output per operator
  - 95%+ detection rate in real-world testing

- **SCAN_REPORT.md** - Detailed Band 8 scan results
  - Telkomsel: 6 cells detected (EARFCN 3495-3506)
  - XL Axiata: 1 cell detected (EARFCN 3650)
  - Smartfren: 1 cell detected (EARFCN 3775)
  - Performance benchmarks and lessons learned

- **Documentation**
  - README.md with full setup instructions
  - PROJECT_HANDOVER.md for Raspberry Pi integration
  - docs/scan_report_band8_2026-08-11.md

### Changed
- Updated version from 0.1.0 to 1.0.0
- Improved scan reliability with chunked approach
- Enhanced JSON output format for easier parsing

### Performance
- **Scan duration:** ~3m28s for full Band 8 (350 EARFCNs)
- **Success rate:** 95%+ in field testing
- **Cells detected:** 6-8 cells per scan on average

### Hardware Tested
- Raspberry Pi 5 / Pi Zero 2W (planned)
- RTL-SDR V3 (R820T tuner)
- srsRAN 4G (cell_search binary)

## [0.1.0] - 2026-07-21

### Initial Release
- Python CLI wrapper around srsRAN
- Multi-band support (Band 8, 5, 3)
- JSON, CSV, YAML, Table output formats
- Local operator database (MCC/MNC → Operator name)
- 148 passing tests

---

## Contributors
- Muhammad Yunus (Initial development)
- Agnes AI (Documentation, optimization analysis)
