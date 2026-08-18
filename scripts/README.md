# Scripts Directory

Quick scan scripts for LTE Cell Scanner with pre-configured parameters for different use cases.

## Available Scripts

| Script | Purpose | Frames | Time | Use Case |
|--------|---------|--------|------|----------|
| `quick_scan.sh` | Fast discovery | 5 | ~5-10s | Quick cell presence check |
| `fast_scan.sh` | Balanced scan | 10 | ~10-15s | Daily monitoring |
| `balanced_scan.sh` | Multi-pass scan | 10+50 | ~20-30s | Accurate RSRP measurement |
| `narrow_scan.sh` | Narrow range | 5 | ~3-5s | Operator-specific scan |
| `band5_scan.sh` | Band 5 scan | 10 | ~15-20s | LTE Band 5 (869-894 MHz) |
| `export_quick.sh` | Scan + Export | 5 | ~10-15s | Automated JSON export |

## Usage

All scripts output JSON format and save to `./exports/` directory with timestamp.

```bash
# From project root
cd /path/to/rtl-sdr-lte-scanner-python

# Run quick scan
./scripts/quick_scan.sh

# Run balanced multi-pass scan
./scripts/balanced_scan.sh

# Run narrow scan (specific EARFCN range)
./scripts/narrow_scan.sh
```

## Output Location

All scan results are saved to:
```
./exports/<script_name>_<timestamp>.json
```

Example:
```
./exports/quick_scan_20250813_143022.json
./exports/fast_scan_20250813_143045.json
./exports/balanced_scan_20250813_143105.json
```

## Configuration

All parameters are hardcoded in each script:
- **BAND**: Default Band 8 (925-960 MHz)
- **FRAMES**: Control scan accuracy vs speed
- **GAIN**: 42 dB (optimal for RTL-SDR V3)
- **TIMEOUT**: Safety timeout per scan
- **OUTPUT_FORMAT**: JSON

## Modification

To modify parameters, edit the corresponding script file. Common changes:

```bash
# Change EARFCN range (narrow_scan.sh)
EARFCN_RANGE="3499-3501"  # Telkomsel center

# Change frames for more/less accuracy
FRAMES=5   # Faster but less accurate
FRAMES=20  # Slower but more accurate

# Change gain for different signal conditions
GAIN=35    # Weaker signal
GAIN=49    # Stronger signal
```

## Exit Codes

- `0`: Success
- `1`: Scan failed (check output for error message)

## Notes

- All scripts run from project root directory
- JSON output includes: frequency, band, earfcn, pci, cell_id, tac, mcc, mnc, operator, rsrp, rsrq, snr
- No manual hardware interaction required
- Scripts respect RTL-SDR device lock mechanism
