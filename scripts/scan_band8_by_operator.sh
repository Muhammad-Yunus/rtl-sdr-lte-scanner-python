#!/bin/bash
#
# Scan Band 8 by Operator Frequency Allocation
# This script scans specific EARFCN ranges for each operator in Band 8
# All results are saved to exports/ as JSON files
#

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Output directory
EXPORTS_DIR="./exports"
mkdir -p "$EXPORTS_DIR"

# CLI command with JSON output
CLI="python3 -m src.cli.main scan --format json"

# Scan parameters
GAIN=42
TIMEOUT=60
FRAMES=5
CHUNK_SIZE=20

echo "========================================"
echo "  Band 8 Operator Scan Script"
echo "========================================"
echo ""
echo "Configuration:"
echo "  Gain: ${GAIN} dB"
echo "  Timeout: ${TIMEOUT}s per chunk"
echo "  Frames: ${FRAMES}"
echo "  Chunk size: ${CHUNK_SIZE} EARFCNs"
echo "  Output: ${EXPORTS_DIR}/"
echo ""

# Track all cells found
ALL_CELLS_FILE="$EXPORTS_DIR/_temp_all_cells.json"
echo "[]" > "$ALL_CELLS_FILE"

# Function to scan one operator range (in chunks)
scan_operator() {
    local operator="$1"
    local earfcn_start="$2"
    local earfcn_end="$3"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    
    echo "----------------------------------------"
    echo "Scanning: ${operator}"
    echo "  EARFCN Range: ${earfcn_start}-${earfcn_end}"
    echo "----------------------------------------"
    
    # Collect all cells for this operator
    local operator_cells="[]"
    
    # Split into chunks
    local current=$earfcn_start
    while [ $current -le $earfcn_end ]; do
        local end=$((current + CHUNK_SIZE - 1))
        [ $end -gt $earfcn_end ] && end=$earfcn_end
        
        echo -n "  Scanning ${current}-${end}... "
        
        # Capture output to file
        local chunk_file="$EXPORTS_DIR/operator_${operator}_${current}_${timestamp}.json"
        $CLI --band 8 --gain "$GAIN" --earfcn-range "${current}-${end}" --timeout "$TIMEOUT" --frames "$FRAMES" > "$chunk_file" 2>&1
        
        # Check if we got valid JSON with cells
        local cell_count=$(python3 -c "
import json
try:
    with open('$chunk_file') as f:
        data = json.load(f)
    if isinstance(data, list):
        print(len(data))
    else:
        print(0)
except:
    print(0)
" 2>/dev/null || echo "0")
        
        echo "  $cell_count cells found"
        
        # Merge with operator cells
        if [ "$cell_count" -gt 0 ]; then
            operator_cells=$(python3 -c "
import json
with open('$operator_cells_file') as f:
    old = json.load(f)
with open('$chunk_file') as f:
    new = json.load(f)
merged = old + new
print(json.dumps(merged))
" 2>/dev/null || echo "$operator_cells")
        fi
        
        current=$((end + 1))
    done
    
    # Save operator results
    if [ "$operator_cells" != "[]" ]; then
        local operator_file="$EXPORTS_DIR/operator_${operator}_${timestamp}.json"
        echo "$operator_cells" > "$operator_file"
        echo "  Saved: $operator_file"
    fi
    
    # Merge to all cells
    ALL_CELLS_FILE=$(python3 -c "
import json
with open('$ALL_CELLS_FILE') as f:
    all = json.load(f)
new = json.loads('$operator_cells')
merged = all + new
print(json.dumps(merged))
" 2>/dev/null || echo "$ALL_CELLS_FILE")
    echo "$ALL_CELLS_FILE" > "$ALL_CELLS_FILE"
}

# Band 8 Operator Allocations (from frequency_band_map.json)
declare -A OPERATOR_RANGES=(
    ["Telkomsel"]="3450 3549"
    ["Indosat Ooredoo Hutchison"]="3550 3649"
    ["XL Axiata"]="3650 3749"
    ["Smartfren"]="3750 3799"
)

# Main execution
echo "Starting Band 8 scan by operator..."
echo ""

SCAN_COUNT=0

for operator in "${!OPERATOR_RANGES[@]}"; do
    read -r start end <<< "${OPERATOR_RANGES[$operator]}"
    scan_operator "$operator" "$start" "$end"
    SCAN_COUNT=$((SCAN_COUNT + 1))
done

# Clean up temp file
rm -f "$ALL_CELLS_FILE"

echo "========================================"
echo "  Scan Complete!"
echo "========================================"
echo ""
echo "Summary:"
echo "  - Scanned ${SCAN_COUNT} operator ranges in Band 8"
echo "  - Total EARFCNs: 3450-3799 (350 channels)"
echo "  - Scanned in chunks of ${CHUNK_SIZE}"
echo "  - Results saved to: ${EXPORTS_DIR}/"
echo ""
echo "  Expected operators: Telkomsel, Indosat, XL, Smartfren"
echo ""

# List all exported files
echo "Exported Files:"
ls -la "$EXPORTS_DIR"/*.json 2>/dev/null | grep -v "_temp" | tail -10
echo ""
