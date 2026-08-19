#!/bin/bash
#
# Smart Band 8 Scan v3 - Iterative Two-Step
# 
# Step 1: rtl_power detects general RF activity
# Step 2: srsRAN cell_search scans for actual LTE cells
#
# Note: rtl_power is a rough guide only. srsRAN does the real work.
#
# Usage:
#   ./scripts/smart_scan_v3.sh              # Normal smart scan
#   ./scripts/smart_scan_v3.sh --quick      # Higher threshold, faster
#   ./scripts/smart_scan_v3.sh --full       # Scan all Band 8
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

RTL_POWER_SCRIPT="python3 scripts/rtl_power_detector.py"
CELL_SEARCH="/home/pi/srsRAN_4G/build/lib/examples/cell_search"

# Configuration
BAND_START=925.0
BAND_END=960.0
RESOLUTION=100  # kHz

# Threshold settings
NORMAL_THRESHOLD=-70
QUICK_THRESHOLD=-60

# srsRAN settings
GAIN=20
FRAMES=15

# Flags
QUICK_SCAN=false
FULL_SCAN=false

if [ "$1" = "--quick" ]; then
    QUICK_SCAN=true
elif [ "$1" = "--full" ]; then
    FULL_SCAN=true
fi

THRESHOLD=$NORMAL_THRESHOLD
if [ "$QUICK_SCAN" = true ]; then
    THRESHOLD=$QUICK_THRESHOLD
fi

EXPORTS_DIR="./exports"
mkdir -p "$EXPORTS_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$EXPORTS_DIR/smart_scan_v3_${TIMESTAMP}.log"
RESULTS_FILE="$EXPORTS_DIR/smart_scan_v3_${TIMESTAMP}.json"

echo "========================================"
echo "  Smart Band 8 Scan v3"
echo "========================================"
echo ""
echo "Timestamp: $TIMESTAMP"
echo "Method: rtl_power (guide) + srsRAN (scanner)"
echo ""

# Initialize results
echo "[]" > "$RESULTS_FILE"
> "$LOG_FILE"
> "$LOG_FILE.cells"

# Function to convert MHz to EARFCN for Band 8 DL
# Formula: freq_MHz = 880 + earfcn * 0.1
# So: earfcn = (freq_MHz - 880) / 0.1
mhz_to_earfcn() {
    local mhz=$1
    echo $(echo "scale=0; ($mhz - 880) * 10" | bc)
}

# Function to scan a specific EARFCN range
scan_earfcn_range() {
    local earfcn_start=$1
    local earfcn_end=$2
    local verbose=$3
    
    if [ $verbose = true ]; then
        echo "  Scanning EARFCN ${earfcn_start}-${earfcn_end}..."
    fi
    
    local output
    output=$($CELL_SEARCH -b 8 -g $GAIN -n $FRAMES -s $earfcn_start -e $earfcn_end 2>&1) || true
    
    # Check for found cells
    local cell_count
    cell_count=$(echo "$output" | grep -c "Found CELL" || echo "0")
    
    if [ $cell_count -gt 0 ]; then
        echo "$output" >> "$log_file"
        echo "    ✓ Found $cell_count cell(s)"
        
        # Extract cell details
        echo "$output" | grep "Found CELL" | while read -r line; do
            local freq=$(echo "$line" | sed -E 's/.*Found CELL ([0-9.]+) MHz.*/\1/')
            local earfcn=$(echo "$line" | sed -E 's/.*EARFCN=([0-9]+).*/\1/')
            local phyid=$(echo "$line" | sed -E 's/.*PHYID=([0-9]+).*/\1/')
            local prb=$(echo "$line" | sed -E 's/.*([0-9]+) PRB.*/\1/')
            local ports=$(echo "$line" | sed -E 's/.*([0-9]+) ports.*/\1/')
            local pss_power=$(echo "$line" | sed -E 's/.*PSS power=([0-9.-]+) dBm.*/\1/')
            
            echo "{\"freq_mhz\": $freq, \"earfcn\": $earfcn, \"phy_id\": $phyid, \"prb\": $prb, \"ports\": $ports, \"pss_power_dbm\": $pss_power}" >> "${LOG_FILE}.cells"
        done
        
        return 0
    else
        return 1
    fi
}

