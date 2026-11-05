# StatementIQ — Code Guide

A walkthrough of how the Bank Statement Processing & Classification System was built, component by component.

This guide is written so you can explain the project in an interview or viva, debug it quickly, and extend it safely.

---

## 1. What the system does

StatementIQ accepts bank statement PDFs and:

1. Detects whether the PDF is text-based or scanned.
2. Extracts account metadata and transaction rows.
3. Normalizes dates, amounts, and descriptions.
4. Validates the ledger using balance continuity.
5. Classifies every transaction with a **non-LLM** hybrid engine:
   - deterministic regex/heuristic rules, then
   - a traditional TF-IDF + Logistic Regression model.
6. Persists everything in SQLite.
7. Lets the user review, correct categories, and export CSV/XLSX through a Flask web UI.

The assessment requirement “no LLMs for classification” is satisfied: classification uses regex rules and a classical ML model trained on synthetic descriptions.

---

## 2. Quick start

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate synthetic statements (text + scanned PDFs)
python -m synthetic --count 12 --out data/samples --image-ratio 0.35 --clean

# 3. Train the classifier (optional; it auto-trains on first app start)
python scripts/train_classifier.py

# 4. Seed the local demo database with a few statements
python scripts/seed_demo.py --reset

# 5. Run the app
python run.py
# Open http://127.0.0.1:5000

# 6. Verify
python -m pytest -q
python scripts/evaluate.py --samples data/samples
```

**OCR dependency:** Tesseract must be installed. On Windows it is usually at
`C:\Program Files\Tesseract-OCR\tesseract.exe`; the app auto-detects it.
You can override it with the `TESSERACT_CMD` environment variable.

**Reset everything:**

```powershell
python scripts/seed_demo.py --reset
```

---

## 3. Architecture at a glance

```text
Browser (Jinja2 templates + vanilla JS + Tailwind CDN)
        |
        | fetch() JSON / form uploads
        v
Flask app (app/__init__.py, app/api/routes.py)
        |
        v
Processing pipeline (app/core/pipeline.py)
        |
        +--> PDF type detection (pdf_detector.py)
        +--> Text extraction (extractors/text_pdf.py)
        +--> OCR extraction (extractors/ocr_pdf.py)
        +--> Normalization (extractors/normalize.py)
        +--> Account metadata parsing (extractors/common.py)
        +--> Validation (validators.py)
        +--> Classification engine (classifiers/pipeline.py)
                 |
                 +--> Rule engine (classifiers/rules.py + data/rules.json)
                 +--> ML model (classifiers/ml.py + data/models/classifier.joblib)
        |
        v
