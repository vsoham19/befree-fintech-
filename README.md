# StatementIQ — Bank Statement Processing & Classification

A Flask prototype that ingests bank statement PDFs (text-based or scanned), extracts transactions, validates them, classifies them **without LLMs**, and exports the reviewed ledger to CSV/XLSX.

## Highlights

- **PDF type detection** (text vs scanned) with automatic OCR fallback
- **Transaction extraction** for HDFC, ICICI, and SBI-style layouts
- **Balance reconciliation** (opening + credits − debits = closing)
- **Non-LLM classification**: 22 deterministic rules + TF-IDF/Logistic Regression
- **Review UI**: filters, inline category edits, bulk categorize, reprocess
- **Exports**: CSV and styled Excel workbooks
- **Synthetic data generator** for repeatable demos and evaluation

## Tech stack

Python 3.13 · Flask · SQLite · pdfplumber · PyMuPDF · Tesseract OCR · scikit-learn · reportlab · Jinja2 · Tailwind CSS

## Quick start

```powershell
pip install -r requirements.txt
python -m synthetic --count 12 --out data/samples --image-ratio 0.35 --clean
python scripts/train_classifier.py          # optional; auto-trains on first run
python scripts/seed_demo.py --reset         # optional demo data
python run.py                               # http://127.0.0.1:5000
```

Tesseract must be installed for scanned PDFs. On Windows the app auto-detects
`C:\Program Files\Tesseract-OCR\tesseract.exe`; override with `TESSERACT_CMD`.

## Useful commands

```powershell
python -m pytest -q                              # test suite
python scripts/evaluate.py --samples data/samples # extraction/classification metrics
python -m synthetic --help                        # generator options
python scripts/seed_demo.py --reset                # reset demo database
```

## Project layout

```text
app/
  __init__.py          Flask app factory + page routes
  api/routes.py        REST API
  core/                extraction, validation, classification, export
  db.py                SQLite persistence
  templates/           dashboard, upload, review, categories
  static/              app.js, app.css, favicon
data/
  categories.json      16 categories
  rules.json           22 heuristic rules
  samples/             generated PDFs + labels
synthetic/             statement generator
scripts/               training, evaluation, demo seeding
tests/                 pytest suite
CODE_GUIDE.md          detailed component-by-component walkthrough
```

## API (summary)

| Method | Endpoint |
|---|---|
| POST | `/api/statements` (multipart: `file` or `files`) |
| GET | `/api/statements` · `/api/statements/<id>` |
| GET | `/api/statements/<id>/transactions` |
| PATCH | `/api/transactions/<id>` (`{ "category": "..." }`) |
| POST | `/api/transactions/bulk-category` |
| POST | `/api/statements/<id>/reprocess` |
| GET | `/api/statements/<id>/export?format=csv\|xlsx` |
| GET | `/api/stats` · `/api/categories` · `/api/rules` · `/api/health` |

## Notes

- Classification is fully non-LLM: deterministic regex rules run first, then a classical TF-IDF + Logistic Regression model handles unseen merchants.
- The included dataset is synthetic; accuracy on real statements depends on retraining and additional bank layouts.
- See [CODE_GUIDE.md](CODE_GUIDE.md) for architecture, design decisions, and a viva walkthrough.
