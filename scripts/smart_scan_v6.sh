#!/bin/bash
#
# Smart Band 8 Scan v6 - FAST Direct Scan
# Langsung scan srsRAN cell_search tanpa rtl_power (lebih cepat!)
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

CELL_SEARCH="/home/pi/srsRAN_4G/build/lib/examples/cell_search"

# srsRAN settings
GAIN=20
FRAMES=15

# Output
EXPORTS_DIR="./exports"
mkdir -p "$EXPORTS_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$EXPORTS_DIR/smart_scan_v6_${TIMESTAMP}.log"
CELLS_FILE="$EXPORTS_DIR/smart_scan_v6_${TIMESTAMP}.cells.json"

echo "========================================"
echo "  Smart Band 8 Scan v6 (FAST)"
echo "========================================"
echo ""
echo "Timestamp: $TIMESTAMP"
echo "Method: Direct srsRAN cell_search (no rtl_power)"
echo ""

# Initialize
echo "[]" > "$CELLS_FILE"

# ============================================================
# LTE Cell Search (Direct srsRAN)
# ============================================================
echo "----------------------------------------"
echo "LTE Cell Search (srsRAN)"
echo "----------------------------------------"

total_cells=0
total_scans=0

# Function to scan one EARFCN range
scan_range() {
    local operator=$1
    local start=$2
    local end=$3
    
    echo ""
    echo "  [$operator] Scanning EARFCN ${start}-${end}..."
    
    # Scan in chunks of 10 EARFCNs
    local current=$start
    while [ $current -le $end ]; do
        local chunk_end=$((current + 9))
        [ $chunk_end -gt $end ] && chunk_end=$end
        
        # Run cell_search
        local output
        output=$($CELL_SEARCH -b 8 -g $GAIN -n $FRAMES -s $current -e $chunk_end 2>/dev/null) || true
        
        # Check for cells
        local cell_count
        cell_count=$(echo "$output" | grep -c "Found CELL [0-9]" || true)
        
        if [ "$cell_count" -gt 0 ]; then
            echo "    EARFCN ${current}-${chunk_end}: Found $cell_count cell(s)"
            total_cells=$((total_cells + cell_count))
            total_scans=$((total_scans + 1))
            
            # Extract cell details and save to JSON
            local cells_json
            cells_json=$(echo "$output" | grep "Found CELL [0-9]" | python3 -c "
import sys, json
for line in sys.stdin:
    line = line.strip()
    if not line.startswith('Found CELL'):
        continue
    try:
        import re
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
" "$operator" 2>/dev/null) || true
            
            if [ -n "$cells_json" ]; then
                echo "$cells_json" >> "$CELLS_FILE"
            fi
            
            echo "$output" >> "$LOG_FILE"
        fi
        
        current=$((chunk_end + 1))
    done
}

# Scan each operator range
scan_range "Telkomsel" 3450 3549
scan_range "Indosat" 3550 3649
scan_range "XL" 3650 3749
scan_range "Smartfren" 3750 3799

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

if [ -f "$CELLS_FILE" ] && [ -s "$CELLS_FILE" ]; then
    python3 -c "
import json
with open('$CELLS_FILE') as f:
    cells = [json.loads(line) for line in f if line.strip()]

for c in sorted(cells, key=lambda x: x['earfcn']):
    print(f\"  {c['operator']:10s} | EARFCN {c['earfcn']:5d} | Freq {c['freq_mhz']} MHz | PHY {c['phy_id']:4d} | PRB {c['prb']:3d} | Ports {c['ports']} | PSS {c['pss_power_dbm']} dBm\")
" 2>/dev/null
else
    echo "No LTE cells detected in Band 8."
fi

echo ""
echo "Output files:"
echo "  Log: $LOG_FILE"
echo "  Cells: $CELLS_FILE"
