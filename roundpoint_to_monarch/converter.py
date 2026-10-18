"""Converters from RoundPoint transactions into Monarch Money CSV data."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from roundpoint_to_monarch.parser import RoundPointTransaction


def convert_to_monarch_transactions(
    transactions: List[RoundPointTransaction],
    account_name: str = "RoundPoint Mortgage",
    merchant: str = "RoundPoint Mortgage Servicing",
    positive_payment: bool = False,
    include_escrow_disbursements: bool = True,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Convert RoundPoint transactions into Monarch Money transactions schema.

    Schema:
    Date,Merchant,Category,Account,Original Statement,Notes,Amount

    Monarch Liability Account Conventions:
    - Payments that pay down the loan balance are negative numbers (e.g. -1673.38),
      unless positive_payment=True is explicitly set.
    """
    rows: List[Dict[str, Any]] = []

    start_dt = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    end_dt = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None

    for tx in transactions:
        tx_dt = datetime.strptime(tx.date, "%Y-%m-%d").date()
        if start_dt and tx_dt < start_dt:
            continue
        if end_dt and tx_dt > end_dt:
            continue

        is_payment = tx.event_type == "payment"
        is_tax = "tax" in tx.type_description.lower()
        is_insurance = "insurance" in tx.type_description.lower()
        is_reversal = "reversal" in tx.type_description.lower() or "returned" in (tx.explanation or "").lower()

        if not is_payment and not include_escrow_disbursements:
            continue

        # Determine Category
        if is_payment:
            category = "Mortgage"
        elif is_tax:
            category = "Property Tax"
        elif is_insurance:
            category = "Home Insurance"
        else:
            category = "Mortgage"

        # Determine Amount
        # In Monarch liability accounts, payments reducing liability are negative.
        # Fees/advances increasing liability are positive.
        if is_payment:
            amt = abs(tx.total_amount)
            signed_amount = amt if positive_payment else -amt
        elif is_reversal:
            # A reversal of a payment increases liability back
            signed_amount = abs(tx.total_amount) if not positive_payment else -abs(tx.total_amount)
        else:
            # Escrow disbursements
            signed_amount = abs(tx.total_amount) if not positive_payment else -abs(tx.total_amount)

        # Original statement description
        parts = [tx.type_description]
        if tx.explanation and tx.explanation != tx.type_description:
            parts.append(tx.explanation)
        if tx.source_of_funds:
            parts.append(f"({tx.source_of_funds})")
        orig_statement = " - ".join(parts)

        # Detailed breakdown in Notes
        notes_parts = []
        if tx.principal_amount > 0:
            notes_parts.append(f"Principal: ${tx.principal_amount:,.2f}")
        if tx.interest_amount > 0:
            notes_parts.append(f"Interest: ${tx.interest_amount:,.2f}")
        if tx.escrow_amount > 0:
            notes_parts.append(f"Escrow: ${tx.escrow_amount:,.2f}")
        if tx.remaining_principal_balance > 0:
            notes_parts.append(f"UPB: ${tx.remaining_principal_balance:,.2f}")
        if tx.due_date and tx.due_date != tx.date:
            notes_parts.append(f"Due: {tx.due_date}")

        notes = " | ".join(notes_parts) if notes_parts else tx.type_description

        rows.append({
            "Date": tx.date,
            "Merchant": merchant,
            "Category": category,
            "Account": account_name,
            "Original Statement": orig_statement,
            "Notes": notes,
            "Amount": f"{signed_amount:.2f}",
        })

    return rows


def convert_to_monarch_balance_history(
    transactions: List[RoundPointTransaction],
    initial_balance: Optional[float] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    positive_balance: bool = False,
) -> List[Dict[str, str]]:
    """Generate continuous daily balance history from RoundPoint transactions.

    Schema:
    Date,Balance

    Monarch Liability Account Conventions:
    - Liability balances (mortgages/debt) must be negative numbers (e.g. -0.0)
      for Monarch to properly calculate Net Worth, unless positive_balance=True.
    - Forward-fills daily so continuous net worth charts render without gaps.
    """
    if not transactions and initial_balance is None:
        return []

    # Map dates to final remaining UPB balance on that date
    date_to_balance: Dict[str, float] = {}
    for tx in transactions:
        if tx.remaining_principal_balance > 0:
            date_to_balance[tx.date] = tx.remaining_principal_balance

    sorted_dates = sorted(date_to_balance.keys())
    if not sorted_dates and initial_balance is None:
        return []

    first_recorded_date = sorted_dates[0] if sorted_dates else start_date
    actual_start = start_date or first_recorded_date
    actual_end = end_date or datetime.today().strftime("%Y-%m-%d")

    start_dt = datetime.strptime(actual_start, "%Y-%m-%d").date()
    end_dt = datetime.strptime(actual_end, "%Y-%m-%d").date()

    if end_dt < start_dt:
        start_dt, end_dt = end_dt, start_dt

    # Determine running balance
    if initial_balance is not None:
        current_upb = initial_balance
    elif sorted_dates:
        current_upb = date_to_balance[sorted_dates[0]]
    else:
        current_upb = 0.0

    rows: List[Dict[str, str]] = []
    curr_dt = start_dt

    while curr_dt <= end_dt:
        curr_str = curr_dt.strftime("%Y-%m-%d")

        if curr_str in date_to_balance:
            current_upb = date_to_balance[curr_str]

        # Apply sign convention
        val = abs(current_upb) if positive_balance else -abs(current_upb)

        rows.append({
            "Date": curr_str,
            "Balance": f"{val:.2f}",
        })
        curr_dt += timedelta(days=1)

    return rows