# ============================================================
# STEP 1: Spectrum Survey with rtl_power
# ============================================================
echo "----------------------------------------"
echo "STEP 1: Spectrum Survey (rtl_power)"
echo "----------------------------------------"

survey_output=$($RTL_POWER_SCRIPT \
    --band-start $BAND_START \
    --band-end $BAND_END \
    --resolution $RESOLUTION \
    --gain 36 \
    --integration 0.5 \
    --output json \
    --threshold $THRESHOLD 2>/dev/null) || true

echo "$survey_output" > "$EXPORTS_DIR/spectrum_survey_v3_${TIMESTAMP}.json"

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
    echo "  No signal activity detected"
else
    chunk_count=$(echo "$chunks" | wc -l)
    echo "  Detected ${chunk_count} active chunk(s)"
    echo "$chunks" | while read -r start end; do
        freq_start=$(echo "scale=1; $start / 10" | bc)
        freq_end=$(echo "scale=1; ($end + 1) / 10" | bc)
        earfcn_start=$(mhz_to_earfcn $(echo "925 + $freq_start" | bc))
        earfcn_end=$(mhz_to_earfcn $(echo "925 + $freq_end" | bc))
        echo "    ${start}-${end} kHz -> EARFCN ${earfcn_start}-${earfcn_end}"
    done
fi

# ============================================================
# STEP 2: Cell Search Strategy
# ============================================================
echo ""
echo "----------------------------------------"
echo "STEP 2: Targeted Cell Search (srsRAN)"
echo "----------------------------------------"

# If full scan, scan entire Band 8
if [ "$FULL_SCAN" = true ]; then
    echo "  Mode: Full Band 8 scan (3450-3799)"
    scan_earfcn_range 3450 3799 true
    echo ""
    echo "  Full scan complete!"
else
    # Use chunk-based scanning from rtl_power
    if [ -n "$chunks" ]; then
        echo "  Mode: Chunk-based scanning"
        
        total_cells=0
        scanned_chunks=0
        
        while read -r chunk_start chunk_end; do
            [ -z "$chunk_start" ] && continue
            
            # Convert chunk to EARFCN
            freq_start=$(echo "scale=1; $chunk_start / 10" | bc)
            freq_end=$(echo "scale=1; ($chunk_end + 1) / 10" | bc)
            earfcn_start=$(mhz_to_earfcn $(echo "925 + $freq_start" | bc))
            earfcn_end=$(mhz_to_earfcn $(echo "925 + $freq_end" | bc))
            
            # Clamp to valid range
            [ $earfcn_start -lt 3450 ] && earfcn_start=3450
            [ $earfcn_end -gt 3799 ] && earfcn_end=3799
            
            if scan_earfcn_range $earfcn_start $earfcn_end false; then
                scanned_chunks=$((scanned_chunks + 1))
            fi
            
        done <<< "$chunks"
        
        echo ""
        echo "  Scanned ${scanned_chunks} chunk(s)"
    else
        # Fallback: scan by operator ranges
        echo "  Mode: Operator-based scanning (fallback)"
        echo "  Ranges: Telkomsel (3450-3549), Indosat (3550-3649), XL (3650-3749), Smartfren (3750-3799)"
        
        scan_earfcn_range 3450 3549 false  # Telkomsel
        scan_earfcn_range 3550 3649 false  # Indosat
        scan_earfcn_range 3650 3749 false  # XL
        scan_earfcn_range 3750 3799 false  # Smartfren
    fi
fi

# ============================================================
# Summary
# ============================================================
echo ""
echo "========================================"
echo "  Scan Complete!"
echo "========================================"
echo ""

if [ -s "$LOG_FILE.cells" ]; then
    cell_count=$(wc -l < "$LOG_FILE.cells")
    echo "Total cells found: ${cell_count}"
    echo ""
    echo "Cell Details:"
    cat "$LOG_FILE.cells" | while read -r line; do
        echo "  $line"
    done
else
    echo "No cells found in this scan."
fi

echo ""
echo "Output files:"
echo "  Results: $RESULTS_FILE"
echo "  Log: $LOG_FILE"
echo "  Cells: ${LOG_FILE}.cells"
