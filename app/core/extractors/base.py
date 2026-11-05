from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RawTransaction:
    date: Optional[str]
    description: str
    debit: Optional[float] = None
    credit: Optional[float] = None
    balance: Optional[float] = None
    amount: Optional[float] = None
    raw_text: str = ""


@dataclass
class ExtractionResult:
    bank: str
    pdf_type: str
    account: dict
    transactions: list[RawTransaction] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    page_count: int = 0
