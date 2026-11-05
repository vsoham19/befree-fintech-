import pytest

from app.core.extractors.normalize import normalize_ws, parse_amount, parse_date


@pytest.mark.parametrize(
    "value,expected",
    [
        ("1,23,456.78", 123456.78),
        ("₹1,234.50", 1234.50),
        ("Rs. 450.00", 450.00),
        ("450.00 Cr", 450.00),
        ("1,000.50 Dr", 1000.50),
        ("(1,000.50)", -1000.50),
        ("-", None),
        ("", None),
        (None, None),
        (1234, 1234.00),
    ],
)
def test_parse_amount(value, expected):
    assert parse_amount(value) == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        ("01/04/2025", "2025-04-01"),
        ("01-04-25", "2025-04-01"),
        ("01.04.2025", "2025-04-01"),
        ("01 Apr 2025", "2025-04-01"),
        ("01-APR-2025", "2025-04-01"),
        ("2025-04-01", "2025-04-01"),
        ("not a date", None),
    ],
)
def test_parse_date(value, expected):
    assert parse_date(value) == expected


def test_normalize_ws():
    assert normalize_ws("  a   b \n c ") == "a b c"
