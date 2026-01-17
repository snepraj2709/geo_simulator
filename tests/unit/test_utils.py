"""Tests for utility modules."""

import pytest

from shared.utils.hashing import hash_password, hash_url, verify_password
from shared.utils.jwt import create_access_token, create_refresh_token, decode_token


class TestHashing:
    """Test hashing utilities."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "testpassword123"
        hashed = hash_password(password)

        assert hashed != password
        assert hashed.startswith("$2b$")

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "testpassword123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "testpassword123"
        hashed = hash_password(password)

        assert verify_password("wrongpassword", hashed) is False

    def test_hash_url(self):
        """Test URL hashing."""
        url = "https://example.com/page"
        hashed = hash_url(url)

        assert len(hashed) == 64  # SHA-256 hex length
        assert hashed == hash_url(url)  # Deterministic


class TestJWT:
    """Test JWT utilities."""

    def test_create_access_token(self):
        """Test access token creation."""
        data = {"sub": "user123"}
        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        data = {"sub": "user123"}
        token = create_refresh_token(data)

        assert token is not None
        assert isinstance(token, str)

    def test_decode_access_token(self):
        """Test access token decoding."""
        data = {"sub": "user123"}
        token = create_access_token(data)

        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["type"] == "access"

    def test_decode_refresh_token(self):
        """Test refresh token decoding."""
        data = {"sub": "user123"}
        token = create_refresh_token(data)

        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["type"] == "refresh"

    def test_decode_invalid_token(self):
        """Test decoding invalid token returns None."""
        payload = decode_token("invalid.token.here")
        assert payload is None
