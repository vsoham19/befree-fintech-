from __future__ import annotations

from pathlib import Path

import fitz

from app.errors import ExtractionError


def detect_pdf_type(path: Path) -> dict:
    try:
        document = fitz.open(str(path))
    except Exception as exc:
        raise ExtractionError(f"Could not open PDF: {exc}", code="invalid_pdf") from exc

    try:
        if document.needs_pass:
            raise ExtractionError("PDF is password protected.", code="pdf_encrypted")
        page_count = document.page_count
        if page_count == 0:
            raise ExtractionError("PDF contains no pages.", code="empty_pdf")

        char_counts: list[int] = []
        image_pages = 0
        for page in document:
            text = page.get_text("text").strip()
            char_counts.append(len(text))
            if page.get_images(full=True) and len(text) < 80:
                image_pages += 1
    finally:
        document.close()

    total_chars = sum(char_counts)
    if total_chars >= 200 and sum(1 for count in char_counts if count >= 40) >= max(1, page_count // 2):
        pdf_type = "text"
    elif total_chars < 40 and image_pages > 0:
        pdf_type = "image"
    elif any(count >= 40 for count in char_counts) and image_pages > 0:
        pdf_type = "mixed"
    elif total_chars >= 40:
        pdf_type = "text"
    else:
        pdf_type = "image" if image_pages else "text"

    return {
        "pdf_type": pdf_type,
        "pages": page_count,
        "text_chars": total_chars,
        "image_pages": image_pages,
    }
