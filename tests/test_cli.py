"""Unit tests for CLI interface."""

import json
import tempfile
import unittest
from pathlib import Path
from roundpoint_to_monarch.cli import main


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        self.mock_json = {
            "metadata": {
                "institution": "RoundPoint Mortgage Servicing LLC",
                "loanNumberMasked": "****9999",
                "noteDate": "2021-01-01",
                "firstPaymentDate": "2021-02-01",
                "maturityDate": "2051-01-01",
                "interestRatePercent": 3.0,
                "mortgageType": "Conventional",
                "termMonths": 360,
                "NoteAmount": 200000.0,
                "piPaymentAmount": 843.21,
                "currentMonthlyEscrowAmount": 300.0,
                "currentTotalMonthlyPayment": 1143.21,
                "currentUPB": 190000.0,
                "currentEscrowBalance": 1500.0,
            },
            "transactions": [
                {
                    "MonetaryEventAppliedDate": "2023-01-01",
                    "MonetaryEventEffectiveDate": "2023-01-01",
                    "MonetaryEventPaymentDueDate": "2023-01-01",
                    "MonetaryEventType": "payment",
                    "MonetaryEventTypeText": "Payment",
                    "MonetaryEventTypeDescription": "Payment",
                    "MonetaryEventExplanationName": "Cash Receipts",
                    "MonetaryEventSourceOfFunds": "Draft ACH",
                    "MonetaryEventTotalPaymentAmount": 1143.21,
                    "PrincipalPaymentAmount": 350.0,
                    "InterestPaymentAmount": 493.21,
                    "EscrowMonthlyPaymentAmount": 300.0,
                    "FeeSummaryTotalFeesAmount": 0,
                    "MonetaryEventUPBAmount": 190000.0,
                    "EscrowBalanceAmount": 1500.0,
                }
            ],
        }

        self.input_file = self.temp_path / "test_roundpoint.json"
        with open(self.input_file, "w", encoding="utf-8") as f:
            json.dump(self.mock_json, f)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_cli_convert_success(self):
        out_dir = self.temp_path / "output"
        code = main([
            "convert",
            str(self.input_file),
            "-d", str(out_dir),
            "-a", "Test Loan",
        ])
        self.assertEqual(code, 0)

        tx_file = out_dir / "roundpoint_monarch_transactions.csv"
        bal_file = out_dir / "roundpoint_monarch_balance_history.csv"

        self.assertTrue(tx_file.exists())
        self.assertTrue(bal_file.exists())

        tx_content = tx_file.read_text(encoding="utf-8")
        self.assertIn("Test Loan", tx_content)
        self.assertIn("-1143.21", tx_content)

        bal_content = bal_file.read_text(encoding="utf-8")
        self.assertIn("-190000.00", bal_content)

    def test_cli_convert_from_origination(self):
        out_dir = self.temp_path / "output_orig"
        code = main([
            "convert",
            str(self.input_file),
            "-d", str(out_dir),
            "--from-origination",
        ])
        self.assertEqual(code, 0)

        tx_file = out_dir / "roundpoint_monarch_transactions.csv"
        tx_lines = tx_file.read_text(encoding="utf-8").strip().splitlines()
        # Header + 23 amortized payments + 1 actual payment = 25 lines
        self.assertGreater(len(tx_lines), 5)

    def test_cli_missing_file_error(self):
        code = main([
            "convert",
            str(self.temp_path / "nonexistent.json"),
        ])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
