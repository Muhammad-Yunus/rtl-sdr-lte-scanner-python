#!/bin/bash
#
# Initialize Smart Scan Cache
# Run initial full scan and save active EARFCNs to cache file
#
# Usage:
#   ./scripts/init_scan_cache.sh [--full-scan]
#
# Options:
#   --full-scan    Force re-scan all ranges (default: use existing exports)
#

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

CACHE_FILE="data/smart_scan_cache.json"
EXPORTS_DIR="exports"

echo "========================================"
echo "  Smart Scan Cache Initializer"
echo "========================================"
echo ""

# Check if we should force full scan
FORCE_SCAN=false
if [ "$1" = "--full-scan" ]; then
    FORCE_SCAN=true
    echo "Mode: Full scan forced"
else
    echo "Mode: Using existing exports (add --full-scan to re-scan)"
fi
echo ""

# Load frequency band map
echo "Loading frequency band map..."
OPERATOR_DATA=$(python3 -c "
import json
with open('data/frequency_band_map.json') as f:
    data = json.load(f)
operators = data['bands']['8']['operators']
for op in operators:
    print(f\"{op['operator']}={op['earfcn_start']} {op['earfcn_end']}\")
")

# Extract active EARFCNs from existing exports
extract_active_earfcns() {
    python3 -c "
import json
from pathlib import Path
from collections import defaultdict

exports_dir = Path('$EXPORTS_DIR')
all_cells = []

for f in sorted(exports_dir.glob('*.json')):
    try:
        with open(f) as fh:
            data = json.load(fh)
            if isinstance(data, list):
                for cell in data:
                    if 'earfcn' in cell and cell['earfcn'] is not None:
                        all_cells.append(cell)
    except:
        pass

# Group by operator and earfcn
operator_earfcns = defaultdict(list)
for cell in all_cells:
    op = cell.get('operator', 'Unknown')
    earfcn = cell['earfcn']
    rsrp = cell.get('rsrp', 0)
    operator_earfcns[op].append({'earfcn': earfcn, 'rsrp': rsrp})

# Build output structure
result = {}
for op, cells in sorted(operator_earfcns.items()):
    unique_earfcns = {}
    for cell in cells:
        ef = cell['earfcn']
        if ef not in unique_earfcns or cell['rsrp'] > unique_earfcns[ef]['rsrp']:
            unique_earfcns[ef] = cell
    
    result[op] = {
        'earfcns': sorted(unique_earfcns.keys()),
        'cell_count': len(unique_earfcns),
        'best_rsrp': max(c['rsrp'] for c in unique_earfcns.values())
    }

print(json.dumps(result, indent=2))
"
}

if [ "$FORCE_SCAN" = true ]; then
    echo "Force mode: You need to run scan_band8_by_operator.sh first"
    echo ""
    echo "Run this command:"
    echo "  ./scripts/scan_band8_by_operator.sh"
    echo ""
    echo "Then run this script again without --full-scan flag."
    exit 0
fi

echo "Extracting active EARFCNs from exports..."
ACTIVE_DATA=$(extract_active_earfcns)

# Save to cache file
echo "$ACTIVE_DATA" > "$CACHE_FILE"

echo "Cache saved to: $CACHE_FILE"
echo ""

# Display results
echo "========================================"
echo "  Active Operators and EARFCNs"
echo "========================================"
echo ""
echo "$ACTIVE_DATA" | python3 -c "
import json
import sys

data = json.load(sys.stdin)

if not data:
    print('No active operators found in exports.')
    print('Run scan_band8_by_operator.sh to discover cells.')
    sys.exit(0)

total_cells = 0
for op, info in sorted(data.items()):
    earfcns = info['earfcns']
    count = info['cell_count']
    best_rsrp = info['best_rsrp']
    total_cells += count
    
    print(f'{op}:')
    print(f'  Cells: {count}')
    print(f'  Best RSRP: {best_rsrp} dBm')
    print(f'  EARFCNs: {earfcns}')
    print()

print(f'Total active operators: {len(data)}')
print(f'Total cells detected: {total_cells}')
"

echo "========================================"
echo "  Cache Ready!"
echo "========================================"
echo ""
echo "You can now run smart_scan_band8.sh to use this cache."
echo ""

