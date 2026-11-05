from __future__ import annotations

import re

from .base import RawTransaction
from .normalize import normalize_ws, parse_amount, parse_date

_DATE_START_RE = re.compile(
    r"^\s*(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{1,2}[\s\-][A-Za-z]{3,9}[\s,\-]+\d{2,4})\s+(.+)$"
)
_AMOUNT_RE = re.compile(r"(?<![\w.,])(\d[\d,]*\.\d{1,2})(?![\w,])")
_SKIP_DESC_RE = re.compile(
    r"\b(opening balance|closing balance|balance b/?f|balance c/?f|total|page\s+\d+)\b",
    re.IGNORECASE,
)


def _tidy_line(line: str) -> str:
    text = normalize_ws(line).lstrip("|").strip()
    text = re.sub(r"(?<=\d)\s*([/\-])\s*(?=\d)", r"\1", text)
    return text


def parse_transaction_line(line: str) -> RawTransaction | None:
    text = _tidy_line(line)
    if not text:
        return None
    match = _DATE_START_RE.match(text)
    if not match:
        return None

    date = parse_date(match.group(1))
    if not date:
        return None

    rest = match.group(2)
    amounts = list(_AMOUNT_RE.finditer(rest))
    if not amounts:
        return None

    description = normalize_ws(rest[: amounts[0].start()]).strip(" -|:/")
    if not description or _SKIP_DESC_RE.search(description):
        return None

    parsed = [parse_amount(item.group(1)) for item in amounts]
    parsed = [value for value in parsed if value is not None]
    if not parsed:
        return None

    balance = parsed[-1]
    amount = parsed[-2] if len(parsed) >= 2 else None

    return RawTransaction(
        date=date,
        description=description,
        amount=amount,
        balance=balance,
        raw_text=text,
    )


def parse_transaction_lines(text: str) -> list[RawTransaction]:
    transactions = []
    for line in text.splitlines():
        transaction = parse_transaction_line(line)
        if transaction:
            transactions.append(transaction)
    return transactions
