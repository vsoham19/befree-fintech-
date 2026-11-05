from __future__ import annotations

import re

from app.models import Transaction

from .extractors.base import RawTransaction
from .extractors.normalize import normalize_ws

_TOLERANCE = 0.011


def _positive(value: float | None) -> float | None:
    if value is None:
        return None
    value = abs(value)
    return value if value > 0 else None


def validate_transactions(
    raw_transactions: list[RawTransaction],
    account: dict,
) -> tuple[list[Transaction], list[str]]:
    transactions: list[Transaction] = []
    warnings: list[str] = []
    previous_balance = account.get("opening_balance")
    mismatch_count = 0
    corrected_count = 0
    skipped_count = 0
    previous_date: str | None = None
    out_of_order = False
    seen: set[tuple] = set()

    for index, raw in enumerate(raw_transactions):
        if not raw.date:
            skipped_count += 1
            continue

        debit = _positive(raw.debit)
        credit = _positive(raw.credit)
        balance = raw.balance
        amount = _positive(raw.amount)
        reasons: list[str] = []
        needs_review = False

        if debit is not None and credit is not None:
            needs_review = True
            reasons.append("both_debit_and_credit")

        if debit is None and credit is None:
            if amount is not None and balance is not None and previous_balance is not None:
                delta = round(balance - previous_balance, 2)
                if delta > 0:
                    credit = amount
                elif delta < 0:
                    debit = amount
                else:
                    skipped_count += 1
                    continue
                if abs(abs(delta) - amount) > _TOLERANCE:
                    needs_review = True
                    reasons.append("amount_balance_mismatch")
            elif amount is not None:
                debit = amount
                needs_review = True
                reasons.append("direction_unknown")
            elif balance is not None and previous_balance is not None:
                delta = round(balance - previous_balance, 2)
                if delta > 0:
                    credit = abs(delta)
                elif delta < 0:
                    debit = abs(delta)
                else:
                    skipped_count += 1
                    continue
            else:
                skipped_count += 1
                continue

        expected_balance = None
        if previous_balance is not None:
            expected_balance = round(
                previous_balance - (debit or 0.0) + (credit or 0.0), 2
            )
            if balance is not None and abs(expected_balance - balance) > _TOLERANCE:
                alternate = round(previous_balance + (debit or 0.0) - (credit or 0.0), 2)
                if abs(alternate - balance) <= _TOLERANCE and (debit or credit):
                    debit, credit = credit, debit
                    corrected_count += 1
                    expected_balance = balance
                else:
                    needs_review = True
                    reasons.append("balance_mismatch")
                    mismatch_count += 1

        if previous_date and raw.date < previous_date:
            out_of_order = True
        previous_date = raw.date

        effective_balance = balance if balance is not None else expected_balance
        if effective_balance is not None:
            previous_balance = effective_balance

        description = normalize_ws(raw.description)
        duplicate_key = (
            raw.date,
            re.sub(r"\s+", " ", description.upper()),
            round(debit or 0.0, 2),
            round(credit or 0.0, 2),
            round(balance or 0.0, 2),
        )
        if duplicate_key in seen:
            needs_review = True
            reasons.append("possible_duplicate")
        seen.add(duplicate_key)

        transactions.append(
            Transaction(
                row_index=index,
                date=raw.date,
                description=description,
                debit=debit,
                credit=credit,
                balance=balance,
                needs_review=needs_review,
                review_reasons=reasons,
                raw_text=raw.raw_text,
            )
        )

    if mismatch_count:
        warnings.append(f"{mismatch_count} transaction(s) failed balance continuity checks.")
    if corrected_count:
        warnings.append(f"Direction of {corrected_count} transaction(s) corrected from balance movement.")
    if skipped_count:
        warnings.append(f"{skipped_count} row(s) skipped because amounts could not be determined.")
    if out_of_order:
        warnings.append("Transaction dates are not in chronological order.")

    closing = account.get("closing_balance")
    if closing is not None and previous_balance is not None:
        if abs(closing - previous_balance) > _TOLERANCE:
            warnings.append(
                f"Closing balance mismatch: statement says {closing:.2f}, transactions end at {previous_balance:.2f}."
            )

    return transactions, warnings
