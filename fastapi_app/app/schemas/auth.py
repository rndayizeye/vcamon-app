from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AuthenticatedUserRead(BaseModel):
    id: str
    email: str | None = None
    role: str | None = None
    app_metadata: dict[str, Any] = Field(default_factory=dict)
    user_metadata: dict[str, Any] = Field(default_factory=dict)


class AuthStatusRead(BaseModel):
    enabled: bool
    provider: str
    environment: str
    ready: bool
    missing_configuration: list[str]
    public_paths: list[str]


class AuthPermissionsRead(BaseModel):
    can_read: bool
    can_write: bool
    can_run_analysis: bool
    can_delete_records: bool
    can_clear_map: bool
    can_delete_cases: bool
    can_manage_users: bool


class AuthSessionRead(BaseModel):
    enabled: bool
    authenticated: bool
    provider: str
    user: AuthenticatedUserRead | None = None
    permissions: AuthPermissionsRead
