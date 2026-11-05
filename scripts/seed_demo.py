from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import Config

PREFERRED_SAMPLES = (
    "hdfc_text_001.pdf",
    "icici_text_002.pdf",
    "sbi_image_009.pdf",
    "hdfc_text_004.pdf",
)


def _reset_demo_data() -> None:
    database_path = Path(Config.DATABASE_PATH)
    if database_path.exists():
        database_path.unlink()
    upload_dir = Path(Config.UPLOAD_DIR)
    if upload_dir.exists():
        for path in upload_dir.glob("*.pdf"):
            path.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the local database with synthetic statements.")
    parser.add_argument("--samples", default="data/samples", help="Directory containing generated PDFs")
    parser.add_argument("--reset", action="store_true", help="Delete the current database and uploads first")
    parser.add_argument("--count", type=int, default=4, help="Maximum number of statements to upload")
    args = parser.parse_args()

    samples_dir = Path(args.samples)
    if not samples_dir.exists():
        parser.error(f"{samples_dir} does not exist. Generate samples with: python -m synthetic")

    candidates: list[Path] = []
    for name in PREFERRED_SAMPLES:
        path = samples_dir / name
        if path.exists():
            candidates.append(path)
    for path in sorted(samples_dir.glob("*.pdf")):
        if path not in candidates:
            candidates.append(path)
    candidates = candidates[: max(1, args.count)]

    if not candidates:
        parser.error(f"No PDFs found in {samples_dir}")

    if args.reset:
        _reset_demo_data()

    from app import create_app

    app = create_app()
    client = app.test_client()

    for path in candidates:
        with open(path, "rb") as handle:
            response = client.post(
                "/api/statements",
                data={"file": (io.BytesIO(handle.read()), path.name)},
                content_type="multipart/form-data",
            )
        payload = response.get_json() or {}
        if payload.get("statements"):
            statement = payload["statements"][0]
            print(
                f"{path.name}: {statement['status']} | "
                f"{statement['summary']['transaction_count']} transactions | {statement['bank']}"
            )
        else:
            errors = payload.get("errors") or []
            message = errors[0]["message"] if errors else "unknown error"
            print(f"{path.name}: FAILED · {message}")

    stats = client.get("/api/stats").get_json()
    print(
        f"\nDatabase now holds {stats['total_statements']} statements "
        f"and {stats['total_transactions']} transactions."
    )


if __name__ == "__main__":
    main()
