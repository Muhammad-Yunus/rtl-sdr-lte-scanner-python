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
TIMEOUT=90  # Increased from 30s - full band scans need more time
FRAMES=10   # Low frames for quick scan

echo "========================================"
echo "  Band 8 Operator Scan Script"
echo "========================================"
echo ""
echo "Configuration:"
echo "  Gain: ${GAIN} dB"
echo "  Timeout: ${TIMEOUT}s per range"
echo "  Frames: ${FRAMES}"
echo ""

# Band 8 Operator Allocations (from frequency_band_map.json)
# Telkomsel: EARFCN 3450-3549 (925.0-934.9 MHz)
# Indosat: EARFCN 3550-3649 (935.0-944.9 MHz)
# XL: EARFCN 3650-3749 (945.0-954.9 MHz)
# Smartfren: EARFCN 3750-3799 (955.0-959.9 MHz)

declare -A OPERATOR_RANGES=(
    ["Telkomsel"]="3450-3549"
    ["Indosat Ooredoo Hutchison"]="3550-3649"
    ["XL Axiata"]="3650-3749"
    ["Smartfren"]="3750-3799"
)

# Function to scan one operator range
scan_operator() {
    local operator="$1"
    local earfcn_range="$2"
    
    echo "----------------------------------------"
    echo "Scanning: ${operator}"
    echo "  EARFCN Range: ${earfcn_range}"
    echo "----------------------------------------"
    
    $CLI --band 8 --gain $GAIN --earfcn-range "$earfcn_range" --timeout $TIMEOUT --frames $FRAMES
    
    echo ""
}

# Main execution
echo "Starting Band 8 scan by operator..."
echo ""

for operator in "${!OPERATOR_RANGES[@]}"; do
    range="${OPERATOR_RANGES[$operator]}"
    scan_operator "$operator" "$range"
done

echo "========================================"
echo "  Scan Complete!"
echo "========================================"
echo ""
echo "Summary:"
echo "  - Scanned 4 operator ranges in Band 8"
echo "  - Total EARFCNs: 3450-3799 (350 channels)"
echo "  - Expected operators: Telkomsel, Indosat, XL, Smartfren"
echo ""
