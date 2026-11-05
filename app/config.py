import os
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def _find_tesseract() -> str | None:
    candidates: list[str | None] = [os.getenv("TESSERACT_CMD"), shutil.which("tesseract")]
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    candidates += [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        str(Path(local_appdata) / "Programs" / "Tesseract-OCR" / "tesseract.exe") if local_appdata else None,
        str(Path(local_appdata) / "Tesseract-OCR" / "tesseract.exe") if local_appdata else None,
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
        "/opt/homebrew/bin/tesseract",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    return None


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "befree-dev-secret")
    DATA_DIR = DATA_DIR
    DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(DATA_DIR / "app.db")))
    UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(DATA_DIR / "uploads")))
    MODEL_DIR = Path(os.getenv("MODEL_DIR", str(DATA_DIR / "models")))
    CATEGORIES_PATH = DATA_DIR / "categories.json"
    RULES_PATH = DATA_DIR / "rules.json"
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_MB", "20")) * 1024 * 1024
    TESSERACT_CMD = os.getenv("TESSERACT_CMD") or _find_tesseract()
    OCR_DPI = int(os.getenv("OCR_DPI", "300"))
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
