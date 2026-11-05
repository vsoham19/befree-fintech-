from __future__ import annotations

import re
from pathlib import Path

import fitz
import pytesseract
from PIL import Image, ImageOps

from app.errors import ExtractionError

from .base import ExtractionResult
from .common import detect_bank, extract_account_info, infer_period
from .line_parser import parse_transaction_lines

_NUMERIC_OCR_FIXES = (
    (re.compile(r"(?<=\d)[Oo](?=\d)"), "0"),
    (re.compile(r"(?<=\d)[Il](?=\d)"), "1"),
    (re.compile(r"(?<=\d)[Ss](?=\d)"), "5"),
)


def _fix_ocr_text(text: str) -> str:
    lines = []
    for line in text.splitlines():
        for pattern, replacement in _NUMERIC_OCR_FIXES:
            line = pattern.sub(replacement, line)
        lines.append(line)
    return "\n".join(lines)


def extract_image_pdf(
    path: Path,
    dpi: int = 300,
    tesseract_cmd: str | None = None,
) -> ExtractionResult:
    if not tesseract_cmd or not Path(tesseract_cmd).exists():
        raise ExtractionError(
            "OCR engine not found. Install Tesseract OCR or set the TESSERACT_CMD environment variable.",
            code="ocr_unavailable",
        )

    pytesseract.pytesseract.tesseract_cmd = str(tesseract_cmd)

    try:
        document = fitz.open(str(path))
    except Exception as exc:
        raise ExtractionError(f"Could not open PDF: {exc}", code="invalid_pdf") from exc

    try:
        if document.needs_pass:
            raise ExtractionError("PDF is password protected.", code="pdf_encrypted")
        page_texts: list[str] = []
        page_count = document.page_count
        for page in document:
            pixmap = page.get_pixmap(dpi=dpi, colorspace=fitz.csGRAY)
            image = Image.frombytes("L", (pixmap.width, pixmap.height), pixmap.samples)
            image = ImageOps.autocontrast(image)
            page_texts.append(
                pytesseract.image_to_string(
                    image,
                    config="--oem 3 --psm 6 -c preserve_interword_spaces=1",
                )
            )
    except ExtractionError:
        raise
    except Exception as exc:
        raise ExtractionError(f"OCR failed: {exc}", code="ocr_failed") from exc
    finally:
        document.close()

    full_text = _fix_ocr_text("\n".join(page_texts))
    bank = detect_bank(full_text)
    account = extract_account_info(full_text)
    transactions = parse_transaction_lines(full_text)
    account = infer_period(account, transactions)

    warnings = []
    if not transactions:
        warnings.append("OCR completed but no transaction rows could be parsed.")
    if not account.get("opening_balance"):
        warnings.append("Opening balance could not be read by OCR.")

    return ExtractionResult(
        bank=bank,
        pdf_type="image",
        account=account,
        transactions=transactions,
        warnings=warnings,
        page_count=page_count,
    )
