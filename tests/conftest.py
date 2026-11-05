from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from synthetic.generator import convert_to_image_pdf, generate_statement


@pytest.fixture(scope="session")
def sample_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("samples")


@pytest.fixture(scope="session")
def text_statement(sample_dir):
    path = sample_dir / "hdfc_text.pdf"
    labels = generate_statement(path, "hdfc", random.Random(123), months=1, density=0.7)
    return path, labels


@pytest.fixture(scope="session")
def image_statement(sample_dir, text_statement):
    target = sample_dir / "hdfc_image.pdf"
    convert_to_image_pdf(text_statement[0], target, dpi=250)
    return target, text_statement[1]


@pytest.fixture(scope="session")
def model_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("models")


@pytest.fixture()
def app(tmp_path, model_dir):
    from app import create_app

    application = create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": tmp_path / "test.db",
            "UPLOAD_DIR": tmp_path / "uploads",
            "MODEL_DIR": model_dir,
        }
    )
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def engine(app):
    return app.extensions["classification_engine"]
