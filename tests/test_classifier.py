from app.config import Config
from app.core.classifiers.rules import RuleEngine


def test_food_rule(engine):
    result = engine.classify("UPI/DR/12345678/SWIGGY/ybl", "debit")
    assert result.category == "Food & Dining"
    assert result.source == "rule"


def test_salary_requires_credit(engine):
    result = engine.classify("NEFT CR-INFOSYS-SALARY APR 2025-12345678", "credit")
    assert result.category == "Salary & Income"

    rule_engine = RuleEngine.from_file(Config.RULES_PATH)
    debit_match = rule_engine.classify("SALARY TRANSFER", "debit")
    assert debit_match is None or debit_match.category != "Salary & Income"


def test_merchant_rules(engine):
    assert engine.classify("POS/12345678/IRCTC/BENGALURU", "debit").category == "Travel"
    assert engine.classify("ATM/CASH WDL/BENGALURU/12345678", "debit").category == "Cash & ATM"
    assert engine.classify("UPI-DR-12345678-NETFLIX-ybl", "debit").category == (
        "Entertainment & Subscriptions"
    )
    assert engine.classify("ACH DR-HDFC LTD-EMI-12345678", "debit").category == "EMI & Loans"


def test_ml_predicts_known_merchant(engine):
    category, probability = engine.ml.predict("UPI-DR-12345678-BIGBASKET-ybl", "debit")
    assert category == "Groceries"
    assert probability > 0.4


def test_unknown_description_is_flagged(engine):
    result = engine.classify("XYZQ 0000 UNKNOWN ENTRY", "debit")
    assert result.needs_review is True
