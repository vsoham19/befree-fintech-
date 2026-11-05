from __future__ import annotations

import re
from datetime import datetime

_AMOUNT_CLEAN = re.compile(r"[^\d.\-]")
_DIGIT_SPACE = re.compile(r"(?<=\d)\s+(?=[\d,])")
_PAREN_NEGATIVE = re.compile(r"^\((.+)\)$")
_CR_DR_SUFFIX = re.compile(r"(?i)\s*(?:cr|dr|credit|debit)\.?\s*$")

_DATE_FORMATS = (
    "%d/%m/%Y",
    "%d/%m/%y",
    "%d-%m-%Y",
    "%d-%m-%y",
    "%d.%m.%Y",
    "%d.%m.%y",
    "%d-%b-%Y",
    "%d-%b-%y",
    "%d %b %Y",
    "%d %b %y",
    "%d-%B-%Y",
    "%d %B %Y",
    "%b %d, %Y",
    "%B %d, %Y",
    "%d %b, %Y",
    "%d-%b, %Y",
    "%Y/%m/%d",
    "%Y-%m-%d",
)


def normalize_ws(value) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def parse_amount(value) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    text = normalize_ws(value)
    if not text or text.lower() in {"-", "--", "na", "n/a", "nil", "none"}:
        return None

    text = text.replace("₹", " ").replace("Rs.", " ").replace("Rs ", " ").replace("INR", " ")
    negative = False
    paren = _PAREN_NEGATIVE.match(text.strip())
    if paren:
        negative = True
        text = paren.group(1)
    text = _CR_DR_SUFFIX.sub("", text).strip()
    text = _DIGIT_SPACE.sub("", text).replace(",", "")
    cleaned = _AMOUNT_CLEAN.sub("", text)
    if cleaned in {"", "-", ".", "-."}:
        return None
    if cleaned.count(".") > 1:
        head, _, tail = cleaned.rpartition(".")
        cleaned = head.replace(".", "") + "." + tail
    try:
        number = float(cleaned)
    except ValueError:
        return None
    if negative:
        number = -number
    return round(number, 2)


def parse_date(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    text = normalize_ws(value)
    if not text:
        return None

    iso = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", text)
    if iso:
        try:
            return datetime.strptime(text, "%Y-%m-%d").date().isoformat()
        except ValueError:
            return None

    text = re.sub(r"(?i)\bsept\b", "Sep", text)
    text = re.sub(r"(\d{1,2})\s*[/\-.]\s*(\d{1,2})\s*[/\-.]\s*(\d{2,4})", r"\1/\2/\3", text)
    text = re.sub(r"(\d{1,2})\s+([A-Za-z]{3,9})[\s,]*-?\s*(\d{2,4})", r"\1-\2-\3", text)

    candidates = [text]
    if " " in text:
        candidates.append(text.split(" ")[0])
    for candidate in candidates:
        candidate = candidate.strip(" ,.|")
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(candidate, fmt).date().isoformat()
            except ValueError:
                continue
    return None
