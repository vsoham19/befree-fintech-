from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import Config
from app.core.classifiers.pipeline import ClassificationEngine
from app.core.pipeline import process_pdf


def _close(actual, expected, tolerance: float = 0.02) -> bool:
    if actual is None and expected is None:
        return True
    if actual is None or expected is None:
        return False
    return abs(float(actual) - float(expected)) <= tolerance


def _evaluate_sample(engine, sample_path: Path, label: dict) -> dict:
    processed = process_pdf(
        sample_path,
        engine,
        ocr_dpi=Config.OCR_DPI,
        tesseract_cmd=Config.TESSERACT_CMD,
        filename=label["file"],
        stored_path=str(sample_path),
    )

    actual = processed.transactions
    expected = label["transactions"]

    actual_by_balance: dict[tuple, list] = defaultdict(list)
    for transaction in actual:
        key = (transaction.date, round(float(transaction.balance), 2))
        actual_by_balance[key].append(transaction)

    matched = 0
    field_hits = 0
    category_hits = 0
    for item in expected:
        key = (item["date"], round(float(item["balance"]), 2))
        candidates = actual_by_balance.get(key)
        if not candidates:
            continue
        transaction = candidates.pop(0)
        matched += 1
        field_hits += sum(
            [
                int(transaction.date == item["date"]),
                int(_close(transaction.debit, item.get("debit"))),
                int(_close(transaction.credit, item.get("credit"))),
                int(_close(transaction.balance, item.get("balance"))),
            ]
        )
        category_hits += int(transaction.category == item["category"])

    statement = processed.statement
    return {
        "file": label["file"],
        "pdf_type": label["pdf_type"],
        "bank_ok": statement.bank == label["bank"],
        "holder_ok": statement.account_holder == label["account_holder"],
        "account_ok": statement.account_number == label["account_number"],
        "ifsc_ok": statement.ifsc == label["ifsc"],
        "expected_rows": len(expected),
        "actual_rows": len(actual),
        "matched_rows": matched,
        "row_recall": matched / len(expected) if expected else 0.0,
        "field_accuracy": field_hits / (matched * 4) if matched else 0.0,
        "category_accuracy": category_hits / matched if matched else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate extraction and classification accuracy.")
    parser.add_argument("--samples", default="data/samples", help="Directory containing labels.json")
    parser.add_argument("--min-field-accuracy", type=float, default=0.0)
    args = parser.parse_args()

    samples_dir = Path(args.samples)
    labels_path = samples_dir / "labels.json"
    if not labels_path.exists():
        parser.error(f"{labels_path} not found. Generate samples with: python -m synthetic")

    payload = json.loads(labels_path.read_text(encoding="utf-8"))
    samples = payload.get("samples", payload if isinstance(payload, list) else [])

    engine = ClassificationEngine(
        rules_path=Config.RULES_PATH,
        model_path=Path(Config.MODEL_DIR) / "classifier.joblib",
        categories_path=Config.CATEGORIES_PATH,
    )

    results = []
    skipped = 0
    for label in samples:
        sample_path = samples_dir / label["file"]
        if not sample_path.exists():
            continue
        if label["pdf_type"] == "image" and not Config.TESSERACT_CMD:
            print(f"SKIP {label['file']} (Tesseract not available)")
            skipped += 1
            continue
        try:
            result = _evaluate_sample(engine, sample_path, label)
        except Exception as exc:
            print(f"FAIL {label['file']}: {exc}")
            skipped += 1
            continue
        results.append(result)
        print(
            f"{result['file']:<28} rows {result['matched_rows']}/{result['expected_rows']} "
            f"field {result['field_accuracy']:.1%} cat {result['category_accuracy']:.1%} "
            f"bank {'ok' if result['bank_ok'] else 'MISS'}"
        )

    if not results:
        print("No samples evaluated.")
        raise SystemExit(1)

    average = lambda key: sum(item[key] for item in results) / len(results)
    print("\nSummary")
    print(f"  samples evaluated : {len(results)} (skipped {skipped})")
    print(f"  bank accuracy     : {sum(item['bank_ok'] for item in results) / len(results):.1%}")
    print(f"  holder accuracy   : {sum(item['holder_ok'] for item in results) / len(results):.1%}")
    print(f"  account accuracy  : {sum(item['account_ok'] for item in results) / len(results):.1%}")
    print(f"  IFSC accuracy     : {sum(item['ifsc_ok'] for item in results) / len(results):.1%}")
    print(f"  row recall        : {average('row_recall'):.1%}")
    print(f"  field accuracy    : {average('field_accuracy'):.1%}")
    print(f"  category accuracy : {average('category_accuracy'):.1%}")

    if average("field_accuracy") < args.min_field_accuracy:
        raise SystemExit(
            f"Field accuracy {average('field_accuracy'):.1%} below threshold "
            f"{args.min_field_accuracy:.1%}"
        )


if __name__ == "__main__":
    main()
