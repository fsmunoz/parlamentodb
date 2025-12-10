"""
Entry point for running ETL fetch as a module.

Usage:
    python -m etl

This will always force re-download of all data files, even if they already exist.
"""

from etl.fetch import fetch_all

if __name__ == "__main__":
    print("==> Starting ETL fetch with force=True")
    # Always force re-download when run via make etl-fetch
    results = fetch_all(force=True)
    print(f"==> Fetch completed. Results: {len(results)} legislatures processed")
    for leg, paths in results.items():
        print(f"  - {leg}: {list(paths.keys())}")
