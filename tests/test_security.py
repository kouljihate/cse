from datetime import datetime, timezone

from bson import ObjectId
from config import VERSION


def _register(client, username="owner"):
    return client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "secret123",
            "full_name": username.title(),
            "role": "admin",
        },
    )


def test_health_reports_version(client):
    data = client.get("/api/health").get_json()
    assert data["version"] == VERSION


def test_login_page_is_public(client):
    resp = client.get("/login")
    assert resp.status_code == 200
    assert "Document Manager" in resp.get_data(as_text=True)


def test_pages_require_authentication(client):
    for path in ("/dashboard", "/documents", "/users", "/requests", "/customers"):
        resp = client.get(path)
        assert resp.status_code == 302, path
        assert "/login" in resp.headers["Location"], path


def test_authenticated_page_renders(client, make_token, make_user):
    user = make_user("admin", "boss")
    client.set_cookie("access_token", make_token(user))
    assert client.get("/dashboard").status_code == 200


def test_api_requires_authentication(client):
    assert client.get("/api/users/").status_code == 401


def test_first_registration_bootstraps_admin(client):
    resp = _register(client, "owner")
    assert resp.status_code == 201
    assert resp.get_json()["role"] == "admin"


def test_registration_cannot_escalate_role(client):
    _register(client, "owner")
    resp = _register(client, "intruder")
    assert resp.status_code == 201
    assert resp.get_json()["role"] == "customer"


def test_login_issues_httponly_cookie_only(client):
    _register(client, "owner")
    resp = client.post(
        "/api/auth/login", json={"username": "owner", "password": "secret123"}
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert "access_token" not in body
    assert body["user"]["username"] == "owner"
    cookie = resp.headers["Set-Cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie


def test_logout_clears_cookie(client, make_token, make_user):
    user = make_user("admin", "boss")
    client.set_cookie("access_token", make_token(user))
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 200
    assert "access_token=;" in resp.headers["Set-Cookie"]


def test_customer_cannot_read_another_customers_document(
    client, db, make_token, make_user, tmp_path
):
    owner = make_user("customer", "alice")
    other = make_user("customer", "bob")
    admin = make_user("admin", "root")

    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    now = datetime.now(timezone.utc)
    doc_id = ObjectId()
    db.documents.insert_one(
        {
            "_id": doc_id,
            "customer_id": owner["_id"],
            "service_id": ObjectId(),
            "original_name": "doc.pdf",
            "stored_path": str(pdf),
            "file_size": pdf.stat().st_size,
            "mime_type": "application/pdf",
            "description": None,
            "uploaded_by": admin["_id"],
            "created_at": now,
            "updated_at": now,
        }
    )

    client.set_cookie("access_token", make_token(other))
    assert client.get(f"/api/documents/{doc_id}").status_code == 403
    assert client.get(f"/api/documents/{doc_id}/file").status_code == 403

    client.set_cookie("access_token", make_token(owner))
    resp = client.get(f"/api/documents/{doc_id}/file")
    assert resp.status_code == 200
    assert resp.data.startswith(b"%PDF")

    client.set_cookie("access_token", make_token(admin))
    assert client.get(f"/api/documents/{doc_id}/file").status_code == 200


def test_unknown_document_returns_404(client, make_token, make_user):
    user = make_user("admin", "root")
    client.set_cookie("access_token", make_token(user))
    assert client.get("/api/documents/not-an-id").status_code == 404
