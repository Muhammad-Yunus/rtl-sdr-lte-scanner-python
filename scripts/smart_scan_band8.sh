#!/bin/bash
#
# Smart Band 8 Scan - Skip Empty CHUNKS with Retry
# Scans only EARFCN segments that have signals in cache
# Includes retry mechanism for inconsistent signals
#
# Usage:
#   ./scripts/smart_scan_band8.sh              # Normal smart scan (use cache)
#   ./scripts/smart_scan_band8.sh --retry      # Enable retry for empty chunks
#   ./scripts/smart_scan_band8.sh --refresh    # Re-scan all ranges, update cache
#   ./scripts/smart_scan_band8.sh --invalidate # Clear cache, full scan, rebuild
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
TIMEOUT=60
FRAMES=5
CHUNK_SIZE=10
MAX_RETRIES=3  # Retry empty chunks up to 3 times
RETRY_DELAY=2  # Seconds between retries

# Check for flags
REFRESH_CACHE=false
INVALIDATE_CACHE=false
ENABLE_RETRY=false

if [ "$1" = "--refresh" ]; then
    REFRESH_CACHE=true
    echo "Mode: Refresh cache (re-scan all ranges)"
elif [ "$1" = "--invalidate" ]; then
    INVALIDATE_CACHE=true
    echo "Mode: Invalidate cache (clear and re-scan all)"
elif [ "$1" = "--retry" ]; then
    ENABLE_RETRY=true
    echo "Mode: Enable retry for inconsistent chunks"
fi

echo "========================================"
echo "  Smart Band 8 Scan (Chunk Mode)"
echo "========================================"
echo ""
echo "Configuration:"
echo "  Gain: ${GAIN} dB"
echo "  Timeout: ${TIMEOUT}s per chunk"
echo "  Frames: ${FRAMES}"
echo "  Chunk size: ${CHUNK_SIZE} EARFCNs"
echo "  Max retries: ${MAX_RETRIES} (${ENABLE_RETRY:+enabled, disabled})"
echo ""

# Cache file
CACHE_FILE="data/smart_scan_cache.json"

# Handle invalidate mode
if [ "$INVALIDATE_CACHE" = true ]; then
    echo "Invalidating cache..."
    if [ -f "$CACHE_FILE" ]; then
        rm "$CACHE_FILE"
        echo "  Cache cleared: $CACHE_FILE"
    else
        echo "  No cache to clear"
    fi
    echo "Running full scan to rebuild cache..."
    echo ""
    ./scripts/scan_band8_by_operator.sh
    echo ""
    echo "Updating cache..."
    ./scripts/init_scan_cache.sh
    echo ""
    echo "Cache refreshed. Run without --invalidate flag for normal smart scan."
    exit 0
fi

# Handle refresh mode
if [ "$REFRESH_CACHE" = true ]; then
    echo "Forcing full re-scan..."
    ./scripts/scan_band8_by_operator.sh
    echo ""
    echo "Updating cache..."
    ./scripts/init_scan_cache.sh
    echo ""
fi

# Check if cache exists
if [ ! -f "$CACHE_FILE" ]; then
    echo "ERROR: Cache file not found: $CACHE_FILE"
    echo "Please run one of:"
    echo "  ./scripts/smart_scan_band8.sh --invalidate  # Full scan + rebuild cache"
    echo "  ./scripts/init_scan_cache.sh                 # Build from exports/"
    exit 1
fi

echo "Loading cache from: $CACHE_FILE"

# Extract active EARFCNs from cache
python3 -c "
import json

with open('$CACHE_FILE') as f:
    data = json.load(f)

all_earfcns = []
for op, info in data.items():
    all_earfcns.extend(info['earfcns'])

print(json.dumps(sorted(set(all_earfcns))))
" > /tmp/smart_scan_active_earfcns.json

ACTIVE_EARFCNS=$(cat /tmp/smart_scan_active_earfcns.json)
echo "Active EARFCNs in cache: $ACTIVE_EARFCNS"
echo ""

# Function to find which chunks have signals
find_active_chunks() {
    local start=$1
    local end=$2
    local earfcns_json="$3"
    
    echo "$earfcns_json" | python3 -c "
import json
import sys

start = $start
end = $end
chunk_size = $CHUNK_SIZE
data = json.load(sys.stdin)

active_chunks = []
current = start
while current <= end:
    chunk_end = min(current + chunk_size - 1, end)
    has_signal = any(current <= e <= chunk_end for e in data)
    
    if has_signal:
        active_chunks.append(f'{current}-{chunk_end}')
    
    current = chunk_end + 1

print(','.join(active_chunks) if active_chunks else 'NONE')
"
}

