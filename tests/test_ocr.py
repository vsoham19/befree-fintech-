import pytest

from app.config import Config
from app.core.pipeline import process_pdf

pytestmark = pytest.mark.skipif(
    not Config.TESSERACT_CMD, reason="Tesseract OCR is not installed"
)


def test_image_pdf_pipeline(image_statement, engine):
    path, labels = image_statement
    processed = process_pdf(
        path,
        engine,
        ocr_dpi=300,
        tesseract_cmd=Config.TESSERACT_CMD,
        filename=path.name,
        stored_path=str(path),
    )
    statement = processed.statement
    assert statement.pdf_type == "image"
    assert statement.bank == labels["bank"]

    expected = labels["transactions"]
    actual_keys = {
        (transaction.date, round(float(transaction.balance), 2))
        for transaction in processed.transactions
        if transaction.balance is not None
    }
    expected_keys = [
        (item["date"], round(float(item["balance"]), 2)) for item in expected
    ]
    matched = sum(1 for key in expected_keys if key in actual_keys)
    assert matched / len(expected_keys) >= 0.7

    matched_transactions = {
        (transaction.date, round(float(transaction.balance), 2)): transaction
        for transaction in processed.transactions
    }
    category_hits = 0
    checked = 0
    for item in expected:
        key = (item["date"], round(float(item["balance"]), 2))
        transaction = matched_transactions.get(key)
        if transaction:
            checked += 1
            category_hits += int(transaction.category == item["category"])
    assert checked > 0
    assert category_hits / checked >= 0.8
