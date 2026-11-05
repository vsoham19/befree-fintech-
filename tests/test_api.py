import io

import fitz


def _upload(client, path, name="statement.pdf"):
    with open(path, "rb") as handle:
        data = {"file": (io.BytesIO(handle.read()), name)}
    return client.post("/api/statements", data=data, content_type="multipart/form-data")


def test_upload_list_detail_and_patch(client, text_statement):
    path, labels = text_statement
    response = _upload(client, path)
    assert response.status_code == 201, response.get_data(as_text=True)

    payload = response.get_json()
    assert payload["errors"] == []
    statement = payload["statements"][0]
    assert statement["status"] == "processed"
    assert statement["bank"] == labels["bank"]
    assert statement["summary"]["transaction_count"] == len(labels["transactions"])
    assert len(statement["transactions"]) == len(labels["transactions"])

    statement_id = statement["id"]
    listing = client.get("/api/statements").get_json()
    assert listing["count"] == 1
    assert listing["items"][0]["id"] == statement_id

    detail = client.get(f"/api/statements/{statement_id}").get_json()
    assert detail["account"]["holder"] == labels["account_holder"]
    assert detail["account"]["ifsc"] == labels["ifsc"]

    transaction_id = detail["transactions"][0]["id"]
    patched = client.patch(
        f"/api/transactions/{transaction_id}", json={"category": "Shopping"}
    )
    assert patched.status_code == 200
    updated = patched.get_json()["transaction"]
    assert updated["category"] == "Shopping"
    assert updated["source"] == "user"
    assert updated["needs_review"] is False

    invalid = client.patch(
        f"/api/transactions/{transaction_id}", json={"category": "Not A Category"}
    )
    assert invalid.status_code == 422


def test_duplicate_upload_is_detected(client, text_statement):
    path, _ = text_statement
    first = _upload(client, path)
    assert first.status_code == 201

    second = _upload(client, path, name="copy.pdf")
    assert second.status_code == 201
    duplicate = second.get_json()["statements"][0]
    assert duplicate["duplicate"] is True


def test_exports(client, text_statement):
    path, _ = text_statement
    statement = _upload(client, path).get_json()["statements"][0]
    statement_id = statement["id"]

    csv_response = client.get(f"/api/statements/{statement_id}/export?format=csv")
    assert csv_response.status_code == 200
    assert "text/csv" in csv_response.content_type
    assert b"Description" in csv_response.data
    assert b"Category" in csv_response.data

    xlsx_response = client.get(f"/api/statements/{statement_id}/export?format=xlsx")
    assert xlsx_response.status_code == 200
    assert xlsx_response.data[:2] == b"PK"

    bad_format = client.get(f"/api/statements/{statement_id}/export?format=pdf")
    assert bad_format.status_code == 400


def test_invalid_file_type(client, tmp_path):
    sample = tmp_path / "notes.txt"
    sample.write_text("not a pdf", encoding="utf-8")
    response = _upload(client, sample, name="notes.txt")
    assert response.status_code == 422
    assert response.get_json()["errors"][0]["code"] == "unsupported_file_type"


def test_encrypted_pdf_is_rejected(client, text_statement, tmp_path):
    encrypted = tmp_path / "locked.pdf"
    document = fitz.open(str(text_statement[0]))
    try:
        document.save(
            str(encrypted),
            encryption=fitz.PDF_ENCRYPT_AES_256,
            owner_pw="owner",
            user_pw="secret",
        )
    finally:
        document.close()

    response = _upload(client, encrypted, name="locked.pdf")
    assert response.status_code == 422
    assert response.get_json()["errors"][0]["code"] == "pdf_encrypted"


def test_stats_and_categories(client, text_statement):
    _upload(client, text_statement[0])
    stats = client.get("/api/stats").get_json()
    assert stats["total_statements"] == 1
    assert stats["total_transactions"] > 0
    assert 0.0 <= stats["classification_rate"] <= 1.0

    categories = client.get("/api/categories").get_json()["categories"]
    assert any(category["name"] == "Food & Dining" for category in categories)
