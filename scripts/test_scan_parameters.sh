#!/bin/bash
#
# Multi-Pass Smart Scan - Systematic Parameter Tuning
# Not just retry, but changing parameters to find stable detection
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

CLI="python3 -m src.cli.main scan --format json"

echo "========================================"
echo "  Multi-Pass Smart Scan"
echo "========================================"
echo ""

# Parameter matrix to test
declare -a GAINS=(42 48 36)
declare -a FRAMES_LIST=(5 10 15)
declare -a TIMEOUTS=(30 60)

echo "Testing parameter combinations..."
echo ""

# Test each parameter combination
for gain in "${GAINS[@]}"; do
    for frames in "${FRAMES_LIST[@]}"; do
        for timeout in "${TIMEOUTS[@]}"; do
            echo -n "Gain=${gain} Frames=${frames} Timeout=${timeout}s... "
            
            result=$($CLI --band 8 --gain "$gain" --earfcn-range "3490-3499" --timeout "$timeout" --frames "$frames" 2>&1)
            cell_count=$(echo "$result" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(len(data) if isinstance(data, list) else 0)
except:
    print(0)
" 2>/dev/null || echo "0")
            
            if [ "$cell_count" -gt 0 ]; then
                echo "✅ $cell_count cells"
                # Save best configuration
                echo "{\"gain\": $gain, \"frames\": $frames, \"timeout\": $timeout, \"cells\": $cell_count}" > /tmp/best_config.json
            else
                echo "❌ blank"
            fi
        done
    done
done

echo ""
echo "========================================"
echo "  Analysis"
echo "========================================"

if [ -f /tmp/best_config.json ]; then
    echo "Best configuration found:"
    cat /tmp/best_config.json
    echo ""
    
    BEST_GAIN=$(cat /tmp/best_config.json | python3 -c "import json,sys; print(json.load(sys.stdin)['gain'])")
    BEST_FRAMES=$(cat /tmp/best_config.json | python3 -c "import json,sys; print(json.load(sys.stdin)['frames'])")
    BEST_TIMEOUT=$(cat /tmp/best_config.json | python3 -c "import json,sys; print(json.load(sys.stdin)['timeout'])")
    
    echo "Recommended for smart scan:"
    echo "  Gain: $BEST_GAIN"
    echo "  Frames: $BEST_FRAMES"
    echo "  Timeout: $BEST_TIMEOUT"
else
    echo "No configuration detected cells"
fi
