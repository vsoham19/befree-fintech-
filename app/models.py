from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class Transaction:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    statement_id: str = ""
    row_index: int = 0
    date: Optional[str] = None
    description: str = ""
    debit: Optional[float] = None
    credit: Optional[float] = None
    balance: Optional[float] = None
    category: str = "Uncategorized"
    source: str = "fallback"
    confidence: float = 0.0
    needs_review: bool = False
    review_reasons: list[str] = field(default_factory=list)
    raw_text: str = ""

    @property
    def direction(self) -> Optional[str]:
        if self.debit:
            return "debit"
        if self.credit:
            return "credit"
        return None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "statement_id": self.statement_id,
            "row_index": self.row_index,
            "date": self.date,
            "description": self.description,
            "debit": self.debit,
            "credit": self.credit,
            "balance": self.balance,
            "direction": self.direction,
            "category": self.category,
            "source": self.source,
            "confidence": round(self.confidence, 4),
            "needs_review": self.needs_review,
            "review_reasons": list(self.review_reasons),
            "raw_text": self.raw_text,
        }

    def to_record(self) -> dict:
        return {
            "id": self.id,
            "statement_id": self.statement_id,
            "row_index": self.row_index,
            "txn_date": self.date,
            "description": self.description,
            "debit": self.debit,
            "credit": self.credit,
            "balance": self.balance,
            "category": self.category,
            "source": self.source,
            "confidence": self.confidence,
            "needs_review": 1 if self.needs_review else 0,
            "review_reasons": list(self.review_reasons),
            "raw_text": self.raw_text,
        }


@dataclass
class Statement:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    filename: str = ""
    stored_path: str = ""
    file_hash: Optional[str] = None
    bank: str = "Unknown Bank"
    pdf_type: str = "unknown"
    account_holder: Optional[str] = None
    account_number: Optional[str] = None
    ifsc: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None
    status: str = "processed"
    error: Optional[str] = None
    warnings: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)

    def to_record(self) -> dict:
        return {
            "id": self.id,
            "file_hash": self.file_hash,
            "filename": self.filename,
            "stored_path": self.stored_path,
            "bank": self.bank,
            "pdf_type": self.pdf_type,
            "account_holder": self.account_holder,
            "account_number": self.account_number,
            "ifsc": self.ifsc,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "opening_balance": self.opening_balance,
            "closing_balance": self.closing_balance,
            "status": self.status,
            "error": self.error,
            "warnings": list(self.warnings),
            "created_at": self.created_at,
        }
