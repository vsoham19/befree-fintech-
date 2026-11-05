import pytest

from app.core.pipeline import process_pdf


def _assert_amount(actual, expected):
    if expected is None:
        assert actual is None
    else:
        assert actual == pytest.approx(expected, abs=0.011)


def test_text_pdf_pipeline(text_statement, engine):
    path, labels = text_statement
    processed = process_pdf(path, engine, filename=path.name, stored_path=str(path))
    statement = processed.statement

    assert statement.status == "processed"
    assert statement.pdf_type == "text"
    assert statement.bank == labels["bank"]
    assert statement.account_holder == labels["account_holder"]
    assert statement.account_number == labels["account_number"]
    assert statement.ifsc == labels["ifsc"]
    assert statement.period_start == labels["period_start"]
    assert statement.period_end == labels["period_end"]
    assert statement.opening_balance == pytest.approx(labels["opening_balance"], abs=0.011)
    assert statement.closing_balance == pytest.approx(labels["closing_balance"], abs=0.011)

    actual = processed.transactions
    expected = labels["transactions"]
    assert len(actual) == len(expected)

    for transaction, item in zip(actual, expected):
        assert transaction.date == item["date"]
        _assert_amount(transaction.debit, item["debit"])
        _assert_amount(transaction.credit, item["credit"])
        _assert_amount(transaction.balance, item["balance"])

    correct = sum(
        1 for transaction, item in zip(actual, expected) if transaction.category == item["category"]
    )
    assert correct / len(expected) >= 0.9

    assert not any("failed balance continuity" in warning.lower() for warning in statement.warnings)
