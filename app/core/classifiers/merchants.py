from __future__ import annotations

import random
import string

CITIES = [
    "Bengaluru",
    "Mumbai",
    "Delhi",
    "Hyderabad",
    "Chennai",
    "Pune",
    "Kolkata",
    "Ahmedabad",
    "Jaipur",
    "Kochi",
]

COMPANIES = [
    "Infosys",
    "TCS",
    "Wipro",
    "Accenture",
    "Deloitte",
    "Tech Mahindra",
    "Capgemini",
    "Cognizant",
    "HCLTech",
    "LTIMindtree",
]

PERSON_NAMES = [
    "Rahul Sharma",
    "Priya Verma",
    "Amit Patel",
    "Sneha Reddy",
    "Vikram Singh",
    "Neha Gupta",
    "Arjun Nair",
    "Pooja Iyer",
    "Karan Mehta",
    "Ananya Das",
    "Rohan Joshi",
    "Ishita Rao",
]

MERCHANT_HANDLES = ["ybl", "okhdfcbank", "okicici", "paytm", "apl", "axl"]

LENDERS = [
    "HDFC Ltd",
    "ICICI Bank",
    "Bajaj Finance",
    "Tata Capital",
    "SBI Home Loan",
    "Axis Bank",
]

MONTH_LABELS = [
    "JAN 2025",
    "FEB 2025",
    "MAR 2025",
    "APR 2025",
    "MAY 2025",
    "JUN 2025",
    "JUL 2025",
    "AUG 2025",
    "SEP 2025",
]

CATEGORY_MERCHANTS: dict[str, list[str]] = {
    "Food & Dining": [
        "Swiggy",
        "Zomato",
        "Domino's",
        "KFC",
        "McDonald's",
        "Starbucks",
        "Barbeque Nation",
        "Haldiram's",
        "Third Wave Coffee",
        "Rebel Foods",
        "Burger King",
        "Pizza Hut",
        "Subway",
    ],
    "Groceries": [
        "BigBasket",
        "Blinkit",
        "Zepto",
        "DMart",
        "Reliance Fresh",
        "More Supermarket",
        "Licious",
        "Country Delight",
        "Grofers",
        "Instamart",
    ],
    "Shopping": [
        "Amazon",
        "Flipkart",
        "Myntra",
        "Ajio",
        "Nykaa",
        "Tata CLiQ",
        "Croma",
        "Decathlon",
        "Meesho",
        "Snapdeal",
    ],
    "Transport": [
        "Uber",
        "Ola",
        "Rapido",
        "Namma Metro",
        "Delhi Metro",
        "IndianOil",
        "HP Petrol Pump",
        "Shell",
        "FASTag",
        "BluSmart",
    ],
    "Travel": [
        "IRCTC",
        "MakeMyTrip",
        "Cleartrip",
        "Goibibo",
        "IndiGo",
        "Air India",
        "RedBus",
        "OYO",
        "Taj Hotels",
    ],
    "Utilities & Bills": [
        "Airtel",
        "Jio",
        "Vi",
        "BESCOM",
        "Tata Power",
        "Adani Electricity",
        "Mahanagar Gas",
        "ACT Fibernet",
        "JioFiber",
        "BWSSB",
    ],
    "Rent & Housing": [],
    "EMI & Loans": [],
    "Salary & Income": [],
    "Transfers": [],
    "Cash & ATM": [],
    "Entertainment & Subscriptions": [
        "Netflix",
        "Spotify",
        "Amazon Prime",
        "Disney+ Hotstar",
        "YouTube Premium",
        "BookMyShow",
        "PVR",
        "INOX",
        "Gaana",
    ],
    "Healthcare": [
        "Apollo Pharmacy",
        "PharmEasy",
        "1mg",
        "Practo",
        "Fortis Hospital",
        "Manipal Hospital",
        "Max Healthcare",
        "Netmeds",
    ],
    "Education": [
        "Udemy",
        "Coursera",
        "Byju's",
        "Unacademy",
        "Vedantu",
        "School Fees",
        "College Fees",
    ],
    "Fees & Charges": [],
}


def _ref(rng: random.Random, length: int = 8) -> str:
    return "".join(rng.choices(string.digits, k=length))


