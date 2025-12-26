"""ETL entry point - fetch legislature data.

Usage:
    python -m etl                    # Fetch all legislatures
    python -m etl -l L17             # Fetch only L17
    python -m etl -l L17,L16         # Fetch L17 and L16
    python -m etl --help             # Show help
"""

import argparse
import sys

from etl.fetch import fetch_all
import config


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Fetch Portuguese Parliament data (iniciativas, atividades, info base)"
    )
    parser.add_argument(
        "-l", "--legislature",
        type=str,
        help="Legislature(s) to fetch (e.g., L17 or L17,L16). If not specified, fetches all."
    )
    parser.add_argument(
        "--skip-info-base",
        action="store_true",
        help="Skip fetching info_base (metadata) files"
    )
    parser.add_argument(
        "--skip-atividades",
        action="store_true",
        help="Skip fetching atividades (activities) files"
    )
    parser.add_argument(
        "--no-force",
        action="store_true",
        help="Don't re-download files that already exist"
    )
    return parser.parse_args()


def main():
    """Fetch legislature data from parlament.pt."""
    args = parse_args()

    # Parse legislature list
    legislatures = None
    if args.legislature:
        legislatures = [leg.strip() for leg in args.legislature.split(",")]

        # Validate legislature codes
        invalid = [leg for leg in legislatures if leg not in config.LEGISLATURES]
        if invalid:
            available = ", ".join(config.LEGISLATURES.keys())
            print(f"Error: Unknown legislature(s): {', '.join(invalid)}", file=sys.stderr)
            print(f"Available legislatures: {available}", file=sys.stderr)
            sys.exit(1)

    # Display what we're fetching
    if legislatures:
        print(f"==> Fetching legislatures: {', '.join(legislatures)}")
    else:
        print("==> Fetching all legislatures")

    # Call fetch_all with parsed arguments
    results = fetch_all(
        legislatures=legislatures,
        include_info_base=not args.skip_info_base,
        include_atividades=not args.skip_atividades,
        force=not args.no_force
    )

    # Display results
    print(f"==> Fetch completed. Results: {len(results)} legislatures processed")
    for leg, paths in results.items():
        print(f"  - {leg}: {list(paths.keys())}")


if __name__ == "__main__":
    main()
