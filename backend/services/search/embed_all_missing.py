#!/usr/bin/env python3
"""
Batch embed all companies that have unembedded PDFs on disk.
Run from: backend/services/search/
Usage: python embed_all_missing.py [--dry-run]
"""

import os
import sys
import time
import subprocess

# Companies with unembedded PDFs, ordered smallest → largest
TICKERS = [
    "MDGL",   # 1 missing
    "TAK",    # 1 missing
    "IONS",   # 2 missing
    "JNJ",    # 5 missing
    "DSNKY",  # 6 missing
    "AXSM",   # 9 missing
    "GPCR",   # 12 missing
    "LLY",    # 12 missing
    "SMMT",   # 22 missing
    "NVO",    # 31 missing
    "ROIV",   # 43 missing
    "GILD",   # 43 missing
    "SRPT",   # 44 missing
    "ABBV",   # 61 missing (already done, will skip)
    "NVS",    # 98 missing
    "ARGX",   # 111 missing
    "RCUS",   # 122 missing
    "BCYC",   # 126 missing
    "RHHBY",  # 171 missing
    "AGTSY",  # 216 missing
]

DRY_RUN = "--dry-run" in sys.argv

def main():
    start = time.time()
    results = {}

    for i, ticker in enumerate(TICKERS):
        print(f"\n{'='*60}")
        print(f"  [{i+1}/{len(TICKERS)}] Embedding {ticker}...")
        print(f"{'='*60}")

        if DRY_RUN:
            print(f"  [dry-run] Would embed {ticker}")
            results[ticker] = "dry-run"
            continue

        try:
            proc = subprocess.run(
                [sys.executable, "embed_documents.py", "--ticker", ticker],
                capture_output=True,
                text=True,
                timeout=600,  # 10 min per company
                env=os.environ,
            )

            # Parse output for summary
            output = proc.stdout + proc.stderr
            for line in output.split("\n"):
                if "Done!" in line or "Embedded" in line or "ERROR" in line or "new documents" in line:
                    print(f"  {line.strip()}")

            if proc.returncode == 0:
                # Extract count from output
                for line in output.split("\n"):
                    if "new documents" in line.lower() or "Done!" in line:
                        results[ticker] = line.strip()
                        break
                else:
                    results[ticker] = "completed (no summary line)"
            else:
                results[ticker] = f"ERROR (exit {proc.returncode})"
                # Print last 5 lines of error
                err_lines = output.strip().split("\n")[-5:]
                for l in err_lines:
                    print(f"  ERR: {l}")

        except subprocess.TimeoutExpired:
            results[ticker] = "TIMEOUT (>10min)"
            print(f"  TIMEOUT: {ticker} took > 10 minutes")
        except Exception as e:
            results[ticker] = f"EXCEPTION: {e}"
            print(f"  EXCEPTION: {e}")

    elapsed = time.time() - start
    print(f"\n\n{'='*60}")
    print(f"  BATCH EMBEDDING COMPLETE")
    print(f"  Total time: {elapsed/60:.1f} minutes")
    print(f"{'='*60}\n")

    for ticker, result in results.items():
        status = "✓" if "ERROR" not in str(result) and "TIMEOUT" not in str(result) else "✗"
        print(f"  {status} {ticker:10s} {result}")

if __name__ == "__main__":
    main()
