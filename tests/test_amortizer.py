"""Unit tests for mortgage amortizer backfill."""

import unittest
from roundpoint_to_monarch.amortizer import add_month, generate_amortization_schedule


class TestAmortizer(unittest.TestCase):
    def test_add_month(self):
        from datetime import datetime
        dt = datetime(2021, 1, 1)
        next_dt = add_month(dt)
        self.assertEqual(next_dt.year, 2021)
        self.assertEqual(next_dt.month, 2)

        dt_dec = datetime(2021, 12, 1)
        next_dt_dec = add_month(dt_dec)
        self.assertEqual(next_dt_dec.year, 2022)
        self.assertEqual(next_dt_dec.month, 1)

    def test_generate_amortization_schedule(self):
        # Test 12 months of a $240,000 loan at 3% interest, $1,011.87/mo
        orig_bal = 240000.0
        rate = 3.0
        first_pmt = "2021-01-01"
        monthly_pi = 1011.87
        until_date = "2022-01-01"

        records = generate_amortization_schedule(
            origination_balance=orig_bal,
            interest_rate_percent=rate,
            first_payment_date=first_pmt,
            monthly_pi_amount=monthly_pi,
            until_date=until_date,
        )

        # Should generate 12 payments (2021-01-01 through 2021-12-01)
        self.assertEqual(len(records), 12)
        self.assertEqual(records[0].date, "2021-01-01")
        self.assertEqual(records[-1].date, "2021-12-01")

        # First payment math:
        # interest = 240,000 * (0.03 / 12) = 600.00
        # principal = 1011.87 - 600.00 = 411.87
        # balance = 240000 - 411.87 = 239588.13
        self.assertEqual(records[0].interest_amount, 600.00)
        self.assertEqual(records[0].principal_amount, 411.87)
        self.assertEqual(records[0].remaining_principal_balance, 239588.13)

        # Verify balance decreases monotonically
        for i in range(len(records) - 1):
            self.assertGreater(
                records[i].remaining_principal_balance,
                records[i + 1].remaining_principal_balance,
            )

    def test_until_date_immediate_stop(self):
        records = generate_amortization_schedule(
            origination_balance=240000.0,
            interest_rate_percent=3.0,
            first_payment_date="2021-01-01",
            monthly_pi_amount=1011.87,
            until_date="2021-01-01",
        )
        self.assertEqual(len(records), 0)


if __name__ == "__main__":
    unittest.main()
