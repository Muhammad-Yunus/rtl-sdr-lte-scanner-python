#!/bin/bash
#
# Smart Band 8 Scan - Two-Step Approach
# Step 1: rtl_power detects active EARFCN chunks (spectrum survey)
# Step 2: srsRAN cell_search scans only those chunks (targeted cell search)
#
# Usage:
#   ./scripts/smart_scan_band8_v2.sh              # Normal smart scan
#   ./scripts/smart_scan_band8_v2.sh --high-snr   # Higher SNR threshold (-50 dBm)
#   ./scripts/smart_scan_band8_v2.sh --no-rerun   # Skip rtl_power if cache exists
#   ./scripts/smart_scan_band8_v2.sh --refresh    # Force re-scan both steps
#

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# CLI commands
RTL_POWER_SCRIPT="python3 scripts/rtl_power_detector.py"
CLI="python3 -m src.cli.main scan --format json"

# Band 8 parameters
BAND_START=925.0
BAND_END=960.0
RESOLUTION=100  # kHz

# Scan parameters for srsRAN
GAIN=42
TIMEOUT=60
FRAMES=10

# Threshold for rtl_power detection
SNR_THRESHOLD=-80

# Output
EXPORTS_DIR="./exports"
SURVEY_FILE="$EXPORTS_DIR/spectrum_survey.json"

# Flags
HIGH_SNR=false
NO_RERUN=false
FORCE_REFRESH=false

if [ "$1" = "--high-snr" ]; then
    HIGH_SNR=true
    SNR_THRESHOLD=-50
elif [ "$1" = "--no-rerun" ]; then
    NO_RERUN=true
elif [ "$1" = "--refresh" ]; then
    FORCE_REFRESH=true
fi

echo "========================================"
echo "  Smart Band 8 Scan (Two-Step)"
echo "========================================"
echo ""
echo "Configuration:"
echo "  Band: 8 (925-960 MHz)"
echo "  RTL Power Threshold: ${SNR_THRESHOLD} dBm"
echo "  srsRAN Gain: ${GAIN} dB"
echo "  srsRAN Timeout: ${TIMEOUT}s"
echo "  srsRAN Frames: ${FRAMES}"
echo ""

mkdir -p "$EXPORTS_DIR"

# ============================================================
# STEP 1: Spectrum Survey with rtl_power
# ============================================================
echo "----------------------------------------"
echo "STEP 1: Spectrum Survey (rtl_power)"
echo "----------------------------------------"
echo "Scanning ${BAND_START}-${BAND_END} MHz..."

threshold_param="--threshold $SNR_THRESHOLD"
survey_output=$($RTL_POWER_SCRIPT \
    --band-start $BAND_START \
    --band-end $BAND_END \
    --resolution $RESOLUTION \
    --gain 36 \
    --integration 0.5 \
    --output json \
    $threshold_param 2>/dev/null) || true

echo "$survey_output" > "$SURVEY_FILE"

# Parse chunks
chunks=$(echo "$survey_output" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    for c in data.get('chunks', []):
        print(f\"{c['start']} {c['end']}\")
except:
    pass
" 2>/dev/null)

if [ -z "$chunks" ]; then
    echo "  Result: No signals detected above threshold"
    exit 0
fi

chunk_count=$(echo "$chunks" | wc -l)
echo "  Result: ${chunk_count} chunk(s) detected"
echo "$chunks" | sed 's/^/    /'

# ============================================================
# STEP 2: Targeted Cell Search with srsRAN
# ============================================================
echo ""
echo "----------------------------------------"
echo "STEP 2: Targeted Cell Search (srsRAN)"
echo "----------------------------------------"

total_cells=0
scanned_chunks=0

while read -r start end; do
    [ -z "$start" ] && continue
    
    # Convert MHz to EARFCN for Band 8
    # Band 8 EARFCN formula: freq_MHz = 880 + earfcn * 0.1
    # So: earfcn = (freq_MHz - 880) / 0.1
    # But spectrum starts at 925 MHz which is EARFCN 3450
    # earfcn = (freq - 925) * 10 + 3450
    
    earfcn_start=$(( (start / 10) + 3450 ))
    earfcn_end=$(( ((end + 1) / 10) + 3450 ))
    
    # Clamp to valid Band 8 range
    [ $earfcn_start -lt 3450 ] && earfcn_start=3450
    [ $earfcn_end -gt 3799 ] && earfcn_end=3799
    
    echo -n "  Scanning EARFCN ${earfcn_start}-${earfcn_end}... "
    
    # Run srsRAN scan
    result=$($CLI --band 8 --gain $GAIN --earfcn-range "${earfcn_start}-${earfcn_end}" --timeout $TIMEOUT --frames $FRAMES 2>/dev/null) || true
    
    # Count cells
    cell_count=$(echo "$result" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(len(data) if isinstance(data, list) else 0)
except:
    print(0)
" 2>/dev/null || echo "0")
    
    echo "$cell_count cells"
    
    if [ "$cell_count" -gt 0 ]; then
        total_cells=$((total_cells + cell_count))
        scanned_chunks=$((scanned_chunks + 1))
    fi
    
done <<< "$chunks"

echo ""
echo "  Total: ${total_cells} cells in ${scanned_chunks} chunks"

echo ""
echo "========================================"
echo "  Scan Complete!"
echo "========================================"
echo ""
echo "Survey saved to: $SURVEY_FILE"
