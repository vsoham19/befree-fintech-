from __future__ import annotations

import hashlib
import json
import logging
import re
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, request, send_file
from werkzeug.utils import secure_filename

from app.core.exporter import build_csv, build_xlsx
from app.core.pipeline import process_pdf
from app.db import Database
from app.errors import ApiError, ExtractionError
from app.models import Statement

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _db() -> Database:
    return current_app.extensions["db"]


def _engine():
    return current_app.extensions["classification_engine"]


def _category_names() -> set[str]:
    return {category["name"] for category in current_app.extensions["categories"]}


def _transaction_payload(row: dict) -> dict:
    direction = "debit" if row.get("debit") else ("credit" if row.get("credit") else None)
    return {
        "id": row["id"],
        "statement_id": row["statement_id"],
        "row_index": row.get("row_index"),
        "date": row.get("txn_date"),
        "description": row.get("description") or "",
        "debit": row.get("debit"),
        "credit": row.get("credit"),
        "balance": row.get("balance"),
        "direction": direction,
        "category": row.get("category") or "Uncategorized",
        "source": row.get("source") or "fallback",
        "confidence": round(float(row.get("confidence") or 0), 4),
        "needs_review": bool(row.get("needs_review")),
        "review_reasons": row.get("review_reasons") or [],
        "raw_text": row.get("raw_text") or "",
    }


def _statement_payload(row: dict, include_transactions: bool = False) -> dict:
    payload = {
        "id": row["id"],
        "filename": row.get("filename"),
        "bank": row.get("bank") or "Unknown Bank",
        "pdf_type": row.get("pdf_type"),
        "status": row.get("status"),
        "error": row.get("error"),
        "account": {
            "holder": row.get("account_holder"),
            "account_number": row.get("account_number"),
            "ifsc": row.get("ifsc"),
        },
        "period": {
            "start": row.get("period_start"),
            "end": row.get("period_end"),
        },
        "opening_balance": row.get("opening_balance"),
        "closing_balance": row.get("closing_balance"),
        "warnings": row.get("warnings") or [],
        "created_at": row.get("created_at"),
        "transaction_count": row.get("transaction_count", 0),
        "review_count": row.get("review_count", 0),
        "summary": _db().statement_summary(row["id"]),
    }
    if include_transactions:
        payload["transactions"] = [
            _transaction_payload(transaction)
            for transaction in _db().get_all_transactions(row["id"])
        ]
    return payload


@api_bp.get("/health")
def health():
    config = current_app.config
    return jsonify(
        {
            "status": "ok",
            "ocr": {
                "available": bool(config.get("TESSERACT_CMD")),
                "command": config.get("TESSERACT_CMD"),
            },
            "categories": len(current_app.extensions["categories"]),
        }
    )


@api_bp.get("/categories")
def categories():
    return jsonify({"categories": current_app.extensions["categories"]})


@api_bp.get("/rules")
def list_rules():
    rules_path = current_app.config["RULES_PATH"]
    with open(rules_path, encoding="utf-8") as handle:
        payload = json.load(handle)
    rules = [
        {
            "id": item.get("id"),
            "category": item.get("category"),
            "direction": item.get("direction", "any"),
            "confidence": item.get("confidence", 0.0),
            "patterns": item.get("patterns", []),
        }
        for item in payload.get("rules", [])
    ]
    return jsonify({"rules": rules, "count": len(rules)})


@api_bp.get("/stats")
def stats():
    return jsonify(_db().stats())


@api_bp.get("/statements")
def list_statements():
    rows = _db().list_statements(
        query=request.args.get("q"),
        bank=request.args.get("bank"),
        status=request.args.get("status"),
        limit=min(int(request.args.get("limit", 100)), 500),
    )
    return jsonify({"items": [_statement_payload(row) for row in rows], "count": len(rows)})


