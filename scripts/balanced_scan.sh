#!/bin/bash
#
# Balanced Scan Script - Multi-Pass (Quick + Deep)
# Purpose: Quick discovery followed by deep accuracy on found cells
# Expected time: ~20-30 seconds
#

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Scan parameters
BAND=8
QUICK_FRAMES=10
DEEP_FRAMES=50
GAIN=42
TIMEOUT=60
OUTPUT_FORMAT="json"
EXPORT_DIR="./exports"

echo "========================================"
echo "  Balanced Scan (Multi-Pass)"
echo "========================================"
echo ""
echo "Configuration:"
echo "  Band: LTE Band $BAND"
echo "  Quick Frames: $QUICK_FRAMES"
echo "  Deep Frames: $DEEP_FRAMES"
echo "  Gain: ${GAIN} dB"
echo "  Timeout: ${TIMEOUT}s"
echo "  Format: $OUTPUT_FORMAT"
echo ""

# Run multi-pass scan
CLI_OUTPUT=$(python3 -m src.cli.main scan \
    --band "$BAND" \
    --multi-pass \
    --frames "$DEEP_FRAMES" \
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
OUTPUT_FILE="${EXPORT_DIR}/balanced_scan_${TIMESTAMP}.json"

mkdir -p "$EXPORT_DIR"
echo "$CLI_OUTPUT" > "$OUTPUT_FILE"

echo "========================================"
echo "  Balanced Scan Complete!"
echo "========================================"
echo ""
echo "Output saved to: $OUTPUT_FILE"
echo ""
echo "$CLI_OUTPUT"
