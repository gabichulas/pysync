#!/usr/bin/env python3
# pysync.py

import argparse
import sys
from engine import generate_manifest, calculate_delta

def main():
    
    parser = argparse.ArgumentParser(prog="pysync", description="A block-level file synchronization engine.")
    
    parser.add_argument("source", help="Path to the local source file")
    parser.add_argument("destination", help="User, host and path for the remote destination. Example: user@host:/path")
    parser.add_argument("-b", "--block-size", type=int, default=4096, help="Block size in bytes (default: 4096)")
    
    args = parser.parse_args()
    
    if not args.source or not args.destination:
        print("Error: Source and destination are required.")
        sys.exit(1)
    
    print(f"[*] Engine initialized:")
    print(f"[*] Generating manifest for {args.destination} with block size {args.block_size}...")
    try:    
        manifest = generate_manifest(args.source, args.block_size)
        print(f"[+] Success! Manifest contains {len(manifest)} blocks.")
        
        print(f"\n[*] Calculating delta stream for {args.source}...")
        delta_stream = calculate_delta(args.destination, manifest, args.block_size)
        
        for instruction in delta_stream:
            action, payload = instruction
            if action == 'LITERAL':
                print(f"    -> [LITERAL] Send {len(payload)} raw bytes.")
            elif action == 'BLOCK':
                print(f"    -> [BLOCK] Send reference to Remote Block Index {payload}.")
                
    except Exception as e:
        print(f"[!] Error reading file: {e}")
        sys.exit(1)
if __name__ == "__main__":
    main()