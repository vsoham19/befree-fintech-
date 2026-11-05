from __future__ import annotations

import calendar
import random
import string
from datetime import date, timedelta
from functools import partial
from pathlib import Path

import fitz
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.classifiers.merchants import COMPANIES, PERSON_NAMES, build_description

PROFILES = {
    "hdfc": {
        "display": "HDFC Bank",
        "title": "HDFC BANK LIMITED",
        "branch": "Koramangala, Bengaluru",
        "ifsc": "HDFC0001234",
        "color": colors.HexColor("#004C8F"),
        "columns": [
            "Date",
            "Narration",
            "Chq./Ref.No.",
            "Value Dt",
            "Withdrawal Amt.",
            "Deposit Amt.",
            "Closing Balance",
        ],
        "widths": [50, 170, 62, 50, 62, 58, 65],
        "amount_start": 4,
    },
    "icici": {
        "display": "ICICI Bank",
        "title": "ICICI BANK LIMITED",
        "branch": "Indiranagar, Bengaluru",
        "ifsc": "ICIC0004567",
        "color": colors.HexColor("#B02A30"),
        "columns": [
            "Date",
            "Mode",
            "Particulars",
            "Withdrawals (INR)",
            "Deposits (INR)",
            "Balance (INR)",
        ],
        "widths": [55, 48, 215, 63, 63, 75],
        "amount_start": 3,
    },
    "sbi": {
        "display": "State Bank of India",
        "title": "STATE BANK OF INDIA",
        "branch": "Jayanagar, Bengaluru",
        "ifsc": "SBIN0007890",
        "color": colors.HexColor("#22409A"),
        "columns": [
            "Txn Date",
            "Value Date",
            "Description",
            "Ref No./Cheque No.",
            "Debit",
            "Credit",
            "Balance",
        ],
        "widths": [48, 48, 185, 70, 50, 50, 62],
        "amount_start": 4,
    },
}

AMOUNT_RANGES = {
    "Food & Dining": (150, 1800),
    "Groceries": (300, 4500),
    "Shopping": (400, 12000),
    "Transport": (60, 900),
    "Travel": (800, 25000),
    "Utilities & Bills": (200, 3500),
    "Rent & Housing": (12000, 38000),
    "EMI & Loans": (5000, 28000),
    "Transfers": (500, 20000),
    "Cash & ATM": (1000, 10000),
    "Entertainment & Subscriptions": (149, 1499),
    "Healthcare": (200, 6000),
    "Education": (1000, 30000),
    "Fees & Charges": (50, 600),
}


