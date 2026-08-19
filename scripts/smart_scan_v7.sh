#!/bin/bash
#
# Smart Band 8 Scan v7 - CACHE-BASED (Final Version)
# Scan chunks berdasarkan cache spectrum_scan
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
LOG_FILE="$EXPORTS_DIR/smart_scan_v7_${TIMESTAMP}.log"
CELLS_FILE="$EXPORTS_DIR/smart_scan_v7_${TIMESTAMP}.cells.json"

echo "========================================"
echo "  Smart Band 8 Scan v7 (CACHE-BASED)"
echo "========================================"
echo ""
echo "Timestamp: $TIMESTAMP"

# Check if cache exists
if [ ! -f "$CACHE_FILE" ]; then
    echo "ERROR: Cache file not found: $CACHE_FILE"
    echo "Please run first: ./scripts/init_scan_cache.sh --full-scan"
    exit 1
fi

# Initialize cells file
echo "[]" > "$CELLS_FILE"

total_cells=0
chunks_scanned=0

echo "----------------------------------------"
echo "Scanning chunks with active signals..."
echo "----------------------------------------"

# Use Python to determine which chunks to scan and execute
python3 << EOF
import json
import subprocess
import re
import sys

# Load cache
with open('$CACHE_FILE') as f:
    cache = json.load(f)

# Get active EARFCNs
all_earfcns = []
for op, info in cache.items():
    all_earfcns.extend(info['earfcns'])

active_earfcns = sorted(set(all_earfcns))

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

# Group EARFCNs into chunks
chunks = []
current_chunk_start = None
current_chunk_end = None
current_chunk_operator = None
chunk_size = $CHUNK_SIZE

for earfcn in active_earfcns:
    if current_chunk_start is None:
        current_chunk_start = earfcn
        current_chunk_end = earfcn
        current_chunk_operator = get_operator(earfcn)
    elif earfcn <= current_chunk_end + chunk_size:
        # Extend current chunk
        current_chunk_end = max(current_chunk_end, earfcn)
    else:
        # Start new chunk
        chunks.append((current_chunk_start, current_chunk_end, current_chunk_operator))
        current_chunk_start = earfcn
        current_chunk_end = earfcn
        current_chunk_operator = get_operator(earfcn)

# Don't forget last chunk
if current_chunk_start is not None:
    chunks.append((current_chunk_start, current_chunk_end, current_chunk_operator))

print(f"Found {len(chunks)} chunks to scan:")
for start, end, op in chunks:
    print(f"  [{op}] EARFCN {start}-{end}")

print()
print("-" * 40)
print("Starting scan...")
print("-" * 40)

total_cells = 0
chunks_scanned = 0

# Scan each chunk
for start, end, operator in chunks:
    print(f"  [{operator}] Scanning EARFCN {start}-{end}...", end=" ", flush=True)
    
    # Run cell_search
    try:
        result = subprocess.run(
            ['$CELL_SEARCH', '-b', '8', '-g', '$GAIN', '-n', '$FRAMES', '-s', str(start), '-e', str(end)],
            capture_output=True,
            text=True,
            timeout=60
        )
        output = result.stdout
        
        # Parse cells
        cells_found = []
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
            except:
                pass
        
        if cells_found:
            print(f"Found {len(cells_found)} cell(s)")
            total_cells += len(cells_found)
            chunks_scanned += 1
            
            # Append to cells file
            with open('$CELLS_FILE', 'a') as f:
                for cell in cells_found:
                    f.write(json.dumps(cell) + '\n')
            
            # Append to log file
            with open('$LOG_FILE', 'a') as f:
                f.write(output)
        else:
            print("No cells")
    
    except subprocess.TimeoutExpired:
        print("TIMEOUT")
    except Exception as e:
        print(f"ERROR: {e}")

# Write summary
print()
print("=" * 40)
print("  Scan Complete!")
print("=" * 40)
print()
print(f"Summary:")
print(f"  Chunks scanned: {chunks_scanned} of {len(chunks)}")
print(f"  Total cells: {total_cells}")
print()

# Display cells
if total_cells > 0:
    print("Detected Cells:")
    print("-" * 40)
    with open('$CELLS_FILE') as f:
        all_cells = [json.loads(line) for line in f if line.strip() and line.strip() != '[]']
    
    for c in sorted(all_cells, key=lambda x: (x['operator'], x['earfcn'])):
        print(f"  {c['operator']:12s} | EARFCN {c['earfcn']:5d} | {c['freq_mhz']} MHz | PHY {c['phy_id']}")
else:
    print("No LTE cells detected in this scan.")

print()
print("Output files:")
print(f"  Log: $LOG_FILE")
print(f"  Cells: $CELLS_FILE")

EOF
