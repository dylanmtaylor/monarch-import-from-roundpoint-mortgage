"""Mortgage amortization generator for pre-boarding backfill."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from roundpoint_to_monarch.parser import RoundPointTransaction


def add_month(dt: datetime) -> datetime:
    """Advance a datetime by 1 month, keeping the same day of month where possible."""
    year = dt.year
    month = dt.month + 1
    if month > 12:
        year += 1
        month = 1
    # Day clamping for end of month if applicable
    day = min(dt.day, 28)
    return dt.replace(year=year, month=month, day=day)


def generate_amortization_schedule(
    origination_balance: float,
    interest_rate_percent: float,
    first_payment_date: str,
    monthly_pi_amount: float,
    until_date: str,
    origination_date: Optional[str] = None,
) -> List[RoundPointTransaction]:
    """Generate scheduled historical monthly mortgage payments up to until_date.

    Args:
        origination_balance: Initial loan amount at origination (e.g. 0.0).
        interest_rate_percent: Annual fixed interest rate as a percent (e.g. 3.0 for 3%).
        first_payment_date: Date of first scheduled monthly payment (YYYY-MM-DD, e.g. '2021-01-01').
        monthly_pi_amount: Fixed monthly principal & interest payment (e.g. 1007.21).
        until_date: Stop generating before or on this date (YYYY-MM-DD, e.g. first RoundPoint record '2023-02-14').
        origination_date: Optional note origination date (YYYY-MM-DD).

    Returns:
        List of synthetic RoundPointTransaction objects for the pre-boarding period.
    """
    monthly_rate = (interest_rate_percent / 100.0) / 12.0
    current_balance = round(origination_balance, 2)

    current_dt = datetime.strptime(first_payment_date, "%Y-%m-%d")
    until_dt = datetime.strptime(until_date, "%Y-%m-%d")

    records: List[RoundPointTransaction] = []

    while current_dt < until_dt:
        date_str = current_dt.strftime("%Y-%m-%d")

        # Calculate interest and principal
        interest = round(current_balance * monthly_rate, 2)
        principal = round(monthly_pi_amount - interest, 2)

        # Ensure we don't overpay principal
        if principal > current_balance:
            principal = current_balance
            interest = round(monthly_pi_amount - principal, 2)
            current_balance = 0.0
        else:
            current_balance = round(current_balance - principal, 2)

        tx = RoundPointTransaction(
            date=date_str,
            effective_date=date_str,
            due_date=date_str,
            event_type="payment",
            type_description="Scheduled Payment (Amortized)",
            explanation="Prior Servicer Pre-Boarding Schedule",
            source_of_funds="ACH Draft",
            total_amount=round(monthly_pi_amount, 2),
            principal_amount=principal,
            interest_amount=interest,
            escrow_amount=0.0,
            fees_amount=0.0,
            remaining_principal_balance=current_balance,
            escrow_balance=0.0,
            late_days=0,
            grace_status="ByDueDate",
        )
        records.append(tx)

        if current_balance <= 0.0:
            break

        current_dt = add_month(current_dt)

    return records
