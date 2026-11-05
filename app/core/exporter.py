from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import datetime, timezone

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

CSV_HEADERS = [
    "Date",
    "Description",
    "Debit",
    "Credit",
    "Balance",
    "Category",
    "Classification Source",
    "Confidence",
    "Needs Review",
    "Bank",
    "Account Holder",
    "Account Number",
    "IFSC",
]


def _money(value) -> str:
    return "" if value is None else f"{float(value):.2f}"


def build_csv(statement: dict, transactions: list[dict]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_HEADERS)
    for transaction in transactions:
        writer.writerow(
            [
                transaction.get("txn_date", ""),
                transaction.get("description", ""),
                _money(transaction.get("debit")),
                _money(transaction.get("credit")),
                _money(transaction.get("balance")),
                transaction.get("category", ""),
                transaction.get("source", ""),
                f"{float(transaction.get('confidence') or 0):.2f}",
                "yes" if transaction.get("needs_review") else "no",
                statement.get("bank") or "",
                statement.get("account_holder") or "",
                statement.get("account_number") or "",
                statement.get("ifsc") or "",
            ]
        )
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


def _category_summary(transactions: list[dict]) -> list[tuple[str, int, float, float]]:
    grouped: dict[str, dict] = defaultdict(lambda: {"count": 0, "debit": 0.0, "credit": 0.0})
    for transaction in transactions:
        category = transaction.get("category") or "Uncategorized"
        grouped[category]["count"] += 1
        grouped[category]["debit"] += float(transaction.get("debit") or 0)
        grouped[category]["credit"] += float(transaction.get("credit") or 0)
    return sorted(
        ((name, values["count"], values["debit"], values["credit"]) for name, values in grouped.items()),
        key=lambda item: item[0],
    )


def build_xlsx(statement: dict, transactions: list[dict]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Transactions"

    header_fill = PatternFill("solid", fgColor="0F172A")
    header_font = Font(color="FFFFFF", bold=True, size=10)
    review_fill = PatternFill("solid", fgColor="FEF3C7")
    thin = Side(style="thin", color="E2E8F0")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for column, header in enumerate(CSV_HEADERS, start=1):
        cell = sheet.cell(row=1, column=column, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border

    for row_index, transaction in enumerate(transactions, start=2):
        values = [
            transaction.get("txn_date", ""),
            transaction.get("description", ""),
            transaction.get("debit"),
            transaction.get("credit"),
            transaction.get("balance"),
            transaction.get("category", ""),
            transaction.get("source", ""),
            float(transaction.get("confidence") or 0),
            "yes" if transaction.get("needs_review") else "no",
            statement.get("bank") or "",
            statement.get("account_holder") or "",
            statement.get("account_number") or "",
            statement.get("ifsc") or "",
        ]
        for column, value in enumerate(values, start=1):
            cell = sheet.cell(row=row_index, column=column, value=value)
            cell.border = border
            if column in (3, 4, 5):
                cell.number_format = '#,##0.00'
                cell.alignment = Alignment(horizontal="right")
            elif column == 8:
                cell.number_format = "0.00"
            elif column == 9:
                cell.alignment = Alignment(horizontal="center")
            if transaction.get("needs_review"):
                cell.fill = review_fill

    widths = [12, 48, 14, 14, 16, 28, 20, 12, 14, 20, 22, 22, 14]
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:M{max(1, len(transactions) + 1)}"

    summary = workbook.create_sheet("Summary")
    summary["A1"] = "Bank Statement Summary"
    summary["A1"].font = Font(bold=True, size=14, color="0F172A")

    details = [
        ("File", statement.get("filename")),
        ("Bank", statement.get("bank")),
        ("Account Holder", statement.get("account_holder")),
        ("Account Number", statement.get("account_number")),
        ("IFSC", statement.get("ifsc")),
        ("Period Start", statement.get("period_start")),
        ("Period End", statement.get("period_end")),
        ("Opening Balance", statement.get("opening_balance")),
        ("Closing Balance", statement.get("closing_balance")),
        ("PDF Type", statement.get("pdf_type")),
        ("Transactions", len(transactions)),
        ("Total Debit", round(sum(float(t.get("debit") or 0) for t in transactions), 2)),
        ("Total Credit", round(sum(float(t.get("credit") or 0) for t in transactions), 2)),
        ("Exported At", datetime.now(timezone.utc).replace(microsecond=0).isoformat()),
    ]
    row = 3
    for label, value in details:
        summary.cell(row=row, column=1, value=label).font = Font(bold=True, color="334155")
        summary.cell(row=row, column=2, value=value)
        row += 1

    row += 1
    summary.cell(row=row, column=1, value="Category").font = header_font
    summary.cell(row=row, column=1).fill = header_fill
    summary.cell(row=row, column=2, value="Transactions").font = header_font
    summary.cell(row=row, column=2).fill = header_fill
    summary.cell(row=row, column=3, value="Debit Total").font = header_font
    summary.cell(row=row, column=3).fill = header_fill
    summary.cell(row=row, column=4, value="Credit Total").font = header_font
    summary.cell(row=row, column=4).fill = header_fill

    for category, count, debit, credit in _category_summary(transactions):
        row += 1
        summary.cell(row=row, column=1, value=category)
        summary.cell(row=row, column=2, value=count)
        summary.cell(row=row, column=3, value=round(debit, 2)).number_format = '#,##0.00'
        summary.cell(row=row, column=4, value=round(credit, 2)).number_format = '#,##0.00'

    summary.column_dimensions["A"].width = 32
    summary.column_dimensions["B"].width = 22
    summary.column_dimensions["C"].width = 18
    summary.column_dimensions["D"].width = 18

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
