"""Unit tests for RoundPoint JSON parser."""

import unittest
from roundpoint_to_monarch.parser import (
    LoanMetadata,
    RoundPointTransaction,
    parse_raw_transaction_item,
    parse_roundpoint_json,
)


class TestParser(unittest.TestCase):
    def setUp(self):
        self.synthetic_raw_bki = {
            "metadata": {
                "institution": "RoundPoint Mortgage Servicing LLC",
                "loanNumberMasked": "****1234",
                "noteDate": "2021-01-15",
                "firstPaymentDate": "2021-03-01",
                "maturityDate": "2051-02-01",
                "interestRatePercent": 3.25,
                "mortgageType": "Conventional",
                "termMonths": 360,
                "NoteAmount": 250000.0,
                "piPaymentAmount": 1088.02,
                "currentMonthlyEscrowAmount": 450.0,
                "currentTotalMonthlyPayment": 1538.02,
                "currentUPB": 240000.0,
                "currentEscrowBalance": 2100.0,
            },
            "transactions": [
                {
                    "MonetaryEventAppliedDate": "2023-03-01",
                    "MonetaryEventEffectiveDate": "2023-03-01",
                    "MonetaryEventPaymentDueDate": "2023-03-01",
                    "MonetaryEventType": "payment",
                    "MonetaryEventTypeText": "Payment",
                    "MonetaryEventTypeDescription": "Monthly Mortgage Payment",
                    "MonetaryEventExplanationName": "Cash Receipts",
                    "MonetaryEventSourceOfFunds": "Draft ACH",
                    "MonetaryEventTotalPaymentAmount": 1538.02,
                    "PrincipalPaymentAmount": 410.50,
                    "InterestPaymentAmount": 677.52,
                    "EscrowMonthlyPaymentAmount": 450.0,
                    "FeeSummaryTotalFeesAmount": 0,
                    "MonetaryEventUPBAmount": 239589.50,
                    "EscrowBalanceAmount": 2550.0,
                    "LatePaymentDaysCount": 0,
                    "GraceDaysPaidDescription": "ByDueDate",
                },
                {
                    "MonetaryEventAppliedDate": "2023-04-01",
                    "MonetaryEventEffectiveDate": "2023-04-01",
                    "MonetaryEventPaymentDueDate": "2023-04-01",
                    "MonetaryEventType": "payment",
                    "MonetaryEventTypeText": "Payment",
                    "MonetaryEventTypeDescription": "Monthly Mortgage Payment",
                    "MonetaryEventExplanationName": "Cash Receipts",
                    "MonetaryEventSourceOfFunds": "Draft ACH",
                    "MonetaryEventTotalPaymentAmount": 1538.02,
                    "PrincipalPaymentAmount": 411.61,
                    "InterestPaymentAmount": 676.41,
                    "EscrowMonthlyPaymentAmount": 450.0,
                    "FeeSummaryTotalFeesAmount": 0,
                    "MonetaryEventUPBAmount": 239177.89,
                    "EscrowBalanceAmount": 3000.0,
                    "LatePaymentDaysCount": 0,
                    "GraceDaysPaidDescription": "ByDueDate",
                },
            ],
        }

        self.synthetic_normalized_list = [
            {
                "date": "2023-05-01",
                "effective_date": "2023-05-01",
                "due_date": "2023-05-01",
                "event_type": "payment",
                "type_description": "Payment",
                "explanation": "Cash Receipts",
                "source_of_funds": "Draft ACH",
                "total_amount": 1538.02,
                "principal_amount": 412.72,
                "interest_amount": 675.30,
                "escrow_amount": 450.0,
                "fees_amount": 0.0,
                "remaining_principal_balance": 238765.17,
                "escrow_balance": 3450.0,
                "late_days": 0,
                "grace_status": "ByDueDate",
            }
        ]

    def test_parse_raw_bki_item(self):
        raw_item = self.synthetic_raw_bki["transactions"][0]
        tx = parse_raw_transaction_item(raw_item)
        self.assertEqual(tx.date, "2023-03-01")
        self.assertEqual(tx.total_amount, 1538.02)
        self.assertEqual(tx.principal_amount, 410.50)
        self.assertEqual(tx.interest_amount, 677.52)
        self.assertEqual(tx.escrow_amount, 450.0)
        self.assertEqual(tx.remaining_principal_balance, 239589.50)
        self.assertEqual(tx.event_type, "payment")

    def test_parse_normalized_item(self):
        norm_item = self.synthetic_normalized_list[0]
        tx = parse_raw_transaction_item(norm_item)
        self.assertEqual(tx.date, "2023-05-01")
        self.assertEqual(tx.total_amount, 1538.02)
        self.assertEqual(tx.principal_amount, 412.72)
        self.assertEqual(tx.remaining_principal_balance, 238765.17)

    def test_parse_roundpoint_json_dict_format(self):
        parsed = parse_roundpoint_json(self.synthetic_raw_bki)
        self.assertEqual(len(parsed.transactions), 2)
        self.assertEqual(parsed.metadata.note_date, "2021-01-15")
        self.assertEqual(parsed.metadata.interest_rate_percent, 3.25)
        self.assertEqual(parsed.metadata.original_principal_amount, 250000.0)
        self.assertEqual(parsed.transactions[0].date, "2023-03-01")
        self.assertEqual(parsed.transactions[1].date, "2023-04-01")

    def test_parse_roundpoint_json_list_format(self):
        parsed = parse_roundpoint_json(self.synthetic_normalized_list)
        self.assertEqual(len(parsed.transactions), 1)
        self.assertEqual(parsed.transactions[0].date, "2023-05-01")
        self.assertEqual(parsed.transactions[0].principal_amount, 412.72)

    def test_empty_input(self):
        parsed = parse_roundpoint_json([])
        self.assertEqual(len(parsed.transactions), 0)
        self.assertIsInstance(parsed.metadata, LoanMetadata)


if __name__ == "__main__":
    unittest.main()
