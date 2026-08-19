#!/bin/bash
#
# Smart Band 8 Scan v8 - HYBRID (Fast + Complete)
# Hybrid approach: Cache-based + fallback untuk chunk kosong
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

CELL_SEARCH="/home/pi/srsRAN_4G/build/lib/examples/cell_search"

# Configuration
GAIN=36
FRAMES=15
CHUNK_SIZE=10
CACHE_FILE="data/smart_scan_cache.json"

# Output
EXPORTS_DIR="./exports"
mkdir -p "$EXPORTS_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$EXPORTS_DIR/smart_scan_v8_${TIMESTAMP}.log"
CELLS_FILE="$EXPORTS_DIR/smart_scan_v8_${TIMESTAMP}.cells.json"

echo "========================================"
echo "  Smart Band 8 Scan v8 (HYBRID)"
echo "========================================"
echo ""
echo "Timestamp: $TIMESTAMP"
echo "Method: Cache-based + full scan fallback"
echo ""

# Initialize cells file
echo "[]" > "$CELLS_FILE"

total_cells=0
chunks_scanned=0

# Check if cache exists
if [ -f "$CACHE_FILE" ]; then
    echo "Loading cache from: $CACHE_FILE"
    echo ""
fi

echo "----------------------------------------"
echo "PHASE 1: Cache-based scan (FAST)"
echo "----------------------------------------"

python3 << 'EOF'
import json
import subprocess
import re
import sys

CELL_SEARCH = "/home/pi/srsRAN_4G/build/lib/examples/cell_search"
GAIN = 36
FRAMES = 15
CHUNK_SIZE = 10

# Try to load cache
cache = {}
try:
    with open('data/smart_scan_cache.json') as f:
        cache = json.load(f)
except:
    pass

# Get active EARFCNs from cache
active_earfcns = []
for op, info in cache.items():
    active_earfcns.extend(info['earfcns'])

active_earfcns = sorted(set(active_earfcns))

# Determine operator by EARFCN range
def get_operator(earfcn):
    if 3450 <= earfcn <= 3549:
        return 'Telkomsel'
    elif 3550 <= earfcn <= 3649:
        return 'Indosat'
    elif 3650 <= earfcn <= 3749:
        return 'XL'
    elif 3750 <= earfcn <= 3799:
        return 'Smartfren'
    return 'Unknown'

# Group into chunks
chunks = []
current_chunk_start = None
current_chunk_end = None
current_chunk_operator = None

for earfcn in active_earfcns:
    if current_chunk_start is None:
        current_chunk_start = earfcn
        current_chunk_end = earfcn
        current_chunk_operator = get_operator(earfcn)
    elif earfcn <= current_chunk_end + CHUNK_SIZE:
        current_chunk_end = max(current_chunk_end, earfcn)
    else:
        chunks.append((current_chunk_start, current_chunk_end, current_chunk_operator))
        current_chunk_start = earfcn
        current_chunk_end = earfcn
        current_chunk_operator = get_operator(earfcn)

if current_chunk_start is not None:
    chunks.append((current_chunk_start, current_chunk_end, current_chunk_operator))

print(f"Found {len(chunks)} chunks in cache")

# Scan each chunk
cells_found = []
for start, end, operator in chunks:
    print(f"  [{operator}] EARFCN {start}-{end}...", end=" ", flush=True)
    
    try:
        result = subprocess.run(
            [CELL_SEARCH, '-b', '8', '-g', str(GAIN), '-n', str(FRAMES), '-s', str(start), '-e', str(end)],
            capture_output=True,
            text=True,
            timeout=60
        )
        output = result.stdout
        
        for line in output.split('\n'):
            if not line.startswith('Found CELL'):
                continue
            
            try:
                freq = re.search(r'Found CELL ([0-9.]+) MHz', line)
                earfcn = re.search(r'EARFCN=([0-9]+)', line)
                phyid = re.search(r'PHYID=([0-9]+)', line)
                prb = re.search(r'([0-9]+) PRB', line)
                ports = re.search(r'([0-9]+) ports', line)
                power = re.search(r'PSS power=([0-9.-]+) dBm', line)
                
                if freq and earfcn and phyid and prb and ports and power:
                    cells_found.append({
                        'operator': operator,
                        'freq_mhz': float(freq.group(1)),
                        'earfcn': int(earfcn.group(1)),
                        'phy_id': int(phyid.group(1)),
                        'prb': int(prb.group(1)),
                        'ports': int(ports.group(1)),
                        'pss_power_dbm': float(power.group(1))
                    })
                    print(f"Found cell")
                    break
                else:
                    print("No cells")
            except:
                print("Parse error")
    
    except subprocess.TimeoutExpired:
        print("TIMEOUT")
    except Exception as e:
        print(f"ERROR: {e}")

