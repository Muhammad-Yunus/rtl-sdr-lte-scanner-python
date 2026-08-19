#!/usr/bin/env python3
"""
rtl_power peak detector for LTE Band 8 scanning.
"""
import subprocess
import json
import sys
import time
from typing import List, Tuple


def run_rtl_power(band_start, band_end, resolution_khz=100, gain=36, integration=0.5, retries=5):
    """Run rtl_power with retries."""
    
    cmd = [
        'rtl_power',
        '-f', f'{band_start}M:{band_end}M:{resolution_khz}k',
        '-g', str(gain),
        '-i', str(integration),
        '-1',
        '-w', 'hann',
        '-'
    ]
    
    last_error = None
    for attempt in range(retries):
        if attempt > 0:
            time.sleep(1.5)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
            
            # Parse all lines
            peaks = []
            all_powers = []
            bin_size = resolution_khz * 1000
            
            for line in result.stdout.split('\n'):
                if not line.startswith('20'):
                    continue
                
                parts = line.split(',')
                if len(parts) < 7:
                    continue
                
                try:
                    start_freq = int(parts[2].strip())
                    bin_size = float(parts[4].strip())
                    powers = parts[6:]  # All power values
                    
                    for i, p_str in enumerate(powers):
                        power = float(p_str.strip())
                        all_powers.append(power)
                        freq_hz = start_freq + i * bin_size
                        peaks.append({'freq_hz': freq_hz, 'power_dbm': power})
                except Exception as e:
                    pass
            
            if peaks:
                all_powers.sort()
                noise_floor = all_powers[len(all_powers) // 2]
                return peaks, noise_floor
            else:
                last_error = "No data"
                
        except Exception as e:
            last_error = str(e)
    
    print(f"Error: {last_error}", file=sys.stderr)
    return [], -200


def find_chunks(peaks, threshold, band_start_mhz):
    """Find signal chunks."""
    signals = [p for p in peaks if p['power_dbm'] >= threshold]
    
    if not signals:
        return []
    
    chunks = []
    current = None
    
    for peak in sorted(signals, key=lambda x: x['freq_hz']):
        earfcn = int((peak['freq_hz'] - band_start_mhz * 1e6) / (100 * 1000))
        
        if current is None:
            current = {'start': earfcn, 'end': earfcn, 'power': peak['power_dbm'], 'bins': 1}
        elif earfcn <= current['end'] + 1:
            current['end'] = max(current['end'], earfcn)
            current['power'] = max(current['power'], peak['power_dbm'])
            current['bins'] += 1
        else:
            chunks.append(current)
            current = {'start': earfcn, 'end': earfcn, 'power': peak['power_dbm'], 'bins': 1}
    
    if current:
        chunks.append(current)
    
    return chunks


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--band-start', type=float, default=925.0)
    parser.add_argument('--band-end', type=float, default=960.0)
    parser.add_argument('--resolution', type=int, default=100)
    parser.add_argument('--gain', type=float, default=36)
    parser.add_argument('--integration', type=float, default=0.5)
    parser.add_argument('--threshold', type=float, default=-80)
    parser.add_argument('--output', choices=['json', 'chunks'], default='chunks')
    args = parser.parse_args()
    
    print(f"Scanning {args.band_start}-{args.band_end} MHz...", file=sys.stderr)
    
    peaks, noise_floor = run_rtl_power(
        args.band_start, args.band_end,
        args.resolution, args.gain, args.integration
    )
    
    if noise_floor == -200:
        print("ERROR: No data", file=sys.stderr)
        sys.exit(1)
    
    print(f"Noise floor: {noise_floor:.1f} dBm", file=sys.stderr)
    
    chunks = find_chunks(peaks, args.threshold, args.band_start)
    
    if args.output == 'json':
        print(json.dumps({
            'noise_floor_dbm': noise_floor,
            'threshold_dbm': args.threshold,
            'chunks_detected': len(chunks),
            'chunks': chunks
        }, indent=2))
    else:
        if chunks:
            for c in chunks:
                print(f"{c['start']}-{c['end']}")
        else:
            print("NONE")
    
    sys.exit(0 if chunks else 1)


if __name__ == '__main__':
    main()
