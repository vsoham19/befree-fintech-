from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.errors import ExtractionError
from app.models import Statement, Transaction

from .classifiers.pipeline import ClassificationEngine
from .extractors import ExtractionResult, extract_image_pdf, extract_text_pdf
from .extractors.common import infer_period
from .pdf_detector import detect_pdf_type
from .validators import validate_transactions


@dataclass
class ProcessedStatement:
    statement: Statement
    transactions: list[Transaction] = field(default_factory=list)
    extraction: dict = field(default_factory=dict)


def _run_extraction(
    path: Path,
    pdf_type: str,
    has_images: bool,
    ocr_dpi: int,
    tesseract_cmd: str | None,
) -> ExtractionResult:
    if pdf_type in ("text", "mixed"):
        result = extract_text_pdf(path)
        if not result.transactions and has_images:
            result = extract_image_pdf(path, dpi=ocr_dpi, tesseract_cmd=tesseract_cmd)
        return result
    return extract_image_pdf(path, dpi=ocr_dpi, tesseract_cmd=tesseract_cmd)


def process_pdf(
    path: Path | str,
    engine: ClassificationEngine,
    *,
    ocr_dpi: int = 300,
    tesseract_cmd: str | None = None,
    filename: str | None = None,
    stored_path: str | None = None,
    file_hash: str | None = None,
    statement_id: str | None = None,
) -> ProcessedStatement:
    path = Path(path)
    info = detect_pdf_type(path)
    extraction = _run_extraction(
        path,
        info["pdf_type"],
        bool(info["image_pages"]),
        ocr_dpi,
        tesseract_cmd,
    )

    if not extraction.transactions:
        raise ExtractionError(
            "No transactions could be extracted from this statement.",
            code="no_transactions",
            details={
                "pdf_type": info["pdf_type"],
                "pages": info["pages"],
                "warnings": extraction.warnings,
            },
        )

    transactions, validation_warnings = validate_transactions(
        extraction.transactions, extraction.account
    )
    if not transactions:
        raise ExtractionError(
            "Transactions were detected but none had usable dates and amounts.",
            code="no_valid_transactions",
            details={"warnings": extraction.warnings + validation_warnings},
        )

    for transaction in transactions:
        result = engine.classify(transaction.description, transaction.direction)
        transaction.category = result.category
        transaction.source = result.source
        transaction.confidence = result.confidence
        if result.needs_review:
            transaction.needs_review = True
            transaction.review_reasons.append("low_confidence_classification")

    account = infer_period(extraction.account, extraction.transactions)
    warnings = extraction.warnings + validation_warnings

    statement = Statement(
        id=statement_id or Statement().id,
        filename=filename or path.name,
        stored_path=stored_path or str(path),
        file_hash=file_hash,
        bank=extraction.bank,
        pdf_type=info["pdf_type"],
        account_holder=account.get("holder"),
        account_number=account.get("account_number"),
        ifsc=account.get("ifsc"),
        period_start=account.get("period_start"),
        period_end=account.get("period_end"),
        opening_balance=account.get("opening_balance"),
        closing_balance=account.get("closing_balance"),
        status="processed",
        error=None,
        warnings=warnings,
    )

    for transaction in transactions:
        transaction.statement_id = statement.id

    return ProcessedStatement(
        statement=statement,
        transactions=transactions,
        extraction={
            "pages": info["pages"],
            "image_pages": info["image_pages"],
            "text_chars": info["text_chars"],
            "extracted_rows": len(extraction.transactions),
        },
    )
