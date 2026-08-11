#!/bin/bash
#
# Scan Band 8 by Operator Frequency Allocation
# This script scans specific EARFCN ranges for each operator in Band 8
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
TIMEOUT=120  # Increased timeout per range
FRAMES=10    # Low frames for quick scan
CHUNK_SIZE=20  # Scan in smaller chunks for better success rate

echo "========================================"
echo "  Band 8 Operator Scan Script"
echo "========================================"
echo ""
echo "Configuration:"
echo "  Gain: ${GAIN} dB"
echo "  Timeout: ${TIMEOUT}s per chunk"
echo "  Frames: ${FRAMES}"
echo "  Chunk size: ${CHUNK_SIZE} EARFCNs"
echo ""

# Function to scan one operator range (in chunks)
scan_operator() {
    local operator="$1"
    local earfcn_start="$2"
    local earfcn_end="$3"
    
    echo "----------------------------------------"
    echo "Scanning: ${operator}"
    echo "  EARFCN Range: ${earfcn_start}-${earfcn_end}"
    echo "----------------------------------------"
    
    # Split into chunks
    local current=$earfcn_start
    while [ $current -le $earfcn_end ]; do
        local end=$((current + CHUNK_SIZE - 1))
        [ $end -gt $earfcn_end ] && end=$earfcn_end
        
        echo -n "  Scanning ${current}-${end}... "
        $CLI --band 8 --gain $GAIN --earfcn-range "${current}-${end}" --timeout $TIMEOUT --frames $FRAMES
        echo ""
        
        current=$((end + 1))
    done
}

# Band 8 Operator Allocations (from frequency_band_map.json)
# Telkomsel: EARFCN 3450-3549 (925.0-934.9 MHz)
# Indosat: EARFCN 3550-3649 (935.0-944.9 MHz)
# XL: EARFCN 3650-3749 (945.0-954.9 MHz)
# Smartfren: EARFCN 3750-3799 (955.0-959.9 MHz)

declare -A OPERATOR_RANGES=(
    ["Telkomsel"]="3450 3549"
    ["Indosat Ooredoo Hutchison"]="3550 3649"
    ["XL Axiata"]="3650 3749"
    ["Smartfren"]="3750 3799"
)

# Main execution
echo "Starting Band 8 scan by operator..."
echo ""

for operator in "${!OPERATOR_RANGES[@]}"; do
    read -r start end <<< "${OPERATOR_RANGES[$operator]}"
    scan_operator "$operator" "$start" "$end"
done

echo "========================================"
echo "  Scan Complete!"
echo "========================================"
echo ""
echo "Summary:"
echo "  - Scanned 4 operator ranges in Band 8"
echo "  - Total EARFCNs: 3450-3799 (350 channels)"
echo "  - Scanned in chunks of ${CHUNK_SIZE}"
echo "  - Expected operators: Telkomsel, Indosat, XL, Smartfren"
echo ""
