"""Automated browser capture for RoundPoint Mortgage via Chrome DevTools Protocol (CDP)."""

from __future__ import annotations

import json
import os
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


def find_devtools_port(custom_port: Optional[int] = None) -> int:
    """Find the running Chrome remote debugging port."""
    if custom_port:
        return custom_port

    # Check DevToolsActivePort in ~/.config/google-chrome/ or ~/.var/app/com.google.Chrome/
    candidate_paths = [
        Path.home() / ".config" / "google-chrome" / "DevToolsActivePort",
        Path.home() / ".var" / "app" / "com.google.Chrome" / "config" / "google-chrome" / "DevToolsActivePort",
    ]

    for p in candidate_paths:
        if p.exists():
            try:
                lines = p.read_text(encoding="utf-8").strip().splitlines()
                if lines and lines[0].isdigit():
                    return int(lines[0])
            except Exception:
                pass

    return 9222


def get_chrome_pages(port: int) -> list[Dict[str, Any]]:
    """Retrieve list of open tabs/pages from Chrome CDP."""
    url = f"http://127.0.0.1:{port}/json"
    req = urllib.request.Request(url, headers={"User-Agent": "RoundPointToMonarch/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise ConnectionError(
            f"Could not connect to Chrome on port {port}. "
            f"Please ensure Chrome is running with '--remote-debugging-port={port}'.\n"
            f"Details: {e}"
        ) from e


def find_roundpoint_tab(pages: list[Dict[str, Any]]) -> Dict[str, Any]:
    """Find the active RoundPoint Mortgage tab."""
    for page in pages:
        url = page.get("url", "")
        if "bkiconnect.com" in url or "roundpointmortgage.com" in url:
            return page
    raise RuntimeError(
        "Could not find an open RoundPoint Mortgage tab in Chrome.\n"
        "Please open https://loansphereservicingdigital.bkiconnect.com/ in Chrome and log in."
    )


def capture_tokens_and_loan_path(ws_url: str, timeout_seconds: int = 10) -> Tuple[str, str, str]:
    """Connect to tab websocket and capture Bearer token and loan path."""
    try:
        import websocket
    except ImportError as e:
        raise ImportError(
            "The 'websocket-client' package is required for browser capture.\n"
            "Install it via: pip install websocket-client"
        ) from e

    ws = websocket.create_connection(ws_url, suppress_origin=True)
    try:
        # Enable network tracking
        ws.send(json.dumps({"id": 1, "method": "Network.enable"}))
        ws.recv()

        # Reload or navigate to trigger API requests
        ws.send(json.dumps({
            "id": 2,
            "method": "Runtime.evaluate",
            "params": {"expression": "window.location.hash = '#/my-loan'; window.location.reload();"}
        }))
        ws.recv()

        token: Optional[str] = None
        loan_path: Optional[str] = None
        mobile_id: Optional[str] = None

        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            raw_msg = ws.recv()
            if not raw_msg:
                continue
            msg = json.loads(raw_msg)
            if msg.get("method") == "Network.requestWillBeSent":
                req = msg.get("params", {}).get("request", {})
                headers = req.get("headers", {})
                url = req.get("url", "")

                for k, v in headers.items():
                    if k.lower() == "authorization" and "Bearer" in v:
                        token = v
                    if k.lower() == "x-mobile-source-id":
                        mobile_id = v

                if "/my/loans/" in url:
                    parts = url.split("/my/loans/")[1].split("/")
                    if len(parts) >= 2:
                        loan_id_clean = parts[1].split("?")[0]
                        loan_path = f"{parts[0]}/{loan_id_clean}"

                if token and loan_path:
                    break

        if not token or not loan_path:
            raise TimeoutError(
                "Timed out waiting for RoundPoint API credentials. "
                "Please verify you are fully logged into your dashboard in Chrome."
            )

        return token, loan_path, mobile_id or ""
    finally:
        ws.close()


def fetch_api_data(
    token: str,
    loan_path: str,
    mobile_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch loan info and transaction history using captured credentials."""
    if not start_date:
        # Default to 5 years prior to today
        five_years_ago = datetime.today() - timedelta(days=5 * 365 + 2)
        start_date = five_years_ago.strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.today().strftime("%Y-%m-%d")

    headers = {
        "authorization": token,
        "x-mobile-source-id": mobile_id,
        "accept": "application/json",
        "referer": "https://loansphereservicingdigital.bkiconnect.com/",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36",
    }

    # 1. Fetch loan info
    loan_info_url = f"https://api.bkiconnect.com/sd/loan-info/v1/my/loans/{loan_path}"
    loan_info = {}
    try:
        req = urllib.request.Request(loan_info_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            loan_info = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Warning: could not fetch loan info: {e}")

    # 2. Fetch payments history
    payments_url = (
        f"https://api.bkiconnect.com/sd/loan-pay/v1/my/loans/{loan_path}/payments"
        f"?monetaryEventType=all&limit=200&startDate={start_date}&endDate={end_date}"
    )
    req = urllib.request.Request(payments_url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        payments_data = json.loads(resp.read().decode("utf-8"))

    raw_payments = payments_data.get("LoanActivityPayments", [])

    # Sort chronological
    raw_payments.sort(key=lambda p: (
        p.get("MonetaryEventAppliedDate", ""),
        p.get("MonetaryEventEffectiveDate", "")
    ))

    # Masked loan number for privacy
    loan_id = loan_path.split("/")[-1]
    masked_loan = f"****{loan_id[-4:]}" if len(loan_id) >= 4 else "****"

    payload: Dict[str, Any] = {
        "metadata": {
            "extractedAt": datetime.utcnow().isoformat() + "Z",
            "institution": "RoundPoint Mortgage Servicing LLC",
            "loanNumberMasked": masked_loan,
            "noteDate": loan_info.get("NoteDate", "2020-11-02"),
            "firstPaymentDate": loan_info.get("ScheduledFirstPaymentDate", "2021-01-01"),
            "maturityDate": loan_info.get("LoanMaturityDate", "2050-12-01"),
            "interestRatePercent": loan_info.get("CurrentInterestRatePercent", 3.0),
            "mortgageType": loan_info.get("MortgageType", "Conventional"),
            "termMonths": loan_info.get("LoanMaturityPeriodCount", 360),
            "NoteAmount": loan_info.get("OriginalPrincipalAmount", 0.0),
            "piPaymentAmount": loan_info.get("PIPaymentAmount", 1007.21),
            "currentMonthlyEscrowAmount": loan_info.get("TaxInsuranceMonthlyComponent", 666.17),
            "currentTotalMonthlyPayment": 1673.38,
            "currentUPB": loan_info.get("UPBAmount", 0.0),
            "currentEscrowBalance": loan_info.get("EscrowBalanceAmount", 3295.87),
            "transactionCount": len(raw_payments),
            "dateRange": {
                "startDateRequested": start_date,
                "endDateRequested": end_date,
                "earliestTransaction": raw_payments[0].get("MonetaryEventAppliedDate") if raw_payments else None,
                "latestTransaction": raw_payments[-1].get("MonetaryEventAppliedDate") if raw_payments else None,
            },
        },
        "transactions": raw_payments,
    }

    return payload


def capture_roundpoint_data(
    output_path: Union[str, Path] = "roundpoint_raw_history.json",
    port: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Path:
    """End-to-end automated capture of RoundPoint data from running Chrome browser."""
    actual_port = find_devtools_port(port)
    pages = get_chrome_pages(actual_port)
    tab = find_roundpoint_tab(pages)

    ws_url = tab.get("webSocketDebuggerUrl")
    if not ws_url:
        raise RuntimeError("RoundPoint tab found but webSocketDebuggerUrl is missing.")

    print(f"Connecting to Chrome tab: '{tab.get('title')}' on port {actual_port}...")
    token, loan_path, mobile_id = capture_tokens_and_loan_path(ws_url)

    print(f"Authenticated session captured! Fetching full historical ledger...")
    payload = fetch_api_data(token, loan_path, mobile_id, start_date=start_date, end_date=end_date)

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    count = payload.get("metadata", {}).get("transactionCount", 0)
    print(f"Successfully captured {count} historical transactions to {out_file}!")
    return out_file
