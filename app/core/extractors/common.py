from __future__ import annotations

import re

from .normalize import normalize_ws, parse_amount, parse_date

BANK_KEYWORDS = (
    ("HDFC Bank", ("HDFC BANK", "HDFC000")),
    ("ICICI Bank", ("ICICI BANK", "ICIC0")),
    ("State Bank of India", ("STATE BANK OF INDIA", "SBIN0")),
    ("Axis Bank", ("AXIS BANK", "UTIB0")),
    ("Kotak Mahindra Bank", ("KOTAK MAHINDRA", "KKBK0")),
    ("IndusInd Bank", ("INDUSIND",)),
    ("Yes Bank", ("YES BANK",)),
    ("Punjab National Bank", ("PUNJAB NATIONAL BANK", "PNB")),
    ("Bank of Baroda", ("BANK OF BARODA", "BARB0")),
)

_DATE_TOKEN = r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{1,2}[\s\-][A-Za-z]{3,9}[\s,\-]+\d{2,4})"

_IFSC_RE = re.compile(r"\b([A-Z]{4}0[A-Z0-9]{6})\b")
_HOLDER_PATTERNS = (
    re.compile(r"account\s*holder(?:\s*name)?\s*[:\-]\s*(.+)", re.IGNORECASE),
    re.compile(r"customer\s*name\s*[:\-]\s*(.+)", re.IGNORECASE),
    re.compile(r"^\s*(?:name|a/c\s*holder)\s*[:\-]\s*(.+)", re.IGNORECASE),
)
_ACCOUNT_RE = re.compile(
    r"(?:account|a/c|acct)\s*(?:no|number|#)?\.?\s*[:\-]?\s*([Xx*\d][Xx*\d\s]{5,24})",
    re.IGNORECASE,
)
_PERIOD_PATTERNS = (
    re.compile(
        r"(?:statement\s+period|statement\s+for\s+the\s+period|period\s+from|period)\s*[:\-]?\s*"
        + _DATE_TOKEN
        + r"\s*(?:to|till|through)\s*"
        + _DATE_TOKEN,
        re.IGNORECASE,
    ),
    re.compile(r"\bfrom\s+" + _DATE_TOKEN + r"\s+to\s+" + _DATE_TOKEN, re.IGNORECASE),
)
_OPENING_RE = re.compile(
    r"(?:opening\s+balance|balance\s+b/?f|brought\s+forward)[ \t]*[:\-]?[ \t]*(?:rs\.?|inr|₹)?[ \t]*"
    r"([0-9][0-9,]*(?:\.[0-9]{1,2})?)",
    re.IGNORECASE,
)
_CLOSING_RE = re.compile(
    r"(?:closing\s+balance|balance\s+c/?f|carried\s+forward)[ \t]*[:\-]?[ \t]*(?:rs\.?|inr|₹)?[ \t]*"
    r"([0-9][0-9,]*(?:\.[0-9]{1,2})?)",
    re.IGNORECASE,
)


def detect_bank(text: str) -> str:
    lines = text.splitlines()
    header = normalize_ws("\n".join(lines[:15])).upper()
    for display, keywords in BANK_KEYWORDS:
        for keyword in keywords:
            if keyword in header:
                return display

    haystack = normalize_ws(text).upper()
    for display, keywords in BANK_KEYWORDS:
        for keyword in keywords:
            if keyword in haystack:
                return display
    return "Unknown Bank"


def _clean_holder(value: str) -> str | None:
    holder = normalize_ws(value).strip(" .:-|")
    holder = re.split(r"\s{2,}|\s+(?:account|a/c|ifsc|branch)\b", holder, maxsplit=1, flags=re.IGNORECASE)[0]
    if not (2 <= len(holder) <= 60):
        return None
    if sum(ch.isdigit() for ch in holder) > len(holder) / 2:
        return None
    lowered = holder.lower()
    if any(word in lowered for word in ("statement", "bank", "account number", "ifsc")):
        return None
    return holder


def _extract_period(text: str) -> tuple[str | None, str | None]:
    lines = [line for line in text.splitlines() if line.strip()]
    for pattern in _PERIOD_PATTERNS:
        for line in lines:
            match = pattern.search(line)
            if not match:
                continue
            start = parse_date(match.group(1))
            end = parse_date(match.group(2))
            if start and end:
                return start, end
    return None, None


def extract_account_info(text: str) -> dict:
    info = {
        "holder": None,
        "account_number": None,
        "ifsc": None,
        "period_start": None,
        "period_end": None,
        "opening_balance": None,
        "closing_balance": None,
    }

    lines = text.splitlines()
    for line in lines[:80]:
        for pattern in _HOLDER_PATTERNS:
            match = pattern.search(line)
            if match:
                holder = _clean_holder(match.group(1))
                if holder:
                    info["holder"] = holder
                    break
        if info["holder"]:
            break

    for match in _ACCOUNT_RE.finditer(text):
        candidate = re.sub(r"[^0-9Xx*]", "", match.group(1))
        if len(candidate) >= 6 and any(ch.isdigit() for ch in candidate):
            info["account_number"] = candidate
            break

    ifsc = _IFSC_RE.search(text.upper())
    if ifsc:
        info["ifsc"] = ifsc.group(1)

    info["period_start"], info["period_end"] = _extract_period(text)
    info["opening_balance"] = _extract_balance(text, _OPENING_RE)
    info["closing_balance"] = _extract_balance(text, _CLOSING_RE)

    return info


def _extract_balance(text: str, pattern: re.Pattern) -> float | None:
    for line in text.splitlines():
        match = pattern.search(line)
        if match:
            value = parse_amount(match.group(1))
            if value is not None:
                return value
    return None


def infer_period(account: dict, transactions) -> dict:
    dates = sorted(tx.date for tx in transactions if getattr(tx, "date", None))
    if not dates:
        return account
    if not account.get("period_start"):
        account["period_start"] = dates[0]
    if not account.get("period_end"):
        account["period_end"] = dates[-1]
    return account