@api_bp.post("/statements")
def upload_statements():
    uploads = request.files.getlist("files") + request.files.getlist("file")
    uploads = [item for item in uploads if item and item.filename]
    if not uploads:
        raise ApiError(
            "No PDF file provided. Use the 'file' or 'files' form field.",
            status_code=400,
            code="no_file",
        )

    database = _db()
    config = current_app.config
    upload_dir = Path(config["UPLOAD_DIR"])
    upload_dir.mkdir(parents=True, exist_ok=True)

    created: list[dict] = []
    errors: list[dict] = []

    for upload in uploads:
        original = secure_filename(upload.filename) or "statement.pdf"
        if Path(original).suffix.lower() != ".pdf":
            errors.append(
                {
                    "filename": upload.filename,
                    "code": "unsupported_file_type",
                    "message": "Only PDF files are supported.",
                }
            )
            continue

        stored_path = upload_dir / f"{uuid4().hex}.pdf"
        upload.save(stored_path)
        digest = hashlib.sha256(stored_path.read_bytes()).hexdigest()

        existing = database.find_by_hash(digest)
        if existing:
            stored_path.unlink(missing_ok=True)
            payload = _statement_payload(existing, include_transactions=True)
            payload["duplicate"] = True
            created.append(payload)
            continue

        try:
            processed = process_pdf(
                stored_path,
                _engine(),
                ocr_dpi=config["OCR_DPI"],
                tesseract_cmd=config.get("TESSERACT_CMD"),
                filename=original,
                stored_path=str(stored_path),
                file_hash=digest,
            )
            database.insert_statement(
                processed.statement.to_record(),
                [transaction.to_record() for transaction in processed.transactions],
            )
            row = database.get_statement(processed.statement.id)
            created.append(_statement_payload(row, include_transactions=True))
        except ExtractionError as exc:
            failure = Statement(
                filename=original,
                stored_path=str(stored_path),
                file_hash=digest,
                status="failed",
                error=exc.message,
            )
            database.insert_statement(failure.to_record(), [])
            errors.append(
                {
                    "filename": original,
                    "code": exc.code,
                    "message": exc.message,
                    "statement_id": failure.id,
                    "details": exc.details,
                }
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Unexpected error while processing %s", original)
            failure = Statement(
                filename=original,
                stored_path=str(stored_path),
                file_hash=digest,
                status="failed",
                error="Unexpected error while processing statement.",
            )
            database.insert_statement(failure.to_record(), [])
            errors.append(
                {
                    "filename": original,
                    "code": "internal_error",
                    "message": "Unexpected error while processing statement.",
                    "statement_id": failure.id,
                    "details": {"error": str(exc)},
                }
            )

    status = 201 if created else 422
    return jsonify({"statements": created, "errors": errors}), status


@api_bp.get("/statements/<statement_id>")
def get_statement(statement_id: str):
    row = _db().get_statement(statement_id)
    if not row:
        raise ApiError("Statement not found.", status_code=404, code="statement_not_found")
    return jsonify(_statement_payload(row, include_transactions=True))


@api_bp.delete("/statements/<statement_id>")
def delete_statement(statement_id: str):
    row = _db().delete_statement(statement_id)
    if not row:
        raise ApiError("Statement not found.", status_code=404, code="statement_not_found")
    stored_path = row.get("stored_path")
    if stored_path:
        Path(stored_path).unlink(missing_ok=True)
    return jsonify({"deleted": statement_id})


@api_bp.post("/statements/<statement_id>/reprocess")
def reprocess_statement(statement_id: str):
    database = _db()
    row = database.get_statement(statement_id)
    if not row:
        raise ApiError("Statement not found.", status_code=404, code="statement_not_found")
    stored_path = Path(row.get("stored_path") or "")
    if not stored_path.exists():
        raise ApiError(
            "The stored PDF for this statement is missing.",
            status_code=410,
            code="source_file_missing",
        )

    config = current_app.config
    try:
        processed = process_pdf(
            stored_path,
            _engine(),
            ocr_dpi=config["OCR_DPI"],
            tesseract_cmd=config.get("TESSERACT_CMD"),
            filename=row.get("filename"),
            stored_path=str(stored_path),
            file_hash=row.get("file_hash"),
            statement_id=statement_id,
        )
    except ExtractionError as exc:
        database.update_statement(statement_id, {"status": "failed", "error": exc.message})
        raise ApiError(exc.message, status_code=422, code=exc.code, details=exc.details) from exc

    statement = processed.statement
    database.replace_transactions(
        statement_id, [transaction.to_record() for transaction in processed.transactions]
    )
    database.update_statement(
        statement_id,
        {
            "bank": statement.bank,
            "pdf_type": statement.pdf_type,
            "account_holder": statement.account_holder,
            "account_number": statement.account_number,
            "ifsc": statement.ifsc,
            "period_start": statement.period_start,
            "period_end": statement.period_end,
            "opening_balance": statement.opening_balance,
            "closing_balance": statement.closing_balance,
            "status": "processed",
            "error": None,
            "warnings": statement.warnings,
        },
    )
    updated = database.get_statement(statement_id)
    return jsonify(_statement_payload(updated, include_transactions=True))


@api_bp.get("/statements/<statement_id>/transactions")
def list_transactions(statement_id: str):
    if not _db().get_statement(statement_id):
        raise ApiError("Statement not found.", status_code=404, code="statement_not_found")

    try:
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(max(1, int(request.args.get("per_page", 100))), 500)
    except ValueError as exc:
        raise ApiError("Pagination parameters must be integers.", status_code=400, code="invalid_pagination") from exc

    needs_review = request.args.get("needs_review")
    review_filter = None
    if needs_review is not None:
        review_filter = needs_review.lower() in {"1", "true", "yes"}

    min_confidence = request.args.get("min_confidence")
    confidence_filter = None
    if min_confidence is not None:
        try:
            confidence_filter = float(min_confidence)
        except ValueError as exc:
            raise ApiError("min_confidence must be a number.", status_code=400, code="invalid_filter") from exc

    items, total = _db().query_transactions(
        statement_id,
        search=request.args.get("search"),
        category=request.args.get("category"),
        direction=request.args.get("direction"),
        needs_review=review_filter,
        min_confidence=confidence_filter,
        page=page,
        per_page=per_page,
    )
    pages = (total + per_page - 1) // per_page if total else 0
    return jsonify(
        {
            "items": [_transaction_payload(item) for item in items],
            "pagination": {"page": page, "per_page": per_page, "total": total, "pages": pages},
            "summary": _db().statement_summary(statement_id),
        }
    )


@api_bp.patch("/transactions/<transaction_id>")
def update_transaction(transaction_id: str):
    payload = request.get_json(silent=True) or {}
    category = payload.get("category")
    if category not in _category_names():
        raise ApiError(
            "A valid category is required.",
            status_code=422,
            code="invalid_category",
            details={"allowed": sorted(_category_names())},
        )
    existing = _db().get_transaction(transaction_id)
    if not existing:
        raise ApiError("Transaction not found.", status_code=404, code="transaction_not_found")
    updated = _db().update_transaction(
        transaction_id,
        {
            "category": category,
            "source": "user",
            "confidence": 1.0,
            "needs_review": 0,
            "review_reasons": [],
        },
    )
    return jsonify({"transaction": _transaction_payload(updated)})


@api_bp.post("/transactions/bulk-category")
def bulk_update_category():
    payload = request.get_json(silent=True) or {}
    category = payload.get("category")
    transaction_ids = payload.get("transaction_ids") or payload.get("ids") or []
    if category not in _category_names():
        raise ApiError(
            "A valid category is required.",
            status_code=422,
            code="invalid_category",
            details={"allowed": sorted(_category_names())},
        )
    if not isinstance(transaction_ids, list) or not transaction_ids:
        raise ApiError(
            "transaction_ids must be a non-empty list.",
            status_code=422,
            code="invalid_transaction_ids",
        )
    updated = _db().bulk_update_categories([str(item) for item in transaction_ids], category)
    return jsonify({"updated": updated, "category": category})


@api_bp.get("/statements/<statement_id>/export")
def export_statement(statement_id: str):
    database = _db()
    row = database.get_statement(statement_id)
    if not row:
        raise ApiError("Statement not found.", status_code=404, code="statement_not_found")

    export_format = (request.args.get("format") or "csv").lower()
    if export_format not in {"csv", "xlsx"}:
        raise ApiError(
            "format must be either 'csv' or 'xlsx'.",
            status_code=400,
            code="invalid_format",
        )

    transactions = database.get_all_transactions(statement_id)
    if export_format == "csv":
        data = build_csv(row, transactions)
        mimetype = "text/csv; charset=utf-8"
    else:
        data = build_xlsx(row, transactions)
        mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    safe_bank = re.sub(r"[^A-Za-z0-9_-]+", "_", row.get("bank") or "statement").strip("_")
    filename = f"{safe_bank}_{statement_id[:8]}_transactions.{export_format}"
    return send_file(
        BytesIO(data),
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename,
    )