SQLite (app/db.py + data/app.db)  --> API payloads / CSV / XLSX
```

### End-to-end data flow

1. User uploads a PDF from `/upload`.
2. `POST /api/statements` saves the file, hashes it, and checks duplicates.
3. `detect_pdf_type()` decides text vs scanned.
4. Text PDFs go through `pdfplumber`; scanned PDFs are rendered and OCR’d with Tesseract.
5. `validate_transactions()` fixes/validates debit-credit direction and balance continuity.
6. `ClassificationEngine.classify()` classifies each description.
7. Rows are inserted into SQLite (`statements` + `transactions`).
8. Review UI fetches `/api/statements/<id>` and allows category edits.
9. Export generates CSV/XLSX from stored data.

---

## 4. Directory map

```text
befree/
├── run.py                     # entry point
├── requirements.txt
├── CODE_GUIDE.md
├── app/
│   ├── __init__.py            # Flask app factory, HTML routes, CORS, error handlers
│   ├── config.py              # paths, upload limit, OCR settings
│   ├── errors.py              # ApiError / ExtractionError
│   ├── models.py              # Statement / Transaction dataclasses
│   ├── db.py                  # SQLite access layer
│   ├── api/routes.py          # REST API
│   ├── core/
│   │   ├── pipeline.py        # orchestration
│   │   ├── pdf_detector.py    # text vs scanned detection
│   │   ├── validators.py      # balance/duplicate/direction checks
│   │   ├── exporter.py        # CSV + styled XLSX
│   │   ├── extractors/
│   │   │   ├── normalize.py   # amount/date parsing
│   │   │   ├── common.py      # bank, holder, IFSC, period, balances
│   │   │   ├── line_parser.py # fallback/OCR line parsing
│   │   │   ├── text_pdf.py    # pdfplumber table parsing
│   │   │   ├── ocr_pdf.py     # PyMuPDF render + Tesseract
│   │   │   └── base.py        # RawTransaction / ExtractionResult
│   │   └── classifiers/
│   │       ├── rules.py       # regex/heuristic engine
│   │       ├── ml.py          # TF-IDF + Logistic Regression
│   │       ├── pipeline.py    # hybrid router + confidence policy
│   │       └── merchants.py   # synthetic descriptions + training corpus
│   └── static/
│       ├── js/app.js          # UI hydration for all four pages
│       └── css/app.css        # toasts, menus, small overrides
│   └── templates/             # dashboard, upload, review, categories
├── data/
│   ├── categories.json        # 16 category definitions + colors/keywords
│   ├── rules.json             # 22 heuristic rules (168 patterns)
│   ├── models/classifier.joblib
│   ├── samples/               # synthetic PDFs + labels.json
│   ├── app.db                 # SQLite database
│   └── uploads/               # stored source PDFs
├── synthetic/
│   ├── generator.py           # 3 bank layouts, transactions, PDFs
│   └── __main__.py            # CLI
├── scripts/
│   ├── train_classifier.py
│   ├── evaluate.py
│   └── seed_demo.py
└── tests/
    ├── test_normalize.py
    ├── test_classifier.py
    ├── test_pipeline.py
    ├── test_ocr.py
    └── test_api.py
