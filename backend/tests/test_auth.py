"""Tests for authentication module."""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.auth import create_access_token, decode_access_token
from app.main import app


class TestAuthFunctions:
    """Test authentication utility functions."""

    def test_create_access_token(self):
        """Test access token creation."""
        token = create_access_token("test_user")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_claims(self):
        """Test access token creation with extra claims."""
        extra_claims = {"tenant_id": "test_tenant", "roles": ["admin", "user"]}
        token = create_access_token("test_user", extra_claims)
        assert isinstance(token, str)

        # Decode and verify claims
        payload = decode_access_token(token)
        assert payload["sub"] == "test_user"
        assert payload["tenant_id"] == "test_tenant"
        assert payload["roles"] == ["admin", "user"]

    def test_decode_access_token_valid(self):
        """Test decoding valid access token."""
        token = create_access_token("test_user")
        payload = decode_access_token(token)
        assert payload["sub"] == "test_user"

    def test_decode_access_token_invalid(self):
        """Test decoding invalid access token."""
        with pytest.raises(HTTPException):  # HTTPException from FastAPI
            decode_access_token("invalid_token")


class TestAuthEndpoints:
    """Test authentication API endpoints."""

    def test_login_success(self):
        """Test successful login."""
        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/login", data={"username": "test_user", "password": "admin"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_password(self):
        """Test login with invalid password."""
        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/login", data={"username": "test_user", "password": "wrong_password"}
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid credentials"

    def test_me_endpoint_with_valid_token(self):
        """Test /me endpoint with valid token."""
        client = TestClient(app)

        # First login to get token
        login_response = client.post(
            "/api/v1/auth/login", data={"username": "test_user", "password": "admin"}
        )
        token = login_response.json()["access_token"]

        # Use token to access /me endpoint
        response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "tenant_id" in data
        assert "roles" in data

    def test_expired_token(self):
        client = TestClient(app)
        # Create an already-expired token by overriding expiry
        import jwt
        from datetime import datetime, UTC, timedelta
        from app.core.config import settings
        payload = {
            "sub": "u1",
            "tenant_id": "t1",
            "roles": ["user"],
            "exp": datetime.now(UTC) - timedelta(seconds=1),
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
        res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 401

    def test_invalid_signature(self):
        client = TestClient(app)
        # Create token signed with wrong key
        import jwt
        from datetime import datetime, UTC, timedelta
        payload = {
            "sub": "u1",
            "tenant_id": "t1",
            "roles": ["user"],
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        }
        token = jwt.encode(payload, "wrong-secret", algorithm="HS256")
        res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 401

    def test_me_endpoint_without_token(self):
        """Test /me endpoint without token."""
        client = TestClient(app)
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_me_endpoint_with_invalid_token(self):
        """Test /me endpoint with invalid token."""
        client = TestClient(app)
        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid_token"})
        assert response.status_code == 401
