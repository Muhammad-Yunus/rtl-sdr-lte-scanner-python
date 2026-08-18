#!/bin/bash
#
# Narrow Scan Script - Specific EARFCN Range
# Purpose: Scan only specific frequency range (operator-specific)
# Expected time: ~3-5 seconds per range
#

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Scan parameters
BAND=8
EARFCN_RANGE="3499-3501"  # Telkomsel central frequencies
FRAMES=5
GAIN=42
TIMEOUT=15
OUTPUT_FORMAT="json"
EXPORT_DIR="./exports"

echo "========================================"
echo "  Narrow Scan (EARFCN $EARFCN_RANGE)"
echo "========================================"
echo ""
echo "Configuration:"
echo "  Band: LTE Band $BAND"
echo "  EARFCN Range: $EARFCN_RANGE"
echo "  Frames: $FRAMES"
echo "  Gain: ${GAIN} dB"
echo "  Timeout: ${TIMEOUT}s"
echo "  Format: $OUTPUT_FORMAT"
echo ""

# Run narrow scan
CLI_OUTPUT=$(python3 -m src.cli.main scan \
    --band "$BAND" \
    --earfcn-range "$EARFCN_RANGE" \
    --frames "$FRAMES" \
    --gain "$GAIN" \
    --timeout "$TIMEOUT" \
    --format "$OUTPUT_FORMAT" 2>&1)

EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "ERROR: Scan failed with exit code $EXIT_CODE"
    echo "$CLI_OUTPUT"
    exit $EXIT_CODE
fi

# Save to file with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="${EXPORT_DIR}/narrow_scan_${TIMESTAMP}.json"

mkdir -p "$EXPORT_DIR"
echo "$CLI_OUTPUT" > "$OUTPUT_FILE"

echo "========================================"
echo "  Narrow Scan Complete!"
echo "========================================"
echo ""
echo "Output saved to: $OUTPUT_FILE"
echo ""
echo "$CLI_OUTPUT"
