# Monarch Import from RoundPoint Mortgage

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Monarch Money](https://img.shields.io/badge/Monarch%20Money-Compatible-blueviolet.svg)](https://www.monarchmoney.com/)

An automated command-line utility to extract and convert **RoundPoint Mortgage** servicing records into continuous daily balance history and itemized transaction CSV files designed specifically for import into **[Monarch Money](https://www.monarchmoney.com/)**.

RoundPoint Mortgage (serviced on Black Knight / ICE Mortgage Technology Servicing Digital) does not offer a direct one-click CSV export button and restricts downloadable PDF statements to an 18-month rolling window. This tool connects directly to your active authenticated session to capture the full multi-year transaction ledger and unpaid principal balance (UPB) history, formatting it for Monarch Money.

---

## 🌟 Key Features

- 🚀 **Automated Chrome Capture**: Connects via Chrome DevTools Protocol (CDP) to your authenticated browser session to extract the complete servicing ledger and loan terms in seconds.
- 💳 **Detailed Monarch Transactions**: Produces `roundpoint_monarch_transactions.csv` formatted with merchant, categories (`Mortgage`, `Property Tax`, `Home Insurance`), and detailed notes with principal, interest, and escrow breakdowns.
- 📉 **Continuous Daily Balance History**: Generates `roundpoint_monarch_balance_history.csv` forward-filling daily unpaid principal balances so net worth and liability charts render smoothly with no gaps.
- 📐 **Full Origination Backfill (`--from-origination`)**: Uses your exact Note terms (origination date, original principal, and fixed interest rate) to mathematically backfill scheduled amortization payments from loan closing up to RoundPoint boarding.
- ⚖️ **Monarch Liability Conventions**: Formats balances and payments as negative numbers in compliance with Monarch Money's official requirements for liability accounts, preventing net worth inversion bugs.
- 🔒 **Zero Data Leakage**: All raw JSON and output CSV files are automatically excluded by `.gitignore`. Test fixtures use strictly synthetic mock data.

---

## 🛠️ How It Works

```
┌─────────────────────────────────┐
│   Chrome Browser (Authenticated)│
│  RoundPoint / Servicing Digital │
└────────────────┬────────────────┘
                 │ Chrome DevTools Protocol (CDP)
                 ▼
┌─────────────────────────────────┐
│  roundpoint-to-monarch capture  │
│  (Extracts 5-Year API Ledger)   │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│   roundpoint_raw_history.json   │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  roundpoint-to-monarch convert  │
│  (with optional --from-origin)  │
└────────────────┬────────────────┘
                 │
        ┌────────┴──────────────────────────┐
        ▼                                   ▼
┌─────────────────────────────────┐   ┌─────────────────────────────────┐
│ roundpoint_monarch_             │   │ roundpoint_monarch_             │
│ balance_history.csv             │   │ transactions.csv                │
│ (Daily continuous snapshots)    │   │ (Principal, Interest, Escrow)   │
└─────────────────────────────────┘   └─────────────────────────────────┘
```

---

## 💻 Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/dylanmtaylor/monarch-import-from-roundpoint-mortgage.git
cd monarch-import-from-roundpoint-mortgage
pip install -e .
```

---

## 🚀 Usage

### Option 1: Automated Capture & Convert (Recommended)

1. Launch Google Chrome with remote debugging enabled:
   ```bash
   # Standard Linux / macOS / Windows Chrome:
   google-chrome --remote-debugging-port=9222 &

   # Flatpak Chrome (Linux):
   flatpak run com.google.Chrome --remote-debugging-port=9222 &
   ```
2. In the opened Chrome window, navigate to your RoundPoint servicing portal and log in:
   [https://loansphereservicingdigital.bkiconnect.com/servicinghome/#/login](https://loansphereservicingdigital.bkiconnect.com/servicinghome/#/login)
3. Once logged in, run the capture command:
   ```bash
   roundpoint-to-monarch capture --from-origination -o ./output
   ```

The tool will connect to Chrome, extract your complete payment ledger and loan metadata, save `roundpoint_raw_history.json`, and generate your Monarch CSV files in `./output/`.

---

### Option 2: Convert an Existing JSON Export

If you already have `roundpoint_raw_history.json` or `roundpoint_mortgage_history.json`:

```bash
# Convert RoundPoint serviced records:
roundpoint-to-monarch roundpoint_raw_history.json -o ./output

# Or backfill full history to note origination:
roundpoint-to-monarch roundpoint_raw_history.json -o ./output --from-origination
```

---

## ⚙️ Command-Line Options

| Option | Description | Default |
|---|---|---|
| `input_file` | Path to RoundPoint JSON file | `roundpoint_raw_history.json` |
| `-o`, `-d`, `--output-dir` | Directory where generated CSVs are saved | `./output` |
| `-a`, `--account-name` | Account name matching Monarch Money | `RoundPoint Mortgage` |
| `-m`, `--merchant` | Merchant name on transaction records | `RoundPoint Mortgage Servicing` |
| `--from-origination` | Backfills amortization from note origination | `False` |
| `--positive-balance` | Outputs balance as positive (instead of negative) | `False` |
| `--positive-payment` | Outputs payments as positive (instead of negative) | `False` |
| `--no-escrow` | Excludes property tax & insurance escrow disbursements | `False` |
| `--start-date` | Filters export starting from `YYYY-MM-DD` | None |
| `--end-date` | Filters export ending at `YYYY-MM-DD` | None |
| `--port` | Chrome DevTools remote debugging port | `9222` (or autodetected) |

---

## 📥 Importing into Monarch Money

Always import via the **Monarch Money Web App** (browser):

### Step 1: Import Balance History (Recommended First)
1. In Monarch, navigate to **Accounts** and select your mortgage account.
2. Click **Edit** in the top-right corner.
3. Click **Upload balance history** (or **Import balance history**).
4. Select `roundpoint_monarch_balance_history.csv`.
5. Verify column mappings (`Date` $\rightarrow$ Date, `Balance` $\rightarrow$ Balance).
6. Click **Import**.

### Step 2: Import Transactions
1. From the same account page, click **Edit** $\rightarrow$ **Upload transactions**.
2. Select `roundpoint_monarch_transactions.csv`.
3. Confirm the column mappings:
   - `Date` $\rightarrow$ Date
   - `Merchant` $\rightarrow$ Merchant
   - `Category` $\rightarrow$ Category
   - `Account` $\rightarrow$ Account
   - `Original Statement` $\rightarrow$ Original Statement
   - `Notes` $\rightarrow$ Notes
   - `Amount` $\rightarrow$ Amount
4. Review preview and complete import.

---

## 🧪 Testing

To run the unit test suite:

```bash
python3 -m unittest discover -s tests -v
```

All tests use strictly synthetic fixtures with zero personal identifying information.

---

## 🔒 Privacy & Security

Your mortgage details and financial data are private:
- The `.gitignore` prevents all `.json`, `.csv`, `.pdf`, `.html`, and `output/` files from being tracked by Git.
- No network requests are sent outside your local machine and RoundPoint's official servicing domain (`api.bkiconnect.com`).
- Always run `git status` before committing to verify no personal files are staged.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