# Function to scan specific chunks with optional retry
scan_chunks() {
    local operator="$1"
    local earfcn_start="$2"
    local earfcn_end="$3"
    local active_chunks="$4"
    
    if [ "$active_chunks" = "NONE" ]; then
        echo "----------------------------------------"
        echo "SKIPPING: ${operator}"
        echo "  EARFCN Range: ${earfcn_start}-${earfcn_end}"
        echo "  Reason: No active chunks in cache"
        echo "----------------------------------------"
        return 0
    fi
    
    echo "----------------------------------------"
    echo "SCANNING: ${operator}"
    echo "  EARFCN Range: ${earfcn_start}-${earfcn_end}"
    echo "  Active chunks: ${active_chunks}"
    echo "----------------------------------------"
    
    IFS=',' read -ra CHUNKS <<< "$active_chunks"
    for chunk in "${CHUNKS[@]}"; do
        local chunk_start=$(echo "$chunk" | cut -d'-' -f1)
        local chunk_end=$(echo "$chunk" | cut -d'-' -f2)
        
        echo -n "  Scanning ${chunk_start}-${chunk_end}... "
        
        # Try scanning with optional retry
        local scan_result
        local retries=0
        local success=false
        
        while [ $retries -lt $MAX_RETRIES ] && [ "$success" = false ]; do
            scan_result=$($CLI --band 8 --gain "$GAIN" --earfcn-range "${chunk_start}-${chunk_end}" --timeout "$TIMEOUT" --frames "$FRAMES" 2>&1)
            
            # Check if we got any cells
            local cell_count=$(echo "$scan_result" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(len(data) if isinstance(data, list) else 0)
except:
    print(0)
" 2>/dev/null || echo "0")
            
            if [ "$cell_count" -gt 0 ]; then
                echo "$scan_result"
                success=true
            elif [ "$ENABLE_RETRY" = true ] && [ $retries -lt $((MAX_RETRIES - 1)) ]; then
                echo "[EMPTY - retry ${retries}/$MAX_RETRIES]"
                sleep $RETRY_DELAY
                retries=$((retries + 1))
            else
                echo "[]"
            fi
        done
        
        echo ""
    done
}

# Load frequency band map
OPERATOR_DATA=$(python3 -c "
import json

with open('data/frequency_band_map.json') as f:
    data = json.load(f)

operators = data['bands']['8']['operators']
for op in operators:
    print(f\"{op['operator']}={op['earfcn_start']} {op['earfcn_end']}\")
")

# Main execution
echo "Starting Smart Band 8 scan (chunk-level skip)..."
echo ""

SCAN_COUNT=0
SKIP_COUNT=0
TOTAL_CHUNKS=0
SCANNED_CHUNKS=0
RETRY_COUNT=0

while IFS='=' read -r operator ranges; do
    read -r start end <<< "$ranges"
    
    active_chunks=$(find_active_chunks "$start" "$end" "$ACTIVE_EARFCNS")
    
    if [ "$active_chunks" = "NONE" ]; then
        SKIP_COUNT=$((SKIP_COUNT + 1))
        echo "----------------------------------------"
        echo "SKIPPING: ${operator}"
        echo "  EARFCN Range: ${start}-${end}"
        echo "  Reason: No active chunks in cache"
        echo "----------------------------------------"
    else
        scan_chunks "$operator" "$start" "$end" "$active_chunks"
        SCAN_COUNT=$((SCAN_COUNT + 1))
        
        IFS=',' read -ra CHUNKS <<< "$active_chunks"
        SCANNED_CHUNKS=$((SCANNED_CHUNKS + ${#CHUNKS[@]}))
    fi
    
    total_chunks=$(( (end - start + 1 + CHUNK_SIZE - 1) / CHUNK_SIZE ))
    TOTAL_CHUNKS=$((TOTAL_CHUNKS + total_chunks))
    
done <<< "$OPERATOR_DATA"

echo "========================================"
echo "  Smart Scan Complete!"
echo "========================================"
echo ""
echo "Summary:"
echo "  - Total operator ranges: $((SCAN_COUNT + SKIP_COUNT))"
echo "  - Operators scanned: ${SCAN_COUNT}"
echo "  - Operators skipped: ${SKIP_COUNT}"
echo "  - Chunks scanned: ${SCANNED_CHUNKS}/${TOTAL_CHUNKS}"
echo "  - Skip rate: $(( (TOTAL_CHUNKS - SCANNED_CHUNKS) * 100 / TOTAL_CHUNKS ))%"
echo ""
echo "Usage:"
echo "  ./scripts/smart_scan_band8.sh              # Normal smart scan"
echo "  ./scripts/smart_scan_band8.sh --retry      # Enable retry for empty chunks"
echo "  ./scripts/smart_scan_band8.sh --refresh    # Re-scan all ranges"
echo "  ./scripts/smart_scan_band8.sh --invalidate # Clear cache & re-scan all"
echo ""