```

---

## 5. Component-by-component

### 5.1 App factory and configuration

Files: `app/__init__.py`, `app/config.py`

- `create_app()` builds the Flask app, applies config overrides (used by tests), creates directories, initializes SQLite, and builds the `ClassificationEngine`.
- The engine is stored in `app.extensions["classification_engine"]`; the DB is in `app.extensions["db"]`.
- HTML routes:
  - `/` dashboard
  - `/upload` upload page
  - `/statements/<id>` statement review
  - `/transactions` transactions workspace (latest statement, with statement switcher)
  - `/categories` taxonomy/rules page
- CORS headers are added in `after_request` so the UI can also be developed separately.
- Error handlers convert `ApiError`, `413`, `404`, and uncaught exceptions into consistent JSON for API routes.

`Config` centralizes:

```text
DATABASE_PATH, UPLOAD_DIR, MODEL_DIR, CATEGORIES_PATH, RULES_PATH,
MAX_CONTENT_LENGTH (20 MB default), OCR_DPI (300), TESSERACT_CMD
```

Tesseract detection checks the `TESSERACT_CMD` env var, `PATH`, and common Windows/Linux install locations.

---

### 5.2 Synthetic data generator

Files: `synthetic/generator.py`, `synthetic/__main__.py`

The assessment allows synthetic data, so the generator creates realistic statements and ground-truth labels.

Three layouts are simulated:

| Profile | Columns | Notes |
|---|---|---|
| `hdfc` | Date, Narration, Ref, Value Dt, Withdrawal, Deposit, Closing Balance | 7 columns, blue header |
| `icici` | Date, Mode, Particulars, Withdrawals, Deposits, Balance | 6 columns |
| `sbi` | Txn Date, Value Date, Description, Ref, Debit, Credit, Balance | 7 columns |

How it works:

1. `_schedule_events()` creates a realistic monthly calendar:
   - salary credit, rent, EMI, utilities, food, groceries, shopping, transport, cash, entertainment, healthcare/travel occasionally, fees, transfers, small income credits.
2. `_materialize()`:
   - sorts events by date,
   - assigns amounts from category ranges,
   - keeps balance continuity (`balance += credit - debit`),
   - reduces a debit if it would overdraw the account.
3. `build_description()` in `classifiers/merchants.py` generates bank-style narrations such as:
   - `UPI-DR-12345678-SWIGGY-ybl`
   - `NEFT CR-INFOSYS-SALARY APR 2025-...`
   - `POS/12345678/IRCTC/BENGALURU`
4. `_build_pdf()` renders a multi-page reportlab PDF with repeated table headers.
5. `convert_to_image_pdf()` renders pages at 300 DPI with PyMuPDF and saves an image-only PDF for the OCR path.
6. The CLI writes `data/samples/labels.json` with exact account data and transaction categories.

Important: the same `build_description()` function is reused to build the ML training corpus. That keeps synthetic labels and the classifier vocabulary aligned.

Useful commands:

```powershell
python -m synthetic --count 12 --months 2 --density 0.8 --image-ratio 0.35 --clean
python -m synthetic --count 2 --image-ratio 1.0 --out data/samples_image
```

---

### 5.3 PDF type detection

File: `app/core/pdf_detector.py`

`detect_pdf_type(path)` uses PyMuPDF:

- Rejects encrypted PDFs (`needs_pass` → `ExtractionError("pdf_encrypted")`).
- Rejects empty PDFs.
- Reads the text layer length per page and counts image-only pages.
- Returns:

```json
{
  "pdf_type": "text" | "image" | "mixed",
  "pages": 3,
  "text_chars": 4200,
  "image_pages": 0
}
```

Decision rules:

- Enough text on most pages → `text`
- Almost no text and images present → `image`
- Some text + image pages → `mixed` (try text first, then OCR fallback)

---

### 5.4 Text PDF extraction

File: `app/core/extractors/text_pdf.py`

`extract_text_pdf(path)`:

1. Opens the PDF with `pdfplumber`.
2. Extracts plain text for metadata.
3. Calls `page.extract_tables()` for each page.
4. `_find_header()` finds the transaction header row.
5. `_classify_header()` maps header cells to roles:

| Header contains | Role |
|---|---|
| balance | `balance` |
| withdraw / debit / dr | `debit` |
| deposit / credit / cr | `credit` |
| date | `date` (first date column wins; Value Date is ignored unless no other date) |
| narration / particular / description / remark / detail | `desc` |

6. `parse_table()` skips:
   - rows without a valid date,
   - opening/closing balance rows,
   - totals,
   - malformed rows without amounts.
7. If table parsing returns nothing, it falls back to `parse_transaction_lines()` on the plain text.

Why this design:

- It is deterministic and fast.
- It works across the three generated layouts because columns are discovered from headers, not hardcoded positions.
- The line parser gives a second chance when table extraction fails.

---

### 5.5 OCR extraction

Files: `app/core/extractors/ocr_pdf.py`, `line_parser.py`

`extract_image_pdf(path)`:

1. Verifies Tesseract is available.
2. Renders each page at 300 DPI with PyMuPDF.
3. Converts to grayscale and applies autocontrast.
4. Runs Tesseract with:

```text
--oem 3 --psm 6 -c preserve_interword_spaces=1
```

5. Applies small OCR numeric fixes (`O→0`, `I/l→1`, `S→5` only between digits).
6. Parses lines with `parse_transaction_line()`.
7. Extracts bank/account metadata from the same OCR text.

`parse_transaction_line()`:

- Requires a date at the start of the line.
- Finds amounts with a decimal part (e.g., `1,23,456.78`).
- Uses:
  - last amount = balance,
  - second-last amount = transaction amount (direction inferred later from balance movement).
- Skips obvious footer/header lines.

Why direction is inferred later: OCR often loses column positions, so the balance delta is more reliable than guessing which amount column it came from.

---

### 5.6 Normalization

File: `app/core/extractors/normalize.py`

`parse_amount()` handles:

- `1,23,456.78`, `₹1,234.50`, `Rs. 450.00`
- `450.00 Cr` / `450.00 Dr`
- parentheses as negative: `(1,000.50)`
- dashes/empty cells → `None`
- OCR-style stray spaces inside numbers

`parse_date()` supports:

- `01/04/2025`, `01-04-25`, `01.04.2025`
- `01 Apr 2025`, `01-APR-2025`, `Apr 01, 2025`
- ISO `2025-04-01`
- Returns ISO date strings (`YYYY-MM-DD`) for stable storage/API output.

`normalize_ws()` collapses whitespace from PDF cells.

---

### 5.7 Account metadata parsing

File: `app/core/extractors/common.py`

`extract_account_info(text)` uses regex patterns for:

- account holder (`Account Holder`, `Customer Name`, `Name`)
- account number (`Account No`, `A/c`, `Acct`)
- IFSC (`^[A-Z]{4}0[A-Z0-9]{6}$`, e.g., `HDFC0001234`)
- statement period (`Statement Period: 01/04/2025 to 30/06/2025`)
- opening/closing balance (`Opening Balance`, `Balance B/F`, `Closing Balance`)

`detect_bank(text)` checks the **first 15 lines first**, then the whole document. This avoids false matches where a transaction description mentions another bank (e.g., an SBI statement containing “ICICI BANK” in a narration).

`infer_period()` falls back to the min/max transaction dates if the period line is missing.

---

### 5.8 Validation and balance reconciliation

File: `app/core/validators.py`

`validate_transactions(raw_transactions, account)` is the “accounting brain”.

For each row it:

1. Converts debit/credit to positive numbers.
2. If direction is missing, infers it from `balance - previous_balance`:
   - negative delta → debit
   - positive delta → credit
3. If debit and credit are both set → flags `both_debit_and_credit`.
4. Checks:

```text
expected_balance = previous_balance - debit + credit
```

5. If the stated balance differs:
   - tries swapping debit/credit (direction correction), otherwise
   - marks `balance_mismatch` and sets `needs_review`.
6. Detects duplicate rows using `(date, description, debit, credit, balance)`.
7. Flags out-of-order dates and closing-balance mismatch at statement level.
8. Returns `Transaction` objects plus statement-level warnings.

Why this matters: it turns noisy OCR/table output into a self-checking ledger. A bad row is surfaced instead of silently trusted.

---

### 5.9 Classification engine (non-LLM)

Files:

- `app/core/classifiers/rules.py`
- `app/core/classifiers/ml.py`
- `app/core/classifiers/pipeline.py`
- `app/core/classifiers/merchants.py`
- `data/categories.json`
- `data/rules.json`

#### Rule engine

`RuleEngine` loads 22 rules / 168 regex patterns from `rules.json`.

Each rule has:

```json
{
  "id": "salary_credit",
  "category": "Salary & Income",
  "direction": "credit",
  "confidence": 0.98,
  "patterns": ["\\bsalary\\b", "\\bpayroll\\b"]
}
```

Matching behavior:

- Rules can be `credit`, `debit`, or `any`.
- Direction-specific rules are skipped if the direction does not match.
- When direction is unknown, directional rules receive a confidence penalty.
- The highest effective-confidence match wins.

Examples covered: salary/interest/dividend/cashback/refund, food, groceries, shopping, transport, travel, utilities, rent, EMI, ATM, entertainment, healthcare, education, fees, UPI/NEFT/IMPS transfers.

#### ML model

`MLClassifier` is a classical scikit-learn pipeline:

- Word TF-IDF: 1–2 grams
- Character TF-IDF: `char_wb` 2–5 grams
- `FeatureUnion`
- `LogisticRegression(max_iter=4000, C=6.0, class_weight="balanced")`

Training data:

- 15 categories
- ~960 synthetic descriptions
- 3 bank narration styles
- direction included as a feature prefix: `credit <description>` / `debit <description>`

Artifact: `data/models/classifier.joblib`

If the artifact is missing, it is trained automatically on first app start. To retrain manually:

```powershell
python scripts/train_classifier.py
```

Why TF-IDF + linear model:

- Non-LLM requirement.
- Fast CPU training/inference.
- Strong baseline for short merchant-style text.
- Explainable and easy to retrain.

#### Hybrid router

`ClassificationEngine.classify(description, direction)` applies this policy:

```text
1. If a rule matches with confidence >= 0.88  -> use rule
2. Else if ML probability >= 0.42             -> use ML (flag review if < 0.60)
3. Else if any rule matched                  -> use rule (flag review if < 0.75)
4. Else                                       -> Uncategorized + needs_review
```

Each transaction stores:

| Field | Meaning |
|---|---|
| `category` | assigned category |
| `source` | `rule`, `ml`, `user`, `fallback` |
| `confidence` | rule confidence or ML probability |
| `needs_review` | low confidence or validation issue |
| `review_reasons` | e.g. `balance_mismatch`, `possible_duplicate` |

User edits set `source = user`, `confidence = 1.0`, and clear review flags.

---

### 5.10 Processing pipeline

File: `app/core/pipeline.py`

`process_pdf()` is the orchestrator:

```text
detect type
  -> text extraction OR OCR
  -> if text yields nothing and images exist -> OCR fallback
  -> account metadata + inferred period
  -> validation
  -> classification for each transaction
  -> Statement object + Transaction objects
