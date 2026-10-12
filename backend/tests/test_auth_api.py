import pytest
import jwt
import time
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from main import app
from routers.auth import JWT_SECRET, JWT_ALGORITHM
import db

client = TestClient(app)


def test_auth_registration_valid_details():
    """1. Registration with valid details succeeds and returns user + JWT token."""
    res = client.post("/api/auth/signup", json={
        "name": "Jane Doe",
        "email": "jane.doe@example.com",
        "password": "securepassword123"
    })
    assert res.status_code == 200, res.text
    data = res.json()
    assert "user" in data
    assert data["user"]["email"] == "jane.doe@example.com"
    assert data["user"]["name"] == "Jane Doe"
    assert "id" in data["user"]
    assert "token" in data
    # Token should be a valid JWT
    payload = jwt.decode(data["token"], JWT_SECRET, algorithms=[JWT_ALGORITHM])
    assert payload["sub"] == data["user"]["id"]
    assert payload["email"] == "jane.doe@example.com"


def test_auth_registration_existing_email():
    """2. Registration with an existing email is rejected with 400."""
    res = client.post("/api/auth/signup", json={
        "name": "Duplicate Jane",
        "email": "jane.doe@example.com",
        "password": "anotherpassword"
    })
    assert res.status_code == 400
    assert "already exists" in res.json().get("detail", "").lower()


def test_auth_registration_invalid_fields():
    """3. Registration with invalid fields (short name, invalid email, short password) fails."""
    # Invalid email format
    res1 = client.post("/api/auth/signup", json={
        "name": "Valid Name",
        "email": "not-an-email",
        "password": "validpassword"
    })
    assert res1.status_code in (400, 422)

    # Password too short (< 4 chars)
    res2 = client.post("/api/auth/signup", json={
        "name": "Valid Name",
        "email": "valid.email@example.com",
        "password": "12"
    })
    assert res2.status_code == 400
    assert "at least 4 characters" in res2.json().get("detail", "")

    # Name too short
    res3 = client.post("/api/auth/signup", json={
        "name": "A",
        "email": "valid.name@example.com",
        "password": "validpassword"
    })
    assert res3.status_code == 400
    assert "at least 2 characters" in res3.json().get("detail", "")


def test_auth_login_valid_credentials():
    """4. Login with valid credentials succeeds and returns token."""
    res = client.post("/api/auth/login", json={
        "email": "jane.doe@example.com",
        "password": "securepassword123"
    })
    assert res.status_code == 200
    data = res.json()
    assert "token" in data
    assert data["user"]["email"] == "jane.doe@example.com"


def test_auth_login_incorrect_password():
    """5. Login with an incorrect password returns 401."""
    res = client.post("/api/auth/login", json={
        "email": "jane.doe@example.com",
        "password": "wrongpassword999"
    })
    assert res.status_code == 401
    assert "invalid email or password" in res.json().get("detail", "").lower()


def test_auth_login_nonexistent_user():
    """6. Login for a nonexistent user returns 401."""
    res = client.post("/api/auth/login", json={
        "email": "nobody_exists_here_999@example.com",
        "password": "somepassword"
    })
    assert res.status_code == 401
    assert "invalid email or password" in res.json().get("detail", "").lower()


def test_authenticated_api_access():
    """7. Authenticated access to /api/auth/me succeeds with Bearer token and X-User-Id."""
    # First login to obtain token
    login_res = client.post("/api/auth/login", json={
        "email": "jane.doe@example.com",
        "password": "securepassword123"
    })
    token = login_res.json()["token"]
    user_id = login_res.json()["user"]["id"]

    # Access via Authorization Bearer token
    res1 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res1.status_code == 200
    assert res1.json()["user"]["id"] == user_id

    # Access via X-User-Id header
    res2 = client.get("/api/auth/me", headers={"X-User-Id": user_id})
    assert res2.status_code == 200
    assert res2.json()["user"]["id"] == user_id


def test_invalid_or_expired_token():
    """8. Expired or invalid tokens return 401."""
    # Malformed token
    res_malformed = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-valid-token"})
    assert res_malformed.status_code == 401

    # Expired token
    expired_payload = {
        "sub": "user-12345",
        "email": "test@example.com",
        "exp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())
    }
    expired_token = jwt.encode(expired_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    res_expired = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res_expired.status_code == 401

    # No credentials
    res_empty = client.get("/api/auth/me")
    assert res_empty.status_code == 401


def test_cors_options_preflight():
    """9. Preflight OPTIONS request from production Vercel domain succeeds with 200."""
    res = client.options("/api/auth/login", headers={
        "Origin": "https://insure-wise-ai.vercel.app",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type"
    })
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "https://insure-wise-ai.vercel.app"
