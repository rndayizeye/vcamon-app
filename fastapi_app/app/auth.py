from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from urllib import error, request

from fastapi import HTTPException, Request, status


@dataclass(frozen=True)
class AuthSettings:
    enabled: bool
    provider: str
    environment: str
    supabase_url: str | None
    supabase_key: str | None
    timeout_seconds: float

    @property
    def ready(self) -> bool:
        if not self.enabled:
            return True
        return bool(self.supabase_url and self.supabase_key)

    @property
    def missing_configuration(self) -> list[str]:
        if not self.enabled:
            return []
        missing: list[str] = []
        if not self.supabase_url:
            missing.append("SUPABASE_URL")
        if not self.supabase_key:
            missing.append("SUPABASE_ANON_KEY or SUPABASE_PUBLISHABLE_KEY")
        return missing


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    email: str | None
    role: str | None
    app_metadata: dict[str, Any]
    user_metadata: dict[str, Any]
    raw_user: dict[str, Any]


OPERATOR_ROLES = ("authenticated", "case_worker", "supervisor")
SUPERVISOR_ROLES = ("supervisor",)


class AuthConfigurationError(RuntimeError):
    pass


class AuthServiceError(RuntimeError):
    pass


_PUBLIC_PATHS = {
    "/",
    "/health",
    "/api",
    "/api/",
    "/api/auth/status",
    "/openapi.json",
}

_PUBLIC_PREFIXES = (
    "/docs",
    "/redoc",
)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@lru_cache
def get_auth_settings() -> AuthSettings:
    return AuthSettings(
        enabled=(_env_bool("AUTH_ENABLED") or _env_bool("SUPABASE_AUTH_ENABLED")),
        provider="supabase",
        environment=os.getenv("APP_ENV", "development"),
        supabase_url=(os.getenv("SUPABASE_URL") or "").rstrip("/") or None,
        supabase_key=(
            os.getenv("SUPABASE_PUBLISHABLE_KEY")
            or os.getenv("SUPABASE_ANON_KEY")
            or os.getenv("SUPABASE_KEY")
            or None
        ),
        timeout_seconds=float(os.getenv("SUPABASE_AUTH_TIMEOUT_SECONDS", "5")),
    )


def clear_auth_settings_cache() -> None:
    get_auth_settings.cache_clear()


def is_public_path(path: str) -> bool:
    if path in _PUBLIC_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in _PUBLIC_PREFIXES)


def get_public_paths() -> list[str]:
    return sorted(_PUBLIC_PATHS | set(_PUBLIC_PREFIXES))


def extract_bearer_token(authorization_header: str | None) -> str | None:
    if not authorization_header:
        return None
    scheme, _, token = authorization_header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def _extract_role(user_payload: dict[str, Any]) -> str | None:
    app_metadata = user_payload.get("app_metadata") or {}
    user_metadata = user_payload.get("user_metadata") or {}

    if isinstance(app_metadata, dict) and isinstance(app_metadata.get("role"), str):
        return app_metadata["role"]
    if isinstance(user_metadata, dict) and isinstance(user_metadata.get("role"), str):
        return user_metadata["role"]
    role = user_payload.get("role")
    return role if isinstance(role, str) else None


def fetch_supabase_user(
    settings: AuthSettings, access_token: str
) -> dict[str, Any] | None:
    if not settings.ready:
        raise AuthConfigurationError(
            "Supabase auth is enabled but required configuration is missing: "
            + ", ".join(settings.missing_configuration)
        )

    url = f"{settings.supabase_url}/auth/v1/user"
    req = request.Request(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "apikey": settings.supabase_key or "",
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with request.urlopen(req, timeout=settings.timeout_seconds) as response:
            payload = response.read().decode("utf-8")
    except error.HTTPError as exc:
        if exc.code in {401, 403}:
            return None
        detail = exc.read().decode("utf-8", errors="ignore").strip()
        raise AuthServiceError(
            f"Supabase auth request failed with status {exc.code}"
            + (f": {detail}" if detail else "")
        ) from exc
    except error.URLError as exc:
        raise AuthServiceError(
            f"Unable to reach Supabase auth service: {exc.reason}"
        ) from exc

    try:
        user_payload = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise AuthServiceError("Supabase auth returned invalid JSON") from exc

    if not isinstance(user_payload, dict):
        raise AuthServiceError("Supabase auth returned an unexpected payload")

    return user_payload


def authenticate_access_token(
    access_token: str, settings: AuthSettings | None = None
) -> AuthenticatedUser | None:
    resolved_settings = settings or get_auth_settings()
    user_payload = fetch_supabase_user(resolved_settings, access_token)
    if not user_payload:
        return None

    user_id = user_payload.get("id")
    if not isinstance(user_id, str) or not user_id:
        raise AuthServiceError("Supabase auth payload is missing a valid user id")

    app_metadata = user_payload.get("app_metadata")
    user_metadata = user_payload.get("user_metadata")

    return AuthenticatedUser(
        id=user_id,
        email=user_payload.get("email")
        if isinstance(user_payload.get("email"), str)
        else None,
        role=_extract_role(user_payload),
        app_metadata=app_metadata if isinstance(app_metadata, dict) else {},
        user_metadata=user_metadata if isinstance(user_metadata, dict) else {},
        raw_user=user_payload,
    )


def get_request_user(request: Request) -> AuthenticatedUser | None:
    user = getattr(request.state, "auth_user", None)
    return user if isinstance(user, AuthenticatedUser) else None


def get_effective_role(user: AuthenticatedUser | None) -> str | None:
    return user.role if user and user.role else None


def build_permission_flags(role: str | None) -> dict[str, bool]:
    normalized_role = role or "unauthenticated"
    is_operator = normalized_role in OPERATOR_ROLES
    is_supervisor = normalized_role in SUPERVISOR_ROLES

    return {
        "can_read": is_operator,
        "can_write": is_operator,
        "can_run_analysis": is_operator,
        "can_delete_records": is_supervisor,
        "can_clear_map": is_supervisor,
        "can_delete_cases": is_supervisor,
        "can_manage_users": is_supervisor,
    }


def require_roles(*roles: str):
    allowed_roles = {role for role in roles if role}

    def dependency(request: Request) -> AuthenticatedUser | None:
        settings = get_auth_settings()
        user = get_request_user(request)

        if not settings.enabled:
            return user
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if allowed_roles and user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Insufficient role. Required one of: "
                    + ", ".join(sorted(allowed_roles))
                ),
            )
        return user

    return dependency
