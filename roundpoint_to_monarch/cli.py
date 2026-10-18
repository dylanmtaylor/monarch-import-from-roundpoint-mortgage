"""Command-line interface for RoundPoint Mortgage to Monarch Money converter."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional
from roundpoint_to_monarch import __version__
from roundpoint_to_monarch.capture import capture_roundpoint_data
from roundpoint_to_monarch.exporter import export_monarch_files
from roundpoint_to_monarch.parser import parse_roundpoint_json


def find_default_input_file() -> Optional[Path]:
    """Look for standard RoundPoint JSON filenames in cwd or home directory."""
    candidates = [
        Path("roundpoint_raw_history.json"),
        Path("roundpoint_mortgage_history.json"),
        Path.home() / "roundpoint_raw_history.json",
        Path.home() / "roundpoint_mortgage_history.json",
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return c
    return None


def run_pipeline(
    input_file: Path,
    output_dir: Path,
    account_name: str,
    merchant: str,
    from_origination: bool,
    positive_balance: bool,
    positive_payment: bool,
    include_escrow: bool,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> int:
    """Execute the parsing and conversion pipeline."""
    print("=" * 60)
    print(" RoundPoint Mortgage to Monarch Money Converter")
    print("=" * 60)
    print(f"Input file:        {input_file.resolve()}")
    print(f"Output directory:  {output_dir.resolve()}")
    print(f"Account name:      {account_name}")
    print(f"Merchant name:     {merchant}")
    print(f"From origination:  {from_origination}")
    print(f"Liability sign:    {'Positive (+)' if positive_balance else 'Negative (-) [Monarch Standard]'}")
    print("-" * 60)

    try:
        parsed_data = parse_roundpoint_json(input_file)
    except Exception as e:
        print(f"❌ Error parsing input JSON: {e}", file=sys.stderr)
        return 1

    meta = parsed_data.metadata
    print(f"📋 Institution:     {meta.institution}")
    if meta.loan_number_masked:
        print(f"🔒 Loan Number:     {meta.loan_number_masked}")
    if meta.note_date:
        print(f"📅 Note Date:       {meta.note_date}")
    if meta.original_principal_amount:
        print(f"💵 Note Amount:     ${meta.original_principal_amount:,.2f}")
    if meta.interest_rate_percent:
        print(f"📈 Interest Rate:   {meta.interest_rate_percent:.3f}%")
    if meta.current_upb:
        print(f"💰 Current UPB:      ${meta.current_upb:,.2f}")

    print(f"🧾 Servicing Ledger: {len(parsed_data.transactions)} transactions loaded.")

    try:
        summary = export_monarch_files(
            parsed_data=parsed_data,
            output_dir=output_dir,
            account_name=account_name,
            merchant=merchant,
            backfill_origination=from_origination,
            positive_balance=positive_balance,
            positive_payment=positive_payment,
            include_escrow_disbursements=include_escrow,
            start_date=start_date,
            end_date=end_date,
        )
    except Exception as e:
        print(f"❌ Error exporting files: {e}", file=sys.stderr)
        return 1

    print("-" * 60)
    print("🎉 Export complete! Generated Monarch Money files:")
    print(f"  1. Transactions:     {summary['transactions_file']}")
    print(f"     -> {summary['transactions_count']} transactions")
    print(f"  2. Balance History:  {summary['balance_history_file']}")
    print(f"     -> {summary['balance_snapshots_count']} daily snapshots")
    if summary["date_range"]:
        print(f"     -> Date Range:     {summary['date_range'][0]} to {summary['date_range'][1]}")
    print(f"     -> Latest Balance: ${float(summary['latest_balance']):,.2f}")
    print("=" * 60)
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert RoundPoint Mortgage transaction and balance history into Monarch Money CSV format.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command")

    # Capture subcommand
    capture_parser = subparsers.add_parser(
        "capture",
        help="Connect to open Chrome browser and capture latest RoundPoint Mortgage JSON.",
    )
    capture_parser.add_argument(
        "-f", "--output-file",
        default="roundpoint_raw_history.json",
        help="Destination path for captured JSON file (default: roundpoint_raw_history.json)",
    )
    capture_parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Chrome remote debugging port (default: autodetected or 9222)",
    )
    capture_parser.add_argument(
        "--convert",
        action="store_true",
        default=True,
        help="Immediately convert captured JSON to Monarch CSV files (default: True)",
    )

    # Convert subcommand
    convert_parser = subparsers.add_parser(
        "convert",
        help="Convert an existing RoundPoint JSON file to Monarch CSV format.",
    )
    convert_parser.add_argument(
        "input_file",
        nargs="?",
        default=None,
        help="Path to RoundPoint JSON file (defaults to standard names in current dir or home)",
    )

    # General / Top-level arguments
    for p in [parser, capture_parser, convert_parser]:
        p.add_argument(
            "-o", "-d", "--output-dir",
            default="./output",
            help="Directory to save generated Monarch CSV files (default: ./output)",
        )
        p.add_argument(
            "-a", "--account-name",
            default="RoundPoint Mortgage",
            help="Monarch account name (default: 'RoundPoint Mortgage')",
        )
        p.add_argument(
            "-m", "--merchant",
            default="RoundPoint Mortgage Servicing",
            help="Merchant label for transactions (default: 'RoundPoint Mortgage Servicing')",
        )
        p.add_argument(
            "--from-origination",
            action="store_true",
            help="Backfill full historical amortization from loan origination date",
        )
        p.add_argument(
            "--positive-balance",
            action="store_true",
            help="Output liability balances as positive (default is negative per Monarch requirement)",
        )
        p.add_argument(
            "--positive-payment",
            action="store_true",
            help="Output payment transactions as positive (default is negative per Monarch requirement)",
        )
        p.add_argument(
            "--no-escrow",
            action="store_true",
            help="Exclude property tax and insurance escrow disbursements from transactions CSV",
        )
        p.add_argument(
            "--start-date",
            default=None,
            help="Optional start date filter (YYYY-MM-DD)",
        )
        p.add_argument(
            "--end-date",
            default=None,
            help="Optional end date filter (YYYY-MM-DD)",
        )

    # Positional input file or capture flag
    # Normalizing argv so `roundpoint-to-monarch [file]` maps cleanly to `convert [file]`
    clean_argv = list(argv) if argv is not None else sys.argv[1:]
    if clean_argv:
        first_arg = clean_argv[0]
        if first_arg not in ["capture", "convert", "-h", "--help", "-v", "--version"]:
            # If user ran with flags or file, route to convert subcommand
            clean_argv = ["convert"] + clean_argv

    args = parser.parse_args(clean_argv)

    out_dir = Path(args.output_dir)
    include_escrow = not args.no_escrow

    # Handle capture command
    if args.command == "capture":
        out_json = getattr(args, "output_file", "roundpoint_raw_history.json")
        port = getattr(args, "port", None)
        try:
            captured_path = capture_roundpoint_data(output_path=out_json, port=port)
        except Exception as e:
            print(f"❌ Browser capture failed: {e}", file=sys.stderr)
            return 1

        if not getattr(args, "convert", True):
            return 0
        input_path = captured_path
    else:
        # Determine input file for convert command
        input_str = getattr(args, "input_file", None)
        if input_str:
            input_path = Path(input_str)
            if not input_path.exists():
                print(f"❌ Input file not found: {input_path}", file=sys.stderr)
                return 1
        else:
            default_path = find_default_input_file()
            if default_path:
                input_path = default_path
            else:
                print("No input file specified and no standard JSON file found.", file=sys.stderr)
                print("Run 'roundpoint-to-monarch capture' to capture data from Chrome,", file=sys.stderr)
                print("or provide a path: 'roundpoint-to-monarch path/to/history.json'", file=sys.stderr)
                return 1

    return run_pipeline(
        input_file=input_path,
        output_dir=out_dir,
        account_name=args.account_name,
        merchant=args.merchant,
        from_origination=args.from_origination,
        positive_balance=args.positive_balance,
        positive_payment=args.positive_payment,
        include_escrow=include_escrow,
        start_date=args.start_date,
        end_date=args.end_date,
    )


if __name__ == "__main__":
    sys.exit(main())
