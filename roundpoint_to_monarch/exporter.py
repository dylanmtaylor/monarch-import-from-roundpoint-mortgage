"""CSV Exporter for Monarch Money formatted files."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from roundpoint_to_monarch.amortizer import generate_amortization_schedule
from roundpoint_to_monarch.converter import (
    convert_to_monarch_balance_history,
    convert_to_monarch_transactions,
)
from roundpoint_to_monarch.parser import ParsedRoundPointData, RoundPointTransaction


def export_monarch_files(
    parsed_data: ParsedRoundPointData,
    output_dir: Union[str, Path] = "./output",
    account_name: str = "RoundPoint Mortgage",
    merchant: str = "RoundPoint Mortgage Servicing",
    backfill_origination: bool = False,
    positive_balance: bool = False,
    positive_payment: bool = False,
    include_escrow_disbursements: bool = True,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Export parsed RoundPoint data to Monarch Money CSV files.

    Generates:
    1. roundpoint_monarch_transactions.csv
    2. roundpoint_monarch_balance_history.csv

    Returns:
        Summary dictionary of export results.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    transactions: List[RoundPointTransaction] = list(parsed_data.transactions)
    metadata = parsed_data.metadata

    # If backfilling amortization from origination
    if backfill_origination:
        first_pmt = metadata.first_payment_date
        if not first_pmt and metadata.note_date:
            from datetime import datetime as dt_cls
            ndt = dt_cls.strptime(metadata.note_date, "%Y-%m-%d")
            m = ndt.month + (2 if ndt.day > 1 else 1)
            y = ndt.year
            while m > 12:
                m -= 12
                y += 1
            first_pmt = f"{y:04d}-{m:02d}-01"

        if first_pmt:
            earliest_rec = transactions[0].date if transactions else end_date or "2099-12-31"
            orig_bal = metadata.original_principal_amount or 0.0
            rate = metadata.interest_rate_percent or 3.0
            pi_amt = metadata.pi_payment_amount or 1007.21

            amortized = generate_amortization_schedule(
                origination_balance=orig_bal,
                interest_rate_percent=rate,
                first_payment_date=first_pmt,
                monthly_pi_amount=pi_amt,
                until_date=earliest_rec,
                origination_date=metadata.note_date,
            )
            # Prepend backfilled transactions
            transactions = amortized + transactions

    # 1. Transactions CSV
    tx_rows = convert_to_monarch_transactions(
        transactions=transactions,
        account_name=account_name,
        merchant=merchant,
        positive_payment=positive_payment,
        include_escrow_disbursements=include_escrow_disbursements,
        start_date=start_date,
        end_date=end_date,
    )

    tx_file = out_dir / "roundpoint_monarch_transactions.csv"
    with open(tx_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "Date",
                "Merchant",
                "Category",
                "Account",
                "Original Statement",
                "Notes",
                "Amount",
            ],
        )
        writer.writeheader()
        writer.writerows(tx_rows)

    # 2. Balance History CSV
    initial_bal = (metadata.original_principal_amount or 0.0) if backfill_origination else None
    actual_start = start_date
    if backfill_origination and not actual_start:
        actual_start = metadata.note_date or (transactions[0].date if transactions else None)

    bal_rows = convert_to_monarch_balance_history(
        transactions=transactions,
        initial_balance=initial_bal,
        start_date=actual_start,
        end_date=end_date,
        positive_balance=positive_balance,
    )

    bal_file = out_dir / "roundpoint_monarch_balance_history.csv"
    with open(bal_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Date", "Balance"])
        writer.writeheader()
        writer.writerows(bal_rows)

    date_range = None
    if bal_rows:
        date_range = (bal_rows[0]["Date"], bal_rows[-1]["Date"])

    latest_bal = bal_rows[-1]["Balance"] if bal_rows else "0.00"

    return {
        "transactions_file": str(tx_file.resolve()),
        "transactions_count": len(tx_rows),
        "balance_history_file": str(bal_file.resolve()),
        "balance_snapshots_count": len(bal_rows),
        "date_range": date_range,
        "latest_balance": latest_bal,
    }
