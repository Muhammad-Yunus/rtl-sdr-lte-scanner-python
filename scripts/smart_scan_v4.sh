#!/bin/bash
#
# Smart Band 8 Scan v4 - Optimized Two-Step
#
# Step 1: rtl_power - rough spectrum overview (for visualization)
# Step 2: srsRAN cell_search - actual LTE cell discovery
#
# Since rtl_power shows full-band noise, we use a hybrid approach:
# - Quick rtl_power scan to confirm no extreme interference
# - Direct srsRAN scanning by operator EARFCN ranges
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

RTL_POWER_SCRIPT="python3 scripts/rtl_power_detector.py"
CELL_SEARCH="/home/pi/srsRAN_4G/build/lib/examples/cell_search"

# Configuration
BAND_START=925.0
BAND_END=960.0
RESOLUTION=100  # kHz

# srsRAN settings
GAIN=20
FRAMES=15

# Output
EXPORTS_DIR="./exports"
mkdir -p "$EXPORTS_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$EXPORTS_DIR/smart_scan_v4_${TIMESTAMP}.log"
RESULTS_FILE="$EXPORTS_DIR/smart_scan_v4_${TIMESTAMP}.json"

echo "========================================"
echo "  Smart Band 8 Scan v4"
echo "========================================"
echo ""
echo "Timestamp: $TIMESTAMP"
echo ""

# Initialize results
echo "[]" > "$RESULTS_FILE"
> "$LOG_FILE"
> "$LOG_FILE.cells"

# ============================================================
# STEP 1: Quick Spectrum Check (rtl_power)
# ============================================================
echo "----------------------------------------"
echo "STEP 1: Spectrum Check (rtl_power)"
echo "----------------------------------------"

quick_survey=$($RTL_POWER_SCRIPT \
    --band-start $BAND_START \
    --band-end $BAND_END \
    --resolution 1000  # 1 MHz chunks for quick check
    --gain 36 \
    --integration 0.3 \
    --output json \
    2>/dev/null) || true

# Parse and display
python3 -c "
import json, sys
try:
    data = json.loads('$quick_survey')
    chunks = data.get('chunks', [])
    if not chunks:
        print('  Result: Clean spectrum (no significant signals)')
    else:
        for c in chunks:
            start_mhz = 925.0 + c['start'] / 10
            end_mhz = 925.0 + (c['end'] + 1) / 10
            print(f'  Signal detected: {start_mhz:.1f}-{end_mhz:.1f} MHz (power: {c[\"power\"]:.1f} dBm)')
except:
    print('  Result: Could not parse spectrum data')
" 2>/dev/null

echo "$quick_survey" > "$EXPORTS_DIR/spectrum_quick_${TIMESTAMP}.json"

# ============================================================
# STEP 2: Targeted Cell Search (srsRAN)
# ============================================================
echo ""
echo "----------------------------------------"
echo "STEP 2: LTE Cell Search (srsRAN)"
echo "----------------------------------------"

# Operator EARFCN ranges (Indonesia Band 8)
declare -A OPERATORS=(
    ["Telkomsel"]="3450 3549"
    ["Indosat"]="3550 3649"
    ["XL Axiata"]="3650 3749"
    ["Smartfren"]="3750 3799"
)

total_cells=0
total_scans=0

for operator in Telkomsel Indosat XL_Axiata Smartfren; do
    range="${OPERATORS[$operator]}"
    read -r start end <<< "$range"
    
    echo ""
    echo "  Scanning $operator (EARFCN ${start}-${end})..."
    
    # Scan in chunks of 10 EARFCNs for efficiency
    current=$start
    while [ $current -le $end ]; do
        chunk_end=$((current + 9))
        [ $chunk_end -gt $end ] && chunk_end=$end
        
        # Run cell_search
        output=$($CELL_SEARCH -b 8 -g $GAIN -n $FRAMES -s $current -e $chunk_end 2>&1) || true
        
        # Check for cells
        cell_count=$(echo "$output" | grep -c "Found CELL" || echo "0")
        
        if [ $cell_count -gt 0 ]; then
            echo "    EARFCN ${current}-${chunk_end}: Found $cell_count cell(s)"
            total_cells=$((total_cells + cell_count))
            total_scans=$((total_scans + 1))
            
            # Extract cell details
            echo "$output" | grep "Found CELL" | while read -r line; do
                local_freq=$(echo "$line" | sed -E 's/.*Found CELL ([0-9.]+) MHz.*/\1/')
                local_earfcn=$(echo "$line" | sed -E 's/.*EARFCN=([0-9]+).*/\1/')
                local_phyid=$(echo "$line" | sed -E 's/.*PHYID=([0-9]+).*/\1/')
                local_prb=$(echo "$line" | sed -E 's/.*([0-9]+) PRB.*/\1/')
                local_ports=$(echo "$line" | sed -E 's/.*([0-9]+) ports.*/\1/')
                local_power=$(echo "$line" | sed -E 's/.*PSS power=([0-9.-]+) dBm.*/\1/')
                
                echo "{\"operator\": \"$operator\", \"freq_mhz\": $local_freq, \"earfcn\": $local_earfcn, \"phy_id\": $local_phyid, \"prb\": $local_prb, \"ports\": $local_ports, \"pss_power_dbm\": $local_power}" >> "${LOG_FILE}.cells"
            done
            
            echo "$output" >> "$LOG_FILE"
        fi
        
        current=$((chunk_end + 1))
    done
done

# ============================================================
# Summary
# ============================================================
echo ""
echo "========================================"
echo "  Scan Complete!"
echo "========================================"
echo ""
echo "Summary:"
echo "  Total scans: ${total_scans}"
echo "  Total cells: ${total_cells}"
echo ""

if [ -s "$LOG_FILE.cells" ]; then
    echo "Detected Cells:"
    echo "----------------------------------------"
    cat "$LOG_FILE.cells" | while read -r line; do
        echo "  $line"
    done
else
    echo "No LTE cells detected in Band 8."
fi

echo ""
echo "Output files:"
echo "  Results: $RESULTS_FILE"
echo "  Log: $LOG_FILE"
echo "  Cells: ${LOG_FILE}.cells"
echo "  Spectrum: $EXPORTS_DIR/spectrum_quick_${TIMESTAMP}.json"
