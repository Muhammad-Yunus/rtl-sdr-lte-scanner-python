#!/bin/bash
#
# Band 5 Scan Script - Fast Scan on LTE Band 5
# Purpose: Scan Band 5 (869-894 MHz) with optimized parameters
# Expected time: ~15-20 seconds
#

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Scan parameters
BAND=5
FRAMES=10
GAIN=42
TIMEOUT=30
OUTPUT_FORMAT="json"
EXPORT_DIR="./exports"

echo "========================================"
echo "  Band 5 Fast Scan (10 frames)"
echo "========================================"
echo ""
echo "Configuration:"
echo "  Band: LTE Band $BAND (869-894 MHz)"
echo "  Frames: $FRAMES"
echo "  Gain: ${GAIN} dB"
echo "  Timeout: ${TIMEOUT}s"
echo "  Format: $OUTPUT_FORMAT"
echo ""

# Run scan
CLI_OUTPUT=$(python3 -m src.cli.main scan \
    --band "$BAND" \
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
OUTPUT_FILE="${EXPORT_DIR}/band5_scan_${TIMESTAMP}.json"

mkdir -p "$EXPORT_DIR"
echo "$CLI_OUTPUT" > "$OUTPUT_FILE"

echo "========================================"
echo "  Band 5 Scan Complete!"
echo "========================================"
echo ""
echo "Output saved to: $OUTPUT_FILE"
echo ""
echo "$CLI_OUTPUT"
