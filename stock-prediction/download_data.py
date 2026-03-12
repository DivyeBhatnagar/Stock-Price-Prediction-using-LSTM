"""
download_data.py  (project root convenience wrapper)
=====================================================
Downloads 10 years of historical data for all 50 NIFTY companies.
Delegates to scripts/download_data.py for the full implementation.

Usage
-----
    python download_data.py                   # download all 50
    python download_data.py --ticker TCS.NS   # single stock
    python download_data.py --force           # force re-download
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))

from download_data import main   # scripts/download_data.py

if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
