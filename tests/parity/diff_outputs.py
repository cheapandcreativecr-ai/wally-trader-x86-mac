#!/usr/bin/env python3
"""Compare CC and OC JSON outputs ignoring timestamps and UUIDs."""
import json, re, sys

def normalize(s: str) -> str:
    s = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', '<TS>', s)
    s = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '<UUID>', s, flags=re.I)
    s = re.sub(r'"created_time"\s*:\s*"[^"]+"', '"created_time": "<TS>"', s)
    return s

def main():
    if len(sys.argv) != 3:
        print("usage: diff_outputs.py <a.json> <b.json>", file=sys.stderr)
        sys.exit(2)
    a, b = sys.argv[1], sys.argv[2]
    A = normalize(open(a).read())
    B = normalize(open(b).read())
    if A == B:
        print("PARITY OK")
        sys.exit(0)
    print("PARITY DIFF")
    print(f"--- {a}")
    print(A[:500])
    print(f"--- {b}")
    print(B[:500])
    sys.exit(1)

if __name__ == "__main__":
    main()
