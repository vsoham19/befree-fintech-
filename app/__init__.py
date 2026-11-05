from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, url_for
from werkzeug.exceptions import HTTPException

from .api import api_bp
from .config import Config
from .core.classifiers.pipeline import ClassificationEngine
from .db import Database
from .errors import ApiError


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    Path(app.config["UPLOAD_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["MODEL_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["DATABASE_PATH"]).parent.mkdir(parents=True, exist_ok=True)

    database = Database(app.config["DATABASE_PATH"])
    database.init()
    app.extensions["db"] = database

    engine = ClassificationEngine(
        rules_path=app.config["RULES_PATH"],
        model_path=Path(app.config["MODEL_DIR"]) / "classifier.joblib",
        categories_path=app.config["CATEGORIES_PATH"],
    )
    app.extensions["classification_engine"] = engine
    app.extensions["categories"] = engine.categories

    app.register_blueprint(api_bp)

    @app.after_request
    def add_cors_headers(response):
        origins = app.config.get("CORS_ORIGINS", "*")
        response.headers.setdefault("Access-Control-Allow-Origin", origins)
        response.headers.setdefault(
            "Access-Control-Allow-Headers", "Content-Type, Authorization"
        )
        response.headers.setdefault(
            "Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS"
        )
        response.headers.setdefault("Access-Control-Expose-Headers", "Content-Disposition")
        return response

    @app.get("/")
    def index():
        template_path = Path(app.root_path) / (app.template_folder or "templates") / "dashboard.html"
        if template_path.exists():
            return render_template("dashboard.html")
        return jsonify(
            {
                "name": "StatementIQ API",
                "status": "ok",
                "message": "Backend is running. Add dashboard.html to app/templates.",
                "endpoints": [
                    "/api/health",
                    "/api/statements",
                    "/api/stats",
                    "/api/categories",
                ],
            }
        )

    @app.get("/upload")
    def upload_page():
        return render_template("upload.html")

    @app.get("/statements/<statement_id>")
    def review_page(statement_id: str):
        row = app.extensions["db"].get_statement(statement_id)
        if not row:
            return redirect(url_for("index"))
        return render_template(
            "review.html",
            statement_id=statement_id,
            active_nav="transactions",
            page_title="StatementIQ · Statement Review",
        )

    @app.get("/transactions")
    def transactions_page():
        database = app.extensions["db"]
        statement_id = request.args.get("statement_id")
        if statement_id:
            row = database.get_statement(statement_id)
            if row and row.get("status") == "processed":
                return render_template(
                    "review.html",
                    statement_id=statement_id,
                    active_nav="transactions",
                    page_title="StatementIQ · Transactions",
                )
        rows = database.list_statements(status="processed", limit=1)
        if rows:
            return render_template(
                "review.html",
                statement_id=rows[0]["id"],
                active_nav="transactions",
                page_title="StatementIQ · Transactions",
            )
        return redirect(url_for("upload_page"))

    @app.get("/categories")
    def categories_page():
        return render_template("categories.html")

    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError):
        return (
            jsonify(
                {
                    "error": {
                        "code": error.code,
                        "message": error.message,
                        "details": error.details,
                    }
                }
            ),
            error.status_code,
        )

    @app.errorhandler(413)
    def handle_too_large(_error):
        return (
            jsonify(
                {
                    "error": {
                        "code": "file_too_large",
                        "message": "Uploaded file exceeds the maximum allowed size.",
                        "details": {"max_bytes": app.config["MAX_CONTENT_LENGTH"]},
                    }
                }
            ),
            413,
        )

    @app.errorhandler(Exception)
    def handle_unexpected(error):
        if isinstance(error, HTTPException):
            return (
                jsonify(
                    {
                        "error": {
                            "code": (error.name or "http_error").lower().replace(" ", "_"),
                            "message": error.description,
                        }
                    }
                ),
                error.code or 500,
            )
        app.logger.exception("Unhandled error")
        return (
            jsonify(
                {
                    "error": {
                        "code": "internal_error",
                        "message": "An unexpected error occurred.",
                    }
                }
            ),
            500,
        )

    return app
