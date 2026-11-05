from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

from .base import ExtractionResult, RawTransaction
from .common import detect_bank, extract_account_info, infer_period
from .line_parser import parse_transaction_lines
from .normalize import normalize_ws, parse_amount, parse_date

_SKIP_ROW_RE = re.compile(
    r"\b(opening\s+balance|closing\s+balance|balance\s+b/?f|balance\s+c/?f|total)\b",
    re.IGNORECASE,
)


def _classify_header(cell) -> str | None:
    header = re.sub(r"[^a-z0-9]+", " ", str(cell or "").lower()).strip()
    if not header:
        return None
    if "balance" in header:
        return "balance"
    if "withdraw" in header or re.search(r"\b(debit|dr)\b", header):
        return "debit"
    if "deposit" in header or re.search(r"\b(credit|cr)\b", header):
        return "credit"
    if "date" in header:
        return "date"
    if any(key in header for key in ("narration", "particular", "description", "remark", "detail")):
        return "desc"
    return None


def _resolve_columns(row) -> dict | None:
    columns: dict[str, int] = {}
    for index, cell in enumerate(row):
        kind = _classify_header(cell)
        if kind and kind not in columns:
            columns[kind] = index
    if "date" not in columns or "desc" not in columns:
        return None
    if not any(kind in columns for kind in ("debit", "credit", "balance")):
        return None
    return columns


def _find_header(table) -> tuple[int, dict] | tuple[None, None]:
    for index, row in enumerate(table[:10]):
        if not row:
            continue
        columns = _resolve_columns(row)
        if columns:
            return index, columns
    return None, None


def _cell(row, index) -> str:
    if index is None or index >= len(row):
        return ""
    return normalize_ws(row[index])


def _positive(value: float | None) -> float | None:
    if value is None:
        return None
    return abs(value) if value != 0 else None


def parse_table(table) -> list[RawTransaction]:
    header_index, columns = _find_header(table)
    if header_index is None or columns is None:
        return []

    transactions: list[RawTransaction] = []
    for row in table[header_index + 1 :]:
        if not row:
            continue
        cells = [normalize_ws(cell) for cell in row]
        joined = " ".join(cells)
        if not joined.strip() or _SKIP_ROW_RE.search(joined):
            continue

        date = parse_date(_cell(row, columns.get("date")))
        if not date:
            for cell in cells:
                date = parse_date(cell)
                if date:
                    break
        if not date:
            continue

        description = _cell(row, columns.get("desc"))
        if not description or _classify_header(description) == "desc":
            continue

        debit = _positive(parse_amount(_cell(row, columns.get("debit"))))
        credit = _positive(parse_amount(_cell(row, columns.get("credit"))))
        balance = parse_amount(_cell(row, columns.get("balance")))
        if debit is None and credit is None and balance is None:
            continue

        transactions.append(
            RawTransaction(
                date=date,
                description=description,
                debit=debit,
                credit=credit,
                balance=balance,
                raw_text=" | ".join(cell for cell in cells if cell),
            )
        )
    return transactions


def extract_text_pdf(path: Path) -> ExtractionResult:
    page_texts: list[str] = []
    transactions: list[RawTransaction] = []

    with pdfplumber.open(str(path)) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=2, y_tolerance=4) or ""
            page_texts.append(text)
            try:
                tables = page.extract_tables()
            except Exception:
                tables = []
            for table in tables:
                transactions.extend(parse_table(table))

    full_text = "\n".join(page_texts)
    bank = detect_bank(full_text)
    account = extract_account_info(full_text)

    if not transactions:
        transactions = parse_transaction_lines(full_text)

    account = infer_period(account, transactions)

    warnings = []
    if not transactions:
        warnings.append("No transaction table could be parsed from the text layer.")
    if not account.get("opening_balance"):
        warnings.append("Opening balance could not be extracted.")

    return ExtractionResult(
        bank=bank,
        pdf_type="text",
        account=account,
        transactions=transactions,
        warnings=warnings,
        page_count=page_count,
    )
