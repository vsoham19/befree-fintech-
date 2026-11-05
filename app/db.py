from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS statements (
    id TEXT PRIMARY KEY,
    file_hash TEXT,
    filename TEXT NOT NULL,
    stored_path TEXT,
    bank TEXT,
    pdf_type TEXT,
    account_holder TEXT,
    account_number TEXT,
    ifsc TEXT,
    period_start TEXT,
    period_end TEXT,
    opening_balance REAL,
    closing_balance REAL,
    status TEXT NOT NULL,
    error TEXT,
    warnings TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    statement_id TEXT NOT NULL REFERENCES statements(id) ON DELETE CASCADE,
    row_index INTEGER,
    txn_date TEXT,
    description TEXT,
    debit REAL,
    credit REAL,
    balance REAL,
    category TEXT,
    source TEXT,
    confidence REAL,
    needs_review INTEGER DEFAULT 0,
    review_reasons TEXT,
    raw_text TEXT
);

CREATE INDEX IF NOT EXISTS idx_transactions_statement ON transactions(statement_id);
CREATE INDEX IF NOT EXISTS idx_statements_hash ON statements(file_hash);
CREATE INDEX IF NOT EXISTS idx_statements_created ON statements(created_at);
"""

STATEMENT_COLUMNS = [
    "id",
    "file_hash",
    "filename",
    "stored_path",
    "bank",
    "pdf_type",
    "account_holder",
    "account_number",
    "ifsc",
    "period_start",
    "period_end",
    "opening_balance",
    "closing_balance",
    "status",
    "error",
    "warnings",
    "created_at",
]

TRANSACTION_COLUMNS = [
    "id",
    "statement_id",
    "row_index",
    "txn_date",
    "description",
    "debit",
    "credit",
    "balance",
    "category",
    "source",
    "confidence",
    "needs_review",
    "review_reasons",
    "raw_text",
]


def _json_dump(value) -> str:
    return json.dumps(value if value is not None else [], ensure_ascii=False)


def _json_load(value, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return fallback


class Database:
    def __init__(self, path: Path | str):
        self.path = Path(path)

    @contextmanager
    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def init(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    def insert_statement(self, statement: dict, transactions: list[dict]) -> None:
        statement = dict(statement)
        statement["warnings"] = _json_dump(statement.get("warnings"))
        columns = ", ".join(STATEMENT_COLUMNS)
        placeholders = ", ".join("?" for _ in STATEMENT_COLUMNS)
        with self.connect() as connection:
            connection.execute(
                f"INSERT INTO statements ({columns}) VALUES ({placeholders})",
                tuple(statement.get(column) for column in STATEMENT_COLUMNS),
            )
            self._insert_transactions(connection, transactions)

    def _insert_transactions(self, connection, transactions: list[dict]) -> None:
        columns = ", ".join(TRANSACTION_COLUMNS)
        placeholders = ", ".join("?" for _ in TRANSACTION_COLUMNS)
        rows = []
        for transaction in transactions:
            transaction = dict(transaction)
            transaction["review_reasons"] = _json_dump(transaction.get("review_reasons"))
            rows.append(tuple(transaction.get(column) for column in TRANSACTION_COLUMNS))
        if rows:
            connection.executemany(
                f"INSERT INTO transactions ({columns}) VALUES ({placeholders})",
                rows,
            )

    def replace_transactions(self, statement_id: str, transactions: list[dict]) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM transactions WHERE statement_id = ?", (statement_id,))
            self._insert_transactions(connection, transactions)

    def update_statement(self, statement_id: str, fields: dict) -> None:
        fields = dict(fields)
        if "warnings" in fields:
            fields["warnings"] = _json_dump(fields["warnings"])
        assignments = ", ".join(f"{key} = ?" for key in fields)
        with self.connect() as connection:
            connection.execute(
                f"UPDATE statements SET {assignments} WHERE id = ?",
                tuple(fields.values()) + (statement_id,),
            )

    def find_by_hash(self, file_hash: str) -> dict | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM statements WHERE file_hash = ? AND status = 'processed' ORDER BY created_at DESC LIMIT 1",
                (file_hash,),
            ).fetchone()
        return self._statement_row(row) if row else None

    def get_statement(self, statement_id: str) -> dict | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT s.*,
                       (SELECT COUNT(*) FROM transactions t WHERE t.statement_id = s.id) AS transaction_count,
                       (SELECT COUNT(*) FROM transactions t WHERE t.statement_id = s.id AND t.needs_review = 1) AS review_count
                FROM statements s WHERE s.id = ?
                """,
                (statement_id,),
            ).fetchone()
        return self._statement_row(row) if row else None

    def list_statements(self, query: str | None = None, bank: str | None = None, status: str | None = None, limit: int = 100) -> list[dict]:
        where = []
        params: list = []
        if query:
            where.append("(s.filename LIKE ? OR s.bank LIKE ? OR s.account_holder LIKE ? OR s.account_number LIKE ?)")
            pattern = f"%{query}%"
            params.extend([pattern, pattern, pattern, pattern])
        if bank:
            where.append("s.bank = ?")
            params.append(bank)
        if status:
            where.append("s.status = ?")
            params.append(status)
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT s.*,
                       (SELECT COUNT(*) FROM transactions t WHERE t.statement_id = s.id) AS transaction_count,
                       (SELECT COUNT(*) FROM transactions t WHERE t.statement_id = s.id AND t.needs_review = 1) AS review_count
                FROM statements s
                {clause}
                ORDER BY s.created_at DESC
                LIMIT ?
                """,
                tuple(params) + (limit,),
            ).fetchall()
        return [self._statement_row(row) for row in rows]

    def delete_statement(self, statement_id: str) -> dict | None:
        row = self.get_statement(statement_id)
        if not row:
            return None
        with self.connect() as connection:
            connection.execute("DELETE FROM statements WHERE id = ?", (statement_id,))
        return row

    def statement_summary(self, statement_id: str) -> dict:
        with self.connect() as connection:
            aggregate = connection.execute(
                """
                SELECT COUNT(*) AS total,
                       COALESCE(SUM(debit), 0) AS total_debit,
                       COALESCE(SUM(credit), 0) AS total_credit,
                       COALESCE(SUM(CASE WHEN needs_review = 1 THEN 1 ELSE 0 END), 0) AS review,
                       COALESCE(SUM(CASE WHEN category <> 'Uncategorized' THEN 1 ELSE 0 END), 0) AS categorized
                FROM transactions WHERE statement_id = ?
                """,
                (statement_id,),
            ).fetchone()
            categories = connection.execute(
                "SELECT category, COUNT(*) AS count FROM transactions WHERE statement_id = ? GROUP BY category",
                (statement_id,),
            ).fetchall()
            sources = connection.execute(
                "SELECT source, COUNT(*) AS count FROM transactions WHERE statement_id = ? GROUP BY source",
                (statement_id,),
            ).fetchall()

        total = aggregate["total"] or 0
        categorized = aggregate["categorized"] or 0
        return {
            "transaction_count": total,
            "total_debit": round(aggregate["total_debit"] or 0, 2),
            "total_credit": round(aggregate["total_credit"] or 0, 2),
            "needs_review": aggregate["review"] or 0,
            "categorized": categorized,
            "classification_rate": round(categorized / total, 4) if total else 0.0,
            "category_counts": {row["category"] or "Uncategorized": row["count"] for row in categories},
            "source_counts": {row["source"] or "fallback": row["count"] for row in sources},
        }

    def query_transactions(
        self,
        statement_id: str,
        *,
        search: str | None = None,
        category: str | None = None,
        direction: str | None = None,
        needs_review: bool | None = None,
        min_confidence: float | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> tuple[list[dict], int]:
        where = ["statement_id = ?"]
        params: list = [statement_id]
        if search:
            where.append("description LIKE ?")
            params.append(f"%{search}%")
        if category:
            where.append("category = ?")
            params.append(category)
        if direction == "debit":
            where.append("debit IS NOT NULL AND debit > 0")
        elif direction == "credit":
            where.append("credit IS NOT NULL AND credit > 0")
        if needs_review is not None:
            where.append("needs_review = ?")
            params.append(1 if needs_review else 0)
        if min_confidence is not None:
            where.append("confidence >= ?")
            params.append(min_confidence)
        clause = " AND ".join(where)
        offset = max(0, (page - 1) * per_page)
        with self.connect() as connection:
            total = connection.execute(
                f"SELECT COUNT(*) AS count FROM transactions WHERE {clause}", tuple(params)
            ).fetchone()["count"]
            rows = connection.execute(
                f"SELECT * FROM transactions WHERE {clause} ORDER BY row_index ASC LIMIT ? OFFSET ?",
                tuple(params) + (per_page, offset),
            ).fetchall()
        return [self._transaction_row(row) for row in rows], total

    def get_all_transactions(self, statement_id: str) -> list[dict]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM transactions WHERE statement_id = ? ORDER BY row_index ASC",
                (statement_id,),
            ).fetchall()
        return [self._transaction_row(row) for row in rows]

    def get_transaction(self, transaction_id: str) -> dict | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM transactions WHERE id = ?", (transaction_id,)
            ).fetchone()
        return self._transaction_row(row) if row else None

    def update_transaction(self, transaction_id: str, fields: dict) -> dict | None:
        fields = dict(fields)
        if "review_reasons" in fields:
            fields["review_reasons"] = _json_dump(fields["review_reasons"])
        if not fields:
            return self.get_transaction(transaction_id)
        assignments = ", ".join(f"{key} = ?" for key in fields)
        with self.connect() as connection:
            cursor = connection.execute(
                f"UPDATE transactions SET {assignments} WHERE id = ?",
                tuple(fields.values()) + (transaction_id,),
            )
            if cursor.rowcount == 0:
                return None
        return self.get_transaction(transaction_id)

    def bulk_update_categories(self, transaction_ids: list[str], category: str) -> int:
        if not transaction_ids:
            return 0
        placeholders = ", ".join("?" for _ in transaction_ids)
        with self.connect() as connection:
            cursor = connection.execute(
                f"""
                UPDATE transactions
                SET category = ?, source = 'user', confidence = 1.0, needs_review = 0, review_reasons = '[]'
                WHERE id IN ({placeholders})
                """,
                (category, *transaction_ids),
            )
        return cursor.rowcount

    def stats(self) -> dict:
        with self.connect() as connection:
            statements = connection.execute(
                "SELECT COUNT(*) AS count FROM statements WHERE status = 'processed'"
            ).fetchone()["count"]
            failed = connection.execute(
                "SELECT COUNT(*) AS count FROM statements WHERE status = 'failed'"
            ).fetchone()["count"]
            aggregate = connection.execute(
                """
                SELECT COUNT(*) AS total,
                       COALESCE(SUM(debit), 0) AS total_debit,
                       COALESCE(SUM(credit), 0) AS total_credit,
                       COALESCE(SUM(CASE WHEN needs_review = 1 THEN 1 ELSE 0 END), 0) AS review,
                       COALESCE(SUM(CASE WHEN category <> 'Uncategorized' THEN 1 ELSE 0 END), 0) AS categorized
                FROM transactions
                """
            ).fetchone()
            categories = connection.execute(
                """
                SELECT category, COUNT(*) AS count,
                       COALESCE(SUM(debit), 0) AS debit_total,
                       COALESCE(SUM(credit), 0) AS credit_total
                FROM transactions
                GROUP BY category
                ORDER BY count DESC
                """
            ).fetchall()
            banks = connection.execute(
                "SELECT bank, COUNT(*) AS count FROM statements WHERE status = 'processed' GROUP BY bank ORDER BY count DESC"
            ).fetchall()
            sources = connection.execute(
                "SELECT source, COUNT(*) AS count FROM transactions GROUP BY source"
            ).fetchall()
            recent = connection.execute(
                """
                SELECT s.*,
                       (SELECT COUNT(*) FROM transactions t WHERE t.statement_id = s.id) AS transaction_count,
                       (SELECT COUNT(*) FROM transactions t WHERE t.statement_id = s.id AND t.needs_review = 1) AS review_count
                FROM statements s ORDER BY s.created_at DESC LIMIT 5
                """
            ).fetchall()

        total = aggregate["total"] or 0
        categorized = aggregate["categorized"] or 0
        return {
            "total_statements": statements,
            "failed_statements": failed,
            "total_transactions": total,
            "total_debit": round(aggregate["total_debit"] or 0, 2),
            "total_credit": round(aggregate["total_credit"] or 0, 2),
            "needs_review": aggregate["review"] or 0,
            "classification_rate": round(categorized / total, 4) if total else 0.0,
            "by_category": [
                {
                    "category": row["category"] or "Uncategorized",
                    "count": row["count"],
                    "debit_total": round(row["debit_total"] or 0, 2),
                    "credit_total": round(row["credit_total"] or 0, 2),
                }
                for row in categories
            ],
            "by_bank": [{"bank": row["bank"] or "Unknown Bank", "count": row["count"]} for row in banks],
            "source_counts": {row["source"] or "fallback": row["count"] for row in sources},
            "recent_statements": [self._statement_row(row) for row in recent],
        }

    @staticmethod
    def _statement_row(row) -> dict:
        if row is None:
            return None
        data = dict(row)
        data["warnings"] = _json_load(data.get("warnings"), [])
        data["transaction_count"] = data.get("transaction_count") or 0
        data["review_count"] = data.get("review_count") or 0
        return data

    @staticmethod
    def _transaction_row(row) -> dict:
        data = dict(row)
        data["needs_review"] = bool(data.get("needs_review"))
        data["review_reasons"] = _json_load(data.get("review_reasons"), [])
        return data