def build_description(
    category: str,
    direction: str,
    style: str,
    rng: random.Random,
    variant: str | None = None,
) -> str:
    city = rng.choice(CITIES).upper()
    ref = _ref(rng)
    month = rng.choice(MONTH_LABELS)

    if category == "Salary & Income":
        subtype = variant or rng.choice(
            ["salary", "salary", "salary", "interest", "dividend", "cashback", "refund"]
        )
        if subtype == "salary":
            company = rng.choice(COMPANIES).upper()
            options = [
                f"NEFT CR-{company}-SALARY {month}-{ref}",
                f"SALARY CREDIT-{company}-{month}",
                f"BY SALARY/{company}/{month}/{ref}",
                f"PAYROLL CREDIT {company} {month}",
                f"SAL CR {company} {month} {ref}",
            ]
        elif subtype == "interest":
            options = [
                f"CREDIT INTEREST {month}",
                f"INTEREST CREDITED-{ref}",
                f"INT.CR-{month}-{ref}",
            ]
        elif subtype == "dividend":
            options = [f"DIVIDEND-{rng.choice(COMPANIES).upper()}-{ref}"]
        elif subtype == "cashback":
            options = [f"CASHBACK CREDIT-{ref}", f"REWARD CREDIT-{ref}"]
        else:
            merchant = rng.choice(
                CATEGORY_MERCHANTS["Shopping"] + CATEGORY_MERCHANTS["Food & Dining"]
            ).upper()
            options = [f"REFUND-{merchant}-{ref}", f"REVERSAL-{merchant}-{ref}"]
        return rng.choice(options)

    if category == "Transfers":
        person = rng.choice(PERSON_NAMES).upper()
        handle = rng.choice(MERCHANT_HANDLES)
        if direction == "credit":
            options = [
                f"UPI/CR/{ref}/{person}/{handle}",
                f"NEFT CR-{person}-{ref}",
                f"IMPS/P2A/{ref}/{person}",
                f"TRANSFER TO {person} {ref}",
            ]
        else:
            options = [
                f"UPI/DR/{ref}/{person}/{handle}",
                f"NEFT DR-{person}-{ref}",
                f"IMPS/P2A/{ref}/{person}",
                f"TRANSFER TO {person} {ref}",
            ]
        return rng.choice(options)

    if category == "Rent & Housing":
        landlord = rng.choice(PERSON_NAMES).upper()
        options = [
            f"NEFT DR-{landlord}-RENT {month}-{ref}",
            f"UPI/{landlord}/RENT/{ref}",
            f"RENT PAYMENT-{landlord}-{ref}",
            f"HOUSE RENT {landlord} {month}",
        ]
        return rng.choice(options)

    if category == "EMI & Loans":
        lender = rng.choice(LENDERS).upper()
        options = [
            f"ACH DR-{lender}-EMI-{ref}",
            f"EMI {lender} {ref}",
            f"LOAN EMI/{lender}/{ref}",
            f"{lender} HOME LOAN EMI {ref}",
        ]
        return rng.choice(options)

    if category == "Cash & ATM":
        options = [
            f"ATM CASH WDL {city} {ref}",
            f"ATM/CASH WDL/{city}/{ref}",
            f"CASH WITHDRAWAL {city}",
        ]
        return rng.choice(options)

    if category == "Fees & Charges":
        options = [
            "SMS ALERT FEE",
            "ANNUAL FEE",
            "MINIMUM BALANCE CHARGE",
            "GST ON CHARGES",
            "PROCESSING FEE",
            "LATE PAYMENT PENALTY",
            "SERVICE CHARGE",
            "SMS CHARGES",
        ]
        return f"{rng.choice(options)} {ref}"

    merchant = rng.choice(CATEGORY_MERCHANTS[category]).upper()
    handle = rng.choice(MERCHANT_HANDLES)
    if style == "hdfc":
        options = [
            f"UPI-DR-{ref}-{merchant}-{handle}",
            f"POS/{ref}/{merchant}/{city}",
            f"UPI-{merchant}-{handle}-{ref}",
        ]
    elif style == "icici":
        options = [
            f"UPI/{merchant}/{ref}",
            f"POS {merchant} {city}",
            f"BILLPAY {merchant} {ref}",
        ]
    else:
        options = [
            f"UPI/DR/{ref}/{merchant}/{handle}",
            f"POS/{merchant}/{city}/{ref}",
            f"UPI/{merchant}/{ref}",
        ]
    return rng.choice(options)


def training_directions(category: str) -> list[str]:
    if category == "Salary & Income":
        return ["credit"]
    if category == "Transfers":
        return ["credit", "debit"]
    return ["debit"]


def iter_training_examples(seed: int = 7, per_style: int = 20):
    rng = random.Random(seed)
    for category in CATEGORY_MERCHANTS:
        for direction in training_directions(category):
            for style in ("hdfc", "icici", "sbi"):
                for _ in range(per_style):
                    yield build_description(category, direction, style, rng), direction, category
