#!/bin/bash
#
# Export Quick Scan Script - Scan and Export JSON
# Purpose: Quick scan with immediate JSON export
# Expected time: ~10-15 seconds
#

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Scan parameters
BAND=8
FRAMES=5
GAIN=42
TIMEOUT=30
OUTPUT_FORMAT="json"
EXPORT_DIR="./exports"
SCAN_NAME="quick_export"

echo "========================================"
echo "  Quick Export Scan"
echo "========================================"
echo ""
echo "Configuration:"
echo "  Band: LTE Band $BAND"
echo "  Frames: $FRAMES"
echo "  Gain: ${GAIN} dB"
echo "  Timeout: ${TIMEOUT}s"
echo "  Format: $OUTPUT_FORMAT"
echo ""

# Run scan and save to temp file
TEMP_FILE=$(mktemp)
trap "rm -f $TEMP_FILE" EXIT

python3 -m src.cli.main scan \
    --band "$BAND" \
    --frames "$FRAMES" \
    --gain "$GAIN" \
    --timeout "$TIMEOUT" \
    --format "$OUTPUT_FORMAT" > "$TEMP_FILE" 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "ERROR: Scan failed with exit code $EXIT_CODE"
    cat "$TEMP_FILE"
    exit $EXIT_CODE
fi

# Move to final location with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="${EXPORT_DIR}/${SCAN_NAME}_${TIMESTAMP}.json"

mkdir -p "$EXPORT_DIR"
mv "$TEMP_FILE" "$OUTPUT_FILE"

echo "========================================"
echo "  Quick Export Complete!"
echo "========================================"
echo ""
echo "Output saved to: $OUTPUT_FILE"
echo ""
cat "$OUTPUT_FILE"
