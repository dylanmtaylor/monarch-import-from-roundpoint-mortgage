"""Unit tests for Monarch CSV converters."""

import unittest
from roundpoint_to_monarch.converter import (
    convert_to_monarch_balance_history,
    convert_to_monarch_transactions,
)
from roundpoint_to_monarch.parser import RoundPointTransaction


class TestConverter(unittest.TestCase):
    def setUp(self):
        self.tx1 = RoundPointTransaction(
            date="2023-03-01",
            effective_date="2023-03-01",
            due_date="2023-03-01",
            event_type="payment",
            type_description="Payment",
            explanation="Cash Receipts",
            source_of_funds="Draft ACH",
            total_amount=1500.0,
            principal_amount=400.0,
            interest_amount=600.0,
            escrow_amount=500.0,
            fees_amount=0.0,
            remaining_principal_balance=200000.0,
            escrow_balance=2500.0,
        )
        self.tx_tax = RoundPointTransaction(
            date="2023-12-15",
            effective_date="2023-12-15",
            due_date=None,
            event_type="escrow",
            type_description="Tax Disbursement",
            explanation=None,
            source_of_funds=None,
            total_amount=-3000.0,
            principal_amount=0.0,
            interest_amount=0.0,
            escrow_amount=-3000.0,
            fees_amount=0.0,
            remaining_principal_balance=196000.0,
            escrow_balance=500.0,
        )

    def test_convert_to_monarch_transactions_default_negative(self):
        rows = convert_to_monarch_transactions(
            [self.tx1],
            account_name="My Mortgage",
            merchant="RoundPoint",
            positive_payment=False,
        )
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["Date"], "2023-03-01")
        self.assertEqual(row["Merchant"], "RoundPoint")
        self.assertEqual(row["Category"], "Mortgage")
        self.assertEqual(row["Account"], "My Mortgage")
        # In Monarch liability accounts, payments paying down debt are negative:
        self.assertEqual(row["Amount"], "-1500.00")
        self.assertIn("Principal: $400.00", row["Notes"])
        self.assertIn("Interest: $600.00", row["Notes"])
        self.assertIn("Escrow: $500.00", row["Notes"])
        self.assertIn("UPB: $200,000.00", row["Notes"])

    def test_convert_to_monarch_transactions_positive_override(self):
        rows = convert_to_monarch_transactions([self.tx1], positive_payment=True)
        self.assertEqual(rows[0]["Amount"], "1500.00")

    def test_convert_to_monarch_transactions_tax_category(self):
        rows = convert_to_monarch_transactions([self.tx_tax])
        self.assertEqual(rows[0]["Category"], "Property Tax")

    def test_convert_to_monarch_balance_history_default_negative(self):
        # 3 days: 2023-03-01 to 2023-03-03
        rows = convert_to_monarch_balance_history(
            [self.tx1],
            start_date="2023-03-01",
            end_date="2023-03-03",
            positive_balance=False,
        )
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["Date"], "2023-03-01")
        self.assertEqual(rows[0]["Balance"], "-200000.00")
        self.assertEqual(rows[1]["Date"], "2023-03-02")
        self.assertEqual(rows[1]["Balance"], "-200000.00")
        self.assertEqual(rows[2]["Date"], "2023-03-03")
        self.assertEqual(rows[2]["Balance"], "-200000.00")

    def test_convert_to_monarch_balance_history_positive_override(self):
        rows = convert_to_monarch_balance_history(
            [self.tx1],
            start_date="2023-03-01",
            end_date="2023-03-01",
            positive_balance=True,
        )
        self.assertEqual(rows[0]["Balance"], "200000.00")


if __name__ == "__main__":
    unittest.main()
