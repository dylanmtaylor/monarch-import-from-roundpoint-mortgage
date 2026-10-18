"""Parser for RoundPoint Mortgage API and JSON exports."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


@dataclass
class LoanMetadata:
    """Metadata describing mortgage loan terms and state."""

    institution: str = "RoundPoint Mortgage Servicing LLC"
    loan_number_masked: Optional[str] = None
    note_date: Optional[str] = None
    first_payment_date: Optional[str] = None
    maturity_date: Optional[str] = None
    interest_rate_percent: Optional[float] = None
    mortgage_type: Optional[str] = None
    term_months: Optional[int] = None
    original_principal_amount: Optional[float] = None
    pi_payment_amount: Optional[float] = None
    current_monthly_escrow_amount: Optional[float] = None
    current_total_monthly_payment: Optional[float] = None
    current_upb: Optional[float] = None
    current_escrow_balance: Optional[float] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoundPointTransaction:
    """Represents a single parsed transaction event from RoundPoint Mortgage."""

    date: str  # YYYY-MM-DD applied date
    effective_date: str  # YYYY-MM-DD
    due_date: Optional[str]  # YYYY-MM-DD or None
    event_type: str  # e.g., 'payment', 'escrow', 'reversals'
    type_description: str  # e.g., 'Payment', 'Tax Disbursement', etc.
    explanation: Optional[str]  # e.g., 'Cash Receipts'
    source_of_funds: Optional[str]  # e.g., 'Draft ACH'
    total_amount: float
    principal_amount: float
    interest_amount: float
    escrow_amount: float
    fees_amount: float
    remaining_principal_balance: float  # UPB immediately after this transaction
    escrow_balance: float
    late_days: int = 0
    grace_status: Optional[str] = None


@dataclass
class ParsedRoundPointData:
    """Container holding metadata and list of parsed transactions."""

    metadata: LoanMetadata
    transactions: List[RoundPointTransaction]


def _parse_float(val: Any, default: float = 0.0) -> float:
    if val is None or val == "":
        return default
    try:
        if isinstance(val, (int, float)):
            return float(val)
        cleaned = str(val).replace("$", "").replace(",", "").strip()
        return float(cleaned)
    except (ValueError, TypeError):
        return default


def _parse_date(date_str: Any) -> Optional[str]:
    if not date_str:
        return None
    val = str(date_str).strip()
    if "T" in val:
        val = val.split("T")[0]
    try:
        # Validate YYYY-MM-DD
        dt = datetime.strptime(val, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        pass
    # Try MM/DD/YYYY
    try:
        dt = datetime.strptime(val, "%m/%d/%Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return val


def parse_raw_transaction_item(item: Dict[str, Any]) -> RoundPointTransaction:
    """Parse a single raw item from RoundPoint API or normalized dict."""
    # Check if this item is in raw BKI format (MonetaryEventAppliedDate) or normalized (date)
    is_raw_bki = "MonetaryEventAppliedDate" in item or "MonetaryEventUPBAmount" in item

    if is_raw_bki:
        applied_date = _parse_date(item.get("MonetaryEventAppliedDate")) or ""
        effective_date = _parse_date(item.get("MonetaryEventEffectiveDate")) or applied_date
        due_date = _parse_date(item.get("MonetaryEventPaymentDueDate"))

        event_type = str(item.get("MonetaryEventType") or "payment").lower()
        type_desc = (
            item.get("MonetaryEventTypeDescription")
            or item.get("MonetaryEventTypeText")
            or "Payment"
        )
        explanation = item.get("MonetaryEventExplanationName")
        source = item.get("MonetaryEventSourceOfFunds")

        total_amount = _parse_float(item.get("MonetaryEventTotalPaymentAmount"))
        principal = _parse_float(item.get("PrincipalPaymentAmount"))
        interest = _parse_float(item.get("InterestPaymentAmount"))
        escrow = _parse_float(item.get("EscrowMonthlyPaymentAmount"))
        fees = _parse_float(item.get("FeeSummaryTotalFeesAmount"))
        upb = _parse_float(item.get("MonetaryEventUPBAmount"))
        escrow_bal = _parse_float(item.get("EscrowBalanceAmount"))
        late_days = int(item.get("LatePaymentDaysCount") or 0)
        grace = item.get("GraceDaysPaidDescription")

        return RoundPointTransaction(
            date=applied_date,
            effective_date=effective_date,
            due_date=due_date,
            event_type=event_type,
            type_description=type_desc,
            explanation=explanation,
            source_of_funds=source,
            total_amount=total_amount,
            principal_amount=principal,
            interest_amount=interest,
            escrow_amount=escrow,
            fees_amount=fees,
            remaining_principal_balance=upb,
            escrow_balance=escrow_bal,
            late_days=late_days,
            grace_status=grace,
        )

    # Otherwise normalized format
    date = _parse_date(item.get("date") or item.get("applied_date")) or ""
    effective_date = _parse_date(item.get("effective_date")) or date
    due_date = _parse_date(item.get("due_date"))

    event_type = str(item.get("event_type") or "payment").lower()
    type_desc = item.get("type_description") or item.get("description") or "Payment"
    explanation = item.get("explanation")
    source = item.get("source_of_funds")

    total_amount = _parse_float(item.get("total_amount") or item.get("amount"))
    principal = _parse_float(item.get("principal_amount") or item.get("principal"))
    interest = _parse_float(item.get("interest_amount") or item.get("interest"))
    escrow = _parse_float(item.get("escrow_amount") or item.get("escrow"))
    fees = _parse_float(item.get("fees_amount") or item.get("fees"))
    upb = _parse_float(
        item.get("remaining_principal_balance")
        or item.get("upb")
        or item.get("balance")
    )
    escrow_bal = _parse_float(item.get("escrow_balance"))
    late_days = int(item.get("late_days") or 0)
    grace = item.get("grace_status")

    return RoundPointTransaction(
        date=date,
        effective_date=effective_date,
        due_date=due_date,
        event_type=event_type,
        type_description=type_desc,
        explanation=explanation,
        source_of_funds=source,
        total_amount=total_amount,
        principal_amount=principal,
        interest_amount=interest,
        escrow_amount=escrow,
        fees_amount=fees,
        remaining_principal_balance=upb,
        escrow_balance=escrow_bal,
        late_days=late_days,
        grace_status=grace,
    )


def parse_roundpoint_json(source: Union[str, Path, Dict[str, Any], List[Any]]) -> ParsedRoundPointData:
    """Parse RoundPoint JSON data from file path or loaded object.

    Handles:
    - Object with 'metadata' and 'transactions'
    - Object with 'LoanActivityPayments'
    - List of transactions
    """
    if isinstance(source, (str, Path)):
        file_path = Path(source)
        if not file_path.exists():
            raise FileNotFoundError(f"Input file not found: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = source

    metadata = LoanMetadata()
    raw_txs: List[Dict[str, Any]] = []

    if isinstance(data, dict):
        # Extract metadata if available
        meta_dict = data.get("metadata", {})
        if meta_dict:
            metadata.institution = meta_dict.get("institution", metadata.institution)
            metadata.loan_number_masked = meta_dict.get("loanNumberMasked")
            metadata.note_date = _parse_date(meta_dict.get("noteDate"))
            metadata.first_payment_date = _parse_date(meta_dict.get("firstPaymentDate") or meta_dict.get("ScheduledFirstPaymentDate"))
            metadata.maturity_date = _parse_date(meta_dict.get("maturityDate"))
            metadata.interest_rate_percent = _parse_float(meta_dict.get("interestRatePercent"), default=0.0) or None
            metadata.mortgage_type = meta_dict.get("mortgageType")
            metadata.term_months = int(meta_dict["termMonths"]) if meta_dict.get("termMonths") else None
            metadata.original_principal_amount = _parse_float(meta_dict.get("NoteAmount") or meta_dict.get("originalPrincipalAmount"), default=0.0) or None
            metadata.pi_payment_amount = _parse_float(meta_dict.get("piPaymentAmount"), default=0.0) or None
            metadata.current_monthly_escrow_amount = _parse_float(meta_dict.get("currentMonthlyEscrowAmount"), default=0.0) or None
            metadata.current_total_monthly_payment = _parse_float(meta_dict.get("currentTotalMonthlyPayment"), default=0.0) or None
            metadata.current_upb = _parse_float(meta_dict.get("currentUPB"), default=0.0) or None
            metadata.current_escrow_balance = _parse_float(meta_dict.get("currentEscrowBalance"), default=0.0) or None

        # Check for top-level loan info keys
        if "NoteDate" in data:
            metadata.note_date = _parse_date(data.get("NoteDate"))
        if "ScheduledFirstPaymentDate" in data:
            metadata.first_payment_date = _parse_date(data.get("ScheduledFirstPaymentDate"))
        if "LoanMaturityDate" in data:
            metadata.maturity_date = _parse_date(data.get("LoanMaturityDate"))
        if "CurrentInterestRatePercent" in data:
            metadata.interest_rate_percent = _parse_float(data.get("CurrentInterestRatePercent"))
        if "PIPaymentAmount" in data:
            metadata.pi_payment_amount = _parse_float(data.get("PIPaymentAmount"))
        if "NoteAmount" in data:
            metadata.original_principal_amount = _parse_float(data.get("NoteAmount"))
        if "UPBAmount" in data:
            metadata.current_upb = _parse_float(data.get("UPBAmount"))

        # Find transaction list
        if "transactions" in data and isinstance(data["transactions"], list):
            raw_txs = data["transactions"]
        elif "LoanActivityPayments" in data and isinstance(data["LoanActivityPayments"], list):
            raw_txs = data["LoanActivityPayments"]
        elif "payments" in data and isinstance(data["payments"], list):
            raw_txs = data["payments"]
    elif isinstance(data, list):
        raw_txs = data

    parsed_txs: List[RoundPointTransaction] = []
    for item in raw_txs:
        if isinstance(item, dict):
            tx = parse_raw_transaction_item(item)
            if tx.date:
                parsed_txs.append(tx)

    # Sort chronological (oldest to newest)
    parsed_txs.sort(key=lambda t: (t.date, t.effective_date))

    return ParsedRoundPointData(metadata=metadata, transactions=parsed_txs)