```

Returns a `ProcessedStatement` dataclass. The API layer is responsible for persistence, so the pipeline remains reusable by scripts and tests.

Failure modes raise `ExtractionError` with codes such as:

- `invalid_pdf`
- `pdf_encrypted`
- `ocr_unavailable`
- `ocr_failed`
- `no_transactions`
- `no_valid_transactions`

---

### 5.11 Persistence

File: `app/db.py`

SQLite is used for zero-setup persistence.

`statements`:

```text
id, file_hash, filename, stored_path, bank, pdf_type,
account_holder, account_number, ifsc,
period_start, period_end, opening_balance, closing_balance,
status, error, warnings, created_at
```

`transactions`:

```text
id, statement_id, row_index, txn_date, description,
debit, credit, balance, category, source, confidence,
needs_review, review_reasons, raw_text
```

Key methods:

- `insert_statement()` / `replace_transactions()`
- `find_by_hash()` for duplicate uploads
- `list_statements()` for the dashboard
- `statement_summary()` for counts/totals/classification rate
- `query_transactions()` for filters + pagination
- `update_transaction()` / `bulk_update_categories()`
- `stats()` for dashboard KPIs

JSON fields (`warnings`, `review_reasons`) are serialized/deserialized at the DB boundary.

---

### 5.12 REST API

File: `app/api/routes.py`

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | App/OCR/category status |
| GET | `/api/categories` | Category definitions + colors |
| GET | `/api/rules` | Rule-engine configuration |
| GET | `/api/stats` | Dashboard KPIs and aggregates |
| GET | `/api/statements` | List statements (`q`, `bank`, `status`, `limit`) |
| POST | `/api/statements` | Upload (`file` or `files` multipart field) |
| GET | `/api/statements/<id>` | Statement detail + all transactions |
| DELETE | `/api/statements/<id>` | Delete statement + stored file |
| POST | `/api/statements/<id>/reprocess` | Re-run extraction/classification |
| GET | `/api/statements/<id>/transactions` | Filtered/paginated transactions |
| PATCH | `/api/transactions/<id>` | Update one category |
| POST | `/api/transactions/bulk-category` | Bulk category update |
| GET | `/api/statements/<id>/export?format=csv\|xlsx` | Download export |

Upload response shape:

```json
{
  "statements": [
    {
      "id": "...",
      "filename": "statement.pdf",
      "bank": "HDFC Bank",
      "pdf_type": "text",
      "status": "processed",
      "account": { "holder": "...", "account_number": "...", "ifsc": "..." },
      "period": { "start": "2025-04-01", "end": "2025-06-30" },
      "opening_balance": 150000.0,
      "closing_balance": 152345.67,
      "summary": {
        "transaction_count": 49,
        "total_debit": 123456.78,
        "total_credit": 150000.0,
        "needs_review": 2,
        "classification_rate": 0.9592,
        "category_counts": { "Food & Dining": 12 },
        "source_counts": { "rule": 40, "ml": 8, "fallback": 1 }
      },
      "transactions": []
    }
  ],
  "errors": []
}
```

Behavior notes:

- Duplicate PDFs return the existing statement with `"duplicate": true`.
- Extraction failures are stored as `status: failed` and returned in `errors[]`.
- Invalid file types and encrypted PDFs produce `422` with an error code.

---

### 5.13 Export

File: `app/core/exporter.py`

- `build_csv()` creates UTF-8 CSV with a BOM for Excel compatibility.
- `build_xlsx()` creates a styled workbook:
  - `Transactions` sheet with filters, frozen header, number formats, review highlighting.
  - `Summary` sheet with account metadata, totals, and category breakdown.
- Currency values are written as numbers in XLSX and formatted strings in CSV.

---

### 5.14 Frontend integration

Files: `app/templates/*.html`, `app/static/js/app.js`, `app/static/css/app.css`

The UI started as Stitch-generated static pages (“Sober Precision Fintech” design) and was wired to the API.

Integration approach:

- Pages are Jinja2 templates served by Flask.
- `body[data-page]` tells `app.js` which page controller to run:
  - `initDashboard()`
  - `initUpload()`
  - `initReview()`
  - `initCategories()`
- Almost all dynamic content is rendered client-side from API JSON.
- Shared utilities in `app.js`:
  - `api()` wrapper
  - INR/date formatters
  - toast notifications
  - dropdown menus
  - HTML escaping
- `wireChrome()` binds sidebar routes, active nav state, upload buttons, and the global search.
- Transactions page has a statement switcher; changing it preserves the `/transactions` context.
- Upload page shows per-file queue status, a 6-step pipeline animation, and a live terminal log while the synchronous API call runs.
- Review page supports:
  - search, type/source/category filters, tabs,
  - client-side pagination,
  - inline category editing (PATCH),
  - bulk categorization,
  - flagged-transaction stepping,
  - CSV/XLSX export and reprocessing.

Why this approach: static design fidelity was preserved while adding real data with minimal framework overhead.

---

## 6. Classification examples

| Description | Direction | Result | Why |
|---|---|---|---|
| `NEFT CR-INFOSYS-SALARY APR 2025-12345678` | credit | Salary & Income | salary rule (0.98) |
| `SALARY TRANSFER` | debit | not Salary & Income | salary rule is credit-only |
| `UPI/DR/12345678/SWIGGY/ybl` | debit | Food & Dining | merchant rule (0.96) |
| `POS/COLLEGE FEES/BENGALURU/24220760` | debit | Education | education rule beats generic “fees” |
| `ATM/CASH WDL/PUNE/12345678` | debit | Cash & ATM | ATM rule (0.97) |
| `REFUND-PIZZA HUT-07956393` | credit | Salary & Income | refund credit rule (0.97) |
| `XYZQ 0000 UNKNOWN ENTRY` | debit | Uncategorized | no rule, low ML probability → review |

---

## 7. Tests and evaluation

### Unit/integration tests — `pytest`

```powershell
python -m pytest -q
```

31 tests currently cover:

- amount/date normalization,
- rule matching and direction sensitivity,
- ML prediction sanity,
- text PDF extraction (field-by-field vs ground truth),
- image OCR extraction,
- upload/list/detail/PATCH/export/stats API flows,
- duplicate uploads,
- encrypted PDFs,
- invalid file types.

### Synthetic benchmark — `scripts/evaluate.py`

```powershell
python scripts/evaluate.py --samples data/samples
```

It compares the pipeline against `labels.json`:

- bank/account/IFSC accuracy,
- row recall,
- field accuracy (date/debit/credit/balance),
- category accuracy,
- text and OCR samples.

Latest run on the 12-sample synthetic benchmark: **100% field accuracy, 100% category accuracy, 100% OCR row recall.** This is a synthetic benchmark, not a claim of real-world accuracy.

---

## 8. Edge cases handled

- Text PDFs with multiple pages.
- Scanned/image-only PDFs via OCR.
- `mixed` PDFs (text first, OCR fallback).
- Password-protected PDFs → clean `422`.
- Duplicate uploads → existing statement returned.
- Amounts with Indian grouping, `Dr/Cr`, parentheses, dashes.
- Multiple date formats.
- Missing debit/credit direction → inferred from balance delta.
- Balance-continuity mismatch → review flag.
- Duplicate rows → review flag.
- Out-of-order dates → warning.
- Unknown bank → `Unknown Bank` fallback.
- Unknown merchant → `Uncategorized` + review.
- User overrides persisted with source `user`.
- Invalid filters/pagination → `400`.
- Upload size limit → `413`.

---

## 9. Known limitations (be honest in the viva)

- **Synthetic distribution bias.** The classifier is trained on generated descriptions. Real statements will contain unseen merchants, so rule/ML accuracy will be lower until retrained on real labeled data.
- **Three bank layouts only.** Header-driven parsing generalizes somewhat, but production needs per-bank templates and more layout tests.
- **OCR is line-based.** Complex multi-column scanned tables, merged cells, stamps, or rotated pages may need layout-aware OCR (PaddleOCR/OpenCV table detection).
- **English/India-centric.** Regex vocabulary is English and INR-focused.
- **Synchronous processing.** Upload waits for extraction/classification; production would use a job queue and streaming status.
- **No authentication or multi-tenancy.**
- **No PDF preview/bounding boxes** in the review page yet.
- **Rules/categories are read-only in the UI** (config files are the source of truth).
- **Tailwind is loaded from CDN**, so styling requires network access on first load.
- **Statement switcher covers processed statements**, not failed ones.

---

## 10. How to extend

### Add a new bank layout

1. Add synthetic layout metadata in `synthetic/generator.py` (`PROFILES`).
2. Add the bank keyword to `BANK_KEYWORDS` in `extractors/common.py`.
3. Ensure the header names map to date/description/debit/credit/balance.
4. Generate samples and run `pytest` + `scripts/evaluate.py`.

### Add a category

1. Add it to `data/categories.json` with a color.
2. Add training descriptions/merchants in `classifiers/merchants.py`.
3. Add rules in `data/rules.json`.
4. Retrain: `python scripts/train_classifier.py`.
5. `POST /api/statements/<id>/reprocess` or re-upload a statement.

### Add/change a rule

Edit `data/rules.json` and restart the app. The rule engine loads at startup. Patterns are Python regexes.

### Retrain the ML model

```powershell
python scripts/train_classifier.py
```

The artifact is replaced at `data/models/classifier.joblib`.

### Change UI pages

- Templates live in `app/templates`.
- Page logic is selected by `body[data-page]` in `app/static/js/app.js`.
- API helpers and formatters are at the top of `app.js`.
- Styling uses the Stitch Tailwind tokens included in each template head.

---

## 11. Suggested demo / viva walkthrough

1. **Dashboard** — show 4 statements, 194 transactions, classification rate, review flags, category distribution.
2. **Upload** — select a PDF, show queue/stepper/log, explain text vs OCR routing.
3. **Review** — open the statement, search/filter, change a category, bulk categorize, export CSV/XLSX.
4. **Transactions tab** — show the statement switcher and that it stays in the Transactions workspace.
5. **Categories page** — show the 16 categories and 22 deterministic rules loaded from JSON.
6. **Code tour** — open `pipeline.py` → `pdf_detector.py` → `text_pdf.py` → `validators.py` → `classifiers/pipeline.py` → `rules.json` → `ml.py` → `db.py` → `api/routes.py`.
7. **Explain the non-LLM choice** — “rules for precision + TF-IDF ML for unseen merchants; confidence routing protects low-quality matches.”
8. **Show verification** — `pytest` output and `scripts/evaluate.py` results.

One-sentence summary you can use:

> “The system is a Flask + SQLite pipeline that detects PDF type, extracts and reconciles transactions, classifies them with a hybrid regex + TF-IDF model (no LLMs), and exposes a review/export workflow through a Stitch-designed UI.”

---

## 12. Troubleshooting

| Problem | Fix |
|---|---|
| `/api/health` shows OCR unavailable | Install Tesseract or set `TESSERACT_CMD` to `tesseract.exe` |
| Scanned PDF returns `no_transactions` | Check OCR quality; try a cleaner 300 DPI scan |
| Model missing | It auto-trains, or run `python scripts/train_classifier.py` |
| Want a clean demo DB | `python scripts/seed_demo.py --reset` |
| Port 5000 busy | `$env:PORT='5001'; python run.py` |
| Upload > 20 MB | Raise `MAX_UPLOAD_MB` env var |
| Styling broken | Tailwind CDN must be reachable |
| Browser shows old JS | Hard refresh (`Ctrl+F5`) |
| Tests fail on OCR | Expected if Tesseract is not installed; the OCR test is skipped |

---

## 13. Function map

| Area | Function | Location |
|---|---|---|
| App factory | `create_app` | `app/__init__.py:15` |
| PDF type | `detect_pdf_type` | `app/core/pdf_detector.py:10` |
| Text extraction | `extract_text_pdf` | `app/core/extractors/text_pdf.py:117` |
| Table parsing | `parse_table` | `app/core/extractors/text_pdf.py:71` |
| OCR extraction | `extract_image_pdf` | `app/core/extractors/ocr_pdf.py:32` |
| Line parsing | `parse_transaction_line` | `app/core/extractors/line_parser.py:24` |
| Amount parsing | `parse_amount` | `app/core/extractors/normalize.py:39` |
| Date parsing | `parse_date` | `app/core/extractors/normalize.py:71` |
| Bank detection | `detect_bank` | `app/core/extractors/common.py:53` |
| Account metadata | `extract_account_info` | `app/core/extractors/common.py:96` |
| Validation | `validate_transactions` | `app/core/validators.py:20` |
| Orchestration | `process_pdf` | `app/core/pipeline.py:38` |
| Rule engine | `RuleEngine.classify` | `app/core/classifiers/rules.py:48` |
| ML training | `MLClassifier.train_default` | `app/core/classifiers/ml.py:26` |
| ML inference | `MLClassifier.predict` | `app/core/classifiers/ml.py:111` |
| Hybrid router | `ClassificationEngine.classify` | `app/core/classifiers/pipeline.py:29` |
| Synthetic statements | `generate_statement` | `synthetic/generator.py:404` |
| Image PDF conversion | `convert_to_image_pdf` | `synthetic/generator.py:472` |
| CSV export | `build_csv` | `app/core/exporter.py:33` |
| XLSX export | `build_xlsx` | `app/core/exporter.py:71` |
| DB access | `Database` | `app/db.py:102` |
| Upload API | `upload_statements` | `app/api/routes.py:146` |
| Review API | `get_statement` | `app/api/routes.py:247` |
| Category edit | `update_transaction` | `app/api/routes.py:365` |
| Export API | `export_statement` | `app/api/routes.py:414` |
| UI controller | `initDashboard/initUpload/initReview/initCategories` | `app/static/js/app.js` |
| Evaluation | `scripts/evaluate.py` | `scripts/evaluate.py` |
| Demo seeding | `scripts/seed_demo.py` | `scripts/seed_demo.py` |