def format_inr(value: float) -> str:
    negative = value < 0
    whole, fraction = f"{abs(value):.2f}".split(".")
    if len(whole) > 3:
        last_three = whole[-3:]
        rest = whole[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        whole = ",".join(groups) + "," + last_three
    return ("-" if negative else "") + whole + "." + fraction


def _digits(rng: random.Random, count: int) -> str:
    return "".join(rng.choices(string.digits, k=count))


def _add_months(value: date, months: int) -> date:
    year = value.year + (value.month - 1 + months) // 12
    month = (value.month - 1 + months) % 12 + 1
    return date(year, month, 1)


def _account_number(profile_key: str, rng: random.Random) -> str:
    if profile_key == "hdfc":
        return "50100" + _digits(rng, 9)
    if profile_key == "icici":
        return "0" + _digits(rng, 11)
    return "3" + _digits(rng, 10)


def _amount_range(category: str, variant: str | None) -> tuple[float, float]:
    if category == "Salary & Income":
        if variant == "salary":
            return (65000, 140000)
        if variant == "interest":
            return (200, 2500)
        if variant == "dividend":
            return (500, 5000)
        if variant == "cashback":
            return (20, 500)
        return (100, 3000)
    return AMOUNT_RANGES[category]


def _count(rng: random.Random, low: int, high: int, density: float) -> int:
    return max(1, round(rng.randint(low, high) * density))


def _schedule_events(rng: random.Random, start: date, months: int, density: float) -> list[dict]:
    events: list[dict] = []

    for offset in range(months):
        month_start = _add_months(start, offset)
        year, month = month_start.year, month_start.month
        days_in_month = calendar.monthrange(year, month)[1]

        def add(day: int, category: str, direction: str, variant: str | None = None) -> None:
            events.append(
                {
                    "date": date(year, month, max(1, min(day, days_in_month))),
                    "category": category,
                    "direction": direction,
                    "variant": variant,
                }
            )

        add(rng.randint(1, 4), "Salary & Income", "credit", "salary")
        add(rng.randint(4, 7), "Rent & Housing", "debit")
        add(rng.randint(6, 9), "EMI & Loans", "debit")

        for _ in range(_count(rng, 1, 2, density)):
            add(rng.randint(8, 15), "Utilities & Bills", "debit")
        for _ in range(max(0, round(rng.randint(0, 2) * density))):
            add(rng.randint(10, 24), "Entertainment & Subscriptions", "debit")
        for _ in range(_count(rng, 5, 8, density)):
            add(rng.randint(1, days_in_month), "Food & Dining", "debit")
        for _ in range(_count(rng, 3, 5, density)):
            add(rng.randint(1, days_in_month), "Groceries", "debit")
        for _ in range(_count(rng, 2, 4, density)):
            add(rng.randint(1, days_in_month), "Shopping", "debit")
        for _ in range(_count(rng, 2, 4, density)):
            add(rng.randint(1, days_in_month), "Transport", "debit")
        for _ in range(_count(rng, 1, 2, density)):
            add(rng.randint(1, days_in_month), "Cash & ATM", "debit")
        if rng.random() < 0.5:
            add(rng.randint(1, days_in_month), "Healthcare", "debit")
        if rng.random() < 0.35:
            add(rng.randint(1, days_in_month), "Travel", "debit")
        if rng.random() < 0.2:
            add(rng.randint(1, days_in_month), "Education", "debit")
        for _ in range(max(0, round(rng.randint(0, 1) * density))):
            add(rng.randint(1, days_in_month), "Fees & Charges", "debit")
        for _ in range(_count(rng, 1, 2, density)):
            add(rng.randint(1, days_in_month), "Transfers", "debit")
        if rng.random() < 0.45:
            add(rng.randint(1, days_in_month), "Transfers", "credit")
        if rng.random() < 0.6:
            variant = rng.choice(["interest", "cashback", "dividend", "refund"])
            add(rng.randint(1, days_in_month), "Salary & Income", "credit", variant)

    return events


def _materialize(
    events: list[dict],
    profile_key: str,
    rng: random.Random,
    opening_balance: float,
) -> list[dict]:
    events = sorted(events, key=lambda item: (item["date"], rng.random()))
    balance = opening_balance
    transactions: list[dict] = []

    for event in events:
        category = event["category"]
        direction = event["direction"]
        low, high = _amount_range(category, event.get("variant"))
        amount = round(rng.uniform(low, high), 2)

        if direction == "debit" and amount > balance - 500:
            amount = round(max(50.0, (balance - 500) * rng.uniform(0.1, 0.4)), 2)
        if amount <= 0:
            continue

        debit = amount if direction == "debit" else None
        credit = amount if direction == "credit" else None
        balance = round(balance - (debit or 0.0) + (credit or 0.0), 2)

        description = build_description(
            category, direction, profile_key, rng, variant=event.get("variant")
        )
        transactions.append(
            {
                "date": event["date"].isoformat(),
                "description": description,
                "debit": debit,
                "credit": credit,
                "balance": balance,
                "category": category,
                "direction": direction,
                "ref": _digits(rng, 8),
            }
        )

    return transactions


def _mode_from_description(description: str) -> str:
    upper = description.upper()
    for mode in ("UPI", "NEFT", "IMPS", "ATM", "POS", "ACH", "BILLPAY"):
        if mode in upper:
            return mode
    return "TXN"


def _row_for_profile(profile_key: str, transaction: dict) -> list[str]:
    date_value = transaction["date"]
    display_date = _iso_to_display(date_value)
    debit = format_inr(transaction["debit"]) if transaction["debit"] else ""
    credit = format_inr(transaction["credit"]) if transaction["credit"] else ""
    balance = format_inr(transaction["balance"])
    description = transaction["description"]

    if profile_key == "hdfc":
        return [display_date, description, transaction["ref"], display_date, debit, credit, balance]
    if profile_key == "icici":
        return [display_date, _mode_from_description(description), description, debit, credit, balance]
    return [display_date, display_date, description, transaction["ref"], debit, credit, balance]


def _iso_to_display(value: str) -> str:
    year, month, day = value.split("-")
    return f"{day}/{month}/{year}"


def _draw_page(canvas, doc, spec):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.drawString(doc.leftMargin, A4[1] - 28, f"{spec['display']} | Statement of Account")
    canvas.drawRightString(A4[0] - doc.rightMargin, 24, f"Page {canvas.getPageNumber()}")
    canvas.setStrokeColor(colors.HexColor("#E2E8F0"))
    canvas.line(doc.leftMargin, A4[1] - 34, A4[0] - doc.rightMargin, A4[1] - 34)
    canvas.restoreState()


def _build_pdf(
    output_path: Path,
    profile_key: str,
    holder: str,
    account_number: str,
    period_start: date,
    period_end: date,
    opening_balance: float,
    transactions: list[dict],
) -> None:
    spec = PROFILES[profile_key]

    bank_style = ParagraphStyle(
        "bank",
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=spec["color"],
        spaceAfter=2,
    )
    address_style = ParagraphStyle(
        "address",
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#475569"),
    )
    details_style = ParagraphStyle(
        "details",
        fontName="Helvetica",
        fontSize=8.2,
        leading=13,
        textColor=colors.HexColor("#1E293B"),
    )
    balance_style = ParagraphStyle(
        "balance",
        fontName="Helvetica",
        fontSize=8.6,
        leading=12,
        textColor=colors.HexColor("#0F172A"),
    )
    note_style = ParagraphStyle(
        "note",
        fontName="Helvetica",
        fontSize=6.5,
        leading=9,
        textColor=colors.HexColor("#64748B"),
    )

    document = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=50,
        bottomMargin=40,
        title=f"{spec['display']} Statement",
        author=spec["display"],
    )

    story = [
        Paragraph(spec["title"], bank_style),
        Paragraph(f"{spec['branch']} | IFSC {spec['ifsc']}", address_style),
        Spacer(1, 10),
        Paragraph(
            f"<b>Account Holder:</b> {holder}<br/>"
            f"<b>Account Number:</b> {account_number}<br/>"
            f"<b>IFSC Code:</b> {spec['ifsc']}<br/>"
            f"<b>Branch:</b> {spec['branch']}<br/>"
            f"<b>Statement Period:</b> {period_start:%d/%m/%Y} to {period_end:%d/%m/%Y}",
            details_style,
        ),
        Spacer(1, 8),
        Paragraph(f"<b>Opening Balance:</b> {format_inr(opening_balance)}", balance_style),
        Spacer(1, 6),
    ]

    table_data = [spec["columns"]]
    for transaction in transactions:
        table_data.append(_row_for_profile(profile_key, transaction))

    table = LongTable(table_data, colWidths=spec["widths"], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), spec["color"]),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 6.8),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 6.7),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("ALIGN", (spec["amount_start"], 1), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(table)

    closing_balance = transactions[-1]["balance"] if transactions else opening_balance
    story += [
        Spacer(1, 8),
        Paragraph(f"<b>Closing Balance:</b> {format_inr(closing_balance)}", balance_style),
        Spacer(1, 10),
        Paragraph(
            "This is a computer-generated statement for prototype and testing purposes only. "
            "No signature is required.",
            note_style,
        ),
    ]

    page_callback = partial(_draw_page, spec=spec)
    document.build(story, onFirstPage=page_callback, onLaterPages=page_callback)


def generate_statement(
    output_path: Path | str,
    profile_key: str,
    rng: random.Random,
    *,
    months: int = 3,
    density: float = 1.0,
    start_date: date | None = None,
) -> dict:
    output_path = Path(output_path)
    if profile_key not in PROFILES:
        raise ValueError(f"Unknown bank profile: {profile_key}")

    months = max(1, min(months, 12))
    spec = PROFILES[profile_key]
    holder = rng.choice(PERSON_NAMES)
    account_number = _account_number(profile_key, rng)

    if start_date is None:
        year = rng.choice([2024, 2025])
        month = rng.randint(1, max(1, 12 - months))
        start_date = date(year, month, 1)

    period_end = _add_months(start_date, months) - timedelta(days=1)
    opening_balance = round(rng.uniform(150000, 450000), 2)

    events = _schedule_events(rng, start_date, months, density)
    transactions = _materialize(events, profile_key, rng, opening_balance)
    if not transactions:
        raise RuntimeError("Synthetic generation produced no transactions")

    _build_pdf(
        output_path,
        profile_key,
        holder,
        account_number,
        start_date,
        period_end,
        opening_balance,
        transactions,
    )

    return {
        "file": output_path.name,
        "bank": spec["display"],
        "profile": profile_key,
        "pdf_type": "text",
        "account_holder": holder,
        "account_number": account_number,
        "ifsc": spec["ifsc"],
        "period_start": start_date.isoformat(),
        "period_end": period_end.isoformat(),
        "opening_balance": opening_balance,
        "closing_balance": transactions[-1]["balance"],
        "transactions": [
            {
                "date": transaction["date"],
                "description": transaction["description"],
                "debit": transaction["debit"],
                "credit": transaction["credit"],
                "balance": transaction["balance"],
                "category": transaction["category"],
            }
            for transaction in transactions
        ],
    }


def convert_to_image_pdf(source: Path | str, destination: Path | str, dpi: int = 300) -> None:
    source = Path(source)
    destination = Path(destination)
    document = fitz.open(str(source))
    try:
        images = []
        for page in document:
            pixmap = page.get_pixmap(dpi=dpi)
            images.append(Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples))
    finally:
        document.close()

    if not images:
        raise RuntimeError("Source PDF has no pages")
    images[0].save(
        str(destination),
        "PDF",
        resolution=dpi,
        save_all=True,
        append_images=images[1:],
    )
