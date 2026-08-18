#!/bin/bash
#
# Smart Band 8 Scan - Skip Empty Ranges Based on Previous Results
# Reads frequency_band_map.json for operator ranges
# Uses exports/*.json to detect which ranges have signals
# Skips scanning ranges with no cells
#

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# CLI command with JSON output
CLI="python3 -m src.cli.main scan --format json"

# Scan parameters
GAIN=42
TIMEOUT=30
FRAMES=5
CHUNK_SIZE=10

echo "========================================"
echo "  Smart Band 8 Scan (Range Skip Mode)"
echo "========================================"
echo ""
echo "Configuration:"
echo "  Gain: ${GAIN} dB"
echo "  Timeout: ${TIMEOUT}s per chunk"
echo "  Frames: ${FRAMES}"
echo "  Chunk size: ${CHUNK_SIZE} EARFCNs"
echo ""

# Function to load previous scan results
load_previous_results() {
    local results_file="/tmp/smart_scan_cache.json"
    
    # Find latest exports and extract cell locations
    python3 -c "
import json
from pathlib import Path
import glob

exports = Path('exports')
if not exports.exists():
    print('{}')
    exit()

all_cells = []
for f in sorted(exports.glob('narrow_scan_*.json')):
    try:
        with open(f) as fh:
            data = json.load(fh)
            if isinstance(data, list):
                all_cells.extend(data)
    except:
        pass

# Extract unique EARFCNs
earfcns = list(set([c['earfcn'] for c in all_cells if 'earfcn' in c]))
print(json.dumps(earfcns))
"
}

# Function to check if range has any cells in previous scan
has_signal_in_range() {
    local start=$1
    local end=$2
    local previous_earfcns="$3"
    
    echo "$previous_earfcns" | python3 -c "
import json
import sys

start = $start
end = $end
data = json.load(sys.stdin)

# Check if any earfcn falls in this range
found = any(start <= e <= end for e in data)
print('true' if found else 'false')
"
}

# Function to scan one operator range (in chunks)
scan_operator() {
    local operator="$1"
    local earfcn_start="$2"
    local earfcn_end="$3"
    local previous_earfcns="$4"
    
    # Check if this range has any signals in previous scans
    local has_signal
    has_signal=$(has_signal_in_range "$earfcn_start" "$earfcn_end" "$previous_earfcns")
    
    if [ "$has_signal" = "false" ]; then
        echo "----------------------------------------"
        echo "SKIPPING: ${operator}"
        echo "  EARFCN Range: ${earfcn_start}-${earfcn_end}"
        echo "  Reason: No signal detected in previous scans"
        echo "----------------------------------------"
        return 0
    fi
    
    echo "----------------------------------------"
    echo "SCANNING: ${operator}"
    echo "  EARFCN Range: ${earfcn_start}-${earfcn_end}"
    echo "----------------------------------------"
    
    # Split into chunks
    local current=$earfcn_start
    while [ $current -le $earfcn_end ]; do
        local end=$((current + CHUNK_SIZE - 1))
        [ $end -gt $earfcn_end ] && end=$earfcn_end
        
        echo -n "  Scanning ${current}-${end}... "
        $CLI --band 8 --gain "$GAIN" --earfcn-range "${current}-${end}" --timeout "$TIMEOUT" --frames "$FRAMES"
        echo ""
        
        current=$((end + 1))
    done
}

# Load frequency band map from JSON
OPERATOR_DATA=$(python3 -c "
import json

with open('data/frequency_band_map.json') as f:
    data = json.load(f)

operators = data['bands']['8']['operators']
for op in operators:
    print(f\"{op['operator']}={op['earfcn_start']} {op['earfcn_end']}\")
")

# Load previous scan results
PREVIOUS_EARFCNS=$(load_previous_results)

# Main execution
echo "Starting Smart Band 8 scan..."
echo ""
echo "Previous scan found cells at EARFCNs: $PREVIOUS_EARFCNS"
echo ""

SCAN_COUNT=0
SKIP_COUNT=0

while IFS='=' read -r operator ranges; do
    read -r start end <<< "$ranges"
    
    # Check if range has signals
    has_signal=$(has_signal_in_range "$start" "$end" "$PREVIOUS_EARFCNS")
    
    if [ "$has_signal" = "true" ]; then
        scan_operator "$operator" "$start" "$end" "$PREVIOUS_EARFCNS"
        SCAN_COUNT=$((SCAN_COUNT + 1))
    else
        SKIP_COUNT=$((SKIP_COUNT + 1))
        echo "----------------------------------------"
        echo "SKIPPING: ${operator}"
        echo "  EARFCN Range: ${start}-${end}"
        echo "  Reason: No signal detected in previous scans"
        echo "----------------------------------------"
    fi
done <<< "$OPERATOR_DATA"

echo "========================================"
echo "  Smart Scan Complete!"
echo "========================================"
echo ""
echo "Summary:"
echo "  - Total operator ranges: $((SCAN_COUNT + SKIP_COUNT))"
echo "  - Ranges scanned: ${SCAN_COUNT}"
echo "  - Ranges skipped: ${SKIP_COUNT}"
echo "  - Expected operators: Telkomsel, Indosat, XL, Smartfren"
echo ""