# Save results
with open('exports/smart_scan_v8_phase1.cells.json', 'w') as f:
    for cell in cells_found:
        f.write(json.dumps(cell) + '\n')

print(f"\nPhase 1 complete: {len(cells_found)} cells from {len(chunks)} chunks")
EOF

# Copy phase 1 results
if [ -f "exports/smart_scan_v8_phase1.cells.json" ] && [ -s "exports/smart_scan_v8_phase1.cells.json" ]; then
    cat exports/smart_scan_v8_phase1.cells.json >> "$CELLS_FILE"
    total_cells=$(wc -l < "$CELLS_FILE")
    total_cells=$((total_cells - 1))  # Subtract initial []
fi

echo ""
echo "----------------------------------------"
echo "PHASE 2: Full scan fallback (COMPREHENSIVE)"
echo "----------------------------------------"
echo "Scanning all chunks to find new cells..."
echo ""

# Phase 2: Scan all chunks sequentially (full coverage)
for start in $(seq 3450 10 3799); do
    end=$((start + 9))
    
    # Determine operator
    if [ $start -le 3549 ]; then
        operator="Telkomsel"
    elif [ $start -le 3649 ]; then
        operator="Indosat"
    elif [ $start -le 3749 ]; then
        operator="XL"
    else
        operator="Smartfren"
    fi
    
    echo -n "  [$operator] EARFCN ${start}-${end}... "
    
    # Run cell_search
    output=$($CELL_SEARCH -b 8 -g $GAIN -n $FRAMES -s $start -e $end 2>/dev/null) || true
    
    # Check for cells
    cell_count=$(echo "$output" | grep -c "Found CELL [0-9]" || true)
    
    if [ "$cell_count" -gt 0 ]; then
        echo "Found $cell_count cell(s)"
        total_cells=$((total_cells + cell_count))
        chunks_scanned=$((chunks_scanned + 1))
        
        # Extract cells
        echo "$output" | grep "Found CELL [0-9]" | python3 -c "
import sys, json, re
for line in sys.stdin:
    line = line.strip()
    if not line.startswith('Found CELL'):
        continue
    try:
        freq = re.search(r'Found CELL ([0-9.]+) MHz', line)
        earfcn = re.search(r'EARFCN=([0-9]+)', line)
        phyid = re.search(r'PHYID=([0-9]+)', line)
        prb = re.search(r'([0-9]+) PRB', line)
        ports = re.search(r'([0-9]+) ports', line)
        power = re.search(r'PSS power=([0-9.-]+) dBm', line)
        
        if freq and earfcn and phyid and prb and ports and power:
            print(json.dumps({
                'operator': sys.argv[1],
                'freq_mhz': float(freq.group(1)),
                'earfcn': int(earfcn.group(1)),
                'phy_id': int(phyid.group(1)),
                'prb': int(prb.group(1)),
                'ports': int(ports.group(1)),
                'pss_power_dbm': float(power.group(1))
            }))
    except:
        pass
" "$operator" >> "$CELLS_FILE" 2>/dev/null
        
        echo "$output" >> "$LOG_FILE"
    else
        echo "No cells"
    fi
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
echo "  Total cells: $total_cells"
echo ""

if [ -f "$CELLS_FILE" ] && [ -s "$CELLS_FILE" ]; then
    echo "Detected Cells:"
    echo "----------------------------------------"
    python3 -c "
import json
with open('$CELLS_FILE') as f:
    cells = [json.loads(line) for line in f if line.strip() and line.strip() != '[]']
    # Deduplicate by earfcn + phy_id
    seen = set()
    unique = []
    for c in cells:
        key = (c['earfcn'], c['phy_id'])
        if key not in seen:
            seen.add(key)
            unique.append(c)

for c in sorted(unique, key=lambda x: (x['operator'], x['earfcn'])):
    print(f\"  {c['operator']:12s} | EARFCN {c['earfcn']:5d} | {c['freq_mhz']} MHz | PHY {c['phy_id']}\")
" 2>/dev/null
else
    echo "No LTE cells detected."
fi

echo ""
echo "Output files:"
echo "  Log: $LOG_FILE"
echo "  Cells: $CELLS_FILE"
