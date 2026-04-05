"""Tests for authentication endpoints."""
import uuid
import pytest


def unique_user():
    return f"user_{uuid.uuid4().hex[:8]}"


class TestRegister:
    def test_register_success(self, client):
        resp = client.post("/api/auth/register", json={"username": unique_user(), "password": "password123"})
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user_id" in data
        assert "username" in data

    def test_register_creates_default_board(self, client, auth_headers):
        resp = client.get("/api/boards", headers=auth_headers)
        assert resp.status_code == 200
        boards = resp.json()
        assert len(boards) >= 1

    def test_register_duplicate_username(self, client):
        uname = unique_user()
        client.post("/api/auth/register", json={"username": uname, "password": "password123"})
        resp = client.post("/api/auth/register", json={"username": uname, "password": "other123"})
        assert resp.status_code == 409

    def test_register_short_username(self, client):
        resp = client.post("/api/auth/register", json={"username": "ab", "password": "password123"})
        assert resp.status_code == 400

    def test_register_short_password(self, client):
        resp = client.post("/api/auth/register", json={"username": unique_user(), "password": "12345"})
        assert resp.status_code == 400


class TestLogin:
    def test_login_success(self, client):
        uname = unique_user()
        client.post("/api/auth/register", json={"username": uname, "password": "password123"})
        resp = client.post("/api/auth/login", json={"username": uname, "password": "password123"})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password(self, client):
        uname = unique_user()
        client.post("/api/auth/register", json={"username": uname, "password": "password123"})
        resp = client.post("/api/auth/login", json={"username": uname, "password": "wrongpass"})
        assert resp.status_code == 401

    def test_login_unknown_user(self, client):
        resp = client.post("/api/auth/login", json={"username": "nobody_here", "password": "pass"})
        assert resp.status_code == 401

    def test_seeded_user_login(self, client):
        """The seed user (user/password) should be able to log in."""
        resp = client.post("/api/auth/login", json={"username": "user", "password": "password"})
        assert resp.status_code == 200


class TestMe:
    def test_me_returns_profile(self, client, auth_headers):
        resp = client.get("/api/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "username" in data

    def test_me_unauthenticated(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code in (401, 403)

    def test_me_bad_token(self, client):
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert resp.status_code == 401


class TestChangePassword:
    def test_change_password(self, client):
        uname = unique_user()
        client.post("/api/auth/register", json={"username": uname, "password": "oldpass123"})
        login = client.post("/api/auth/login", json={"username": uname, "password": "oldpass123"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.put(
            "/api/auth/password",
            json={"current_password": "oldpass123", "new_password": "newpass456"},
            headers=headers,
        )
        assert resp.status_code == 200

        # Old password should no longer work
        assert client.post("/api/auth/login", json={"username": uname, "password": "oldpass123"}).status_code == 401
        # New password should work
        assert client.post("/api/auth/login", json={"username": uname, "password": "newpass456"}).status_code == 200

    def test_change_password_wrong_current(self, client, auth_headers):
        resp = client.put(
            "/api/auth/password",
            json={"current_password": "wrongcurrent", "new_password": "newpass456"},
            headers=auth_headers,
        )
        assert resp.status_code == 401
