"""Unit tests for local Supabase JWT verification in fastapi_app.app.auth.

These exercise verify_jwt / authenticate_access_token directly (no HTTP layer),
covering the happy path, rejection cases, and the remote userinfo fallback.
"""

from __future__ import annotations

import os
import time

import jwt
import pytest

os.environ.setdefault("DATABASE_URL", "sqlite://")

from fastapi_app.app import auth as auth_module
from fastapi_app.app.auth import (
    AuthConfigurationError,
    AuthSettings,
    authenticate_access_token,
    verify_jwt,
)

SECRET = "unit-test-jwt-secret-at-least-32-bytes!!"


def settings(*, jwt_secret: str | None = SECRET, supabase_url: str | None = None):
    return AuthSettings(
        enabled=True,
        provider="supabase",
        environment="test",
        supabase_url=supabase_url,
        supabase_key="sb_key",
        timeout_seconds=5.0,
        jwt_secret=jwt_secret,
        jwt_audience="authenticated",
    )


def make_token(
    secret: str = SECRET, *, exp_offset: int = 3600, aud="authenticated", **overrides
):
    now = int(time.time())
    claims = {
        "sub": "user-1",
        "email": "u@example.com",
        "aud": aud,
        "role": "authenticated",
        "app_metadata": {"role": "case_worker"},
        "user_metadata": {},
        "iat": now,
        "exp": now + exp_offset,
    }
    claims.update(overrides)
    return jwt.encode(claims, secret, algorithm="HS256")


def test_valid_hs256_token_returns_claims():
    claims = verify_jwt(settings(), make_token())
    assert claims is not None
    assert claims["sub"] == "user-1"
    assert claims["app_metadata"]["role"] == "case_worker"


def test_authenticate_builds_user_from_sub_claim():
    user = authenticate_access_token(make_token(), settings())
    assert user is not None
    assert user.id == "user-1"
    assert user.email == "u@example.com"
    assert user.role == "case_worker"


def test_expired_token_rejected():
    assert verify_jwt(settings(), make_token(exp_offset=-10)) is None


def test_wrong_signature_rejected():
    forged = make_token(secret="some-other-secret-32-bytes-long-aaaa")
    assert verify_jwt(settings(), forged) is None


def test_wrong_audience_rejected():
    assert verify_jwt(settings(), make_token(aud="other-audience")) is None


def test_missing_exp_rejected():
    now = int(time.time())
    token = jwt.encode(
        {"sub": "user-1", "aud": "authenticated", "iat": now},
        SECRET,
        algorithm="HS256",
    )
    assert verify_jwt(settings(), token) is None


def test_malformed_token_rejected():
    assert verify_jwt(settings(), "not-a-jwt") is None


def test_unsupported_algorithm_rejected():
    # HS512 is a valid JWT but not in the accepted algorithm set.
    now = int(time.time())
    token = jwt.encode(
        {"sub": "u", "aud": "authenticated", "exp": now + 60},
        SECRET * 2,  # HS512 wants a 64-byte key
        algorithm="HS512",
    )
    assert verify_jwt(settings(), token) is None


def test_hs256_without_secret_raises_configuration_error():
    with pytest.raises(AuthConfigurationError):
        verify_jwt(settings(jwt_secret=None), make_token())


def test_falls_back_to_remote_userinfo_when_no_local_source(monkeypatch):
    """No jwt_secret and no supabase_url → local verification disabled, remote
    userinfo path is used instead."""
    called = {}

    def fake_fetch(s, token):
        called["token"] = token
        return {
            "id": "remote-user",
            "email": "remote@example.com",
            "app_metadata": {"role": "supervisor"},
            "user_metadata": {},
        }

    monkeypatch.setattr(auth_module, "fetch_supabase_user", fake_fetch)
    cfg = settings(jwt_secret=None, supabase_url=None)
    assert cfg.local_verification_enabled is False

    user = authenticate_access_token("opaque-token", cfg)
    assert called["token"] == "opaque-token"
    assert user is not None
    assert user.id == "remote-user"
    assert user.role == "supervisor"


def test_local_verification_preferred_when_supabase_url_set(monkeypatch):
    """With supabase_url configured, the remote userinfo call is never made."""

    def boom(s, token):  # pragma: no cover - must not be called
        raise AssertionError("remote userinfo should not be called")

    monkeypatch.setattr(auth_module, "fetch_supabase_user", boom)
    cfg = settings(supabase_url="https://example.supabase.co")
    assert cfg.local_verification_enabled is True

    user = authenticate_access_token(make_token(), cfg)
    assert user is not None
    assert user.id == "user-1"
