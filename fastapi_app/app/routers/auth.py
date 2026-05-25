from __future__ import annotations

from fastapi import APIRouter, Request

from fastapi_app.app.auth import (
    build_permission_flags,
    get_auth_settings,
    get_effective_role,
    get_public_paths,
    get_request_user,
)
from fastapi_app.app.schemas import (
    AuthenticatedUserRead,
    AuthPermissionsRead,
    AuthSessionRead,
    AuthStatusRead,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/status", response_model=AuthStatusRead)
def auth_status():
    settings = get_auth_settings()
    return AuthStatusRead(
        enabled=settings.enabled,
        provider=settings.provider,
        environment=settings.environment,
        ready=settings.ready,
        missing_configuration=settings.missing_configuration,
        public_paths=get_public_paths(),
    )


@router.get("/me", response_model=AuthSessionRead)
def auth_me(request: Request):
    settings = get_auth_settings()
    user = get_request_user(request)

    serialized_user = None
    if user:
        serialized_user = AuthenticatedUserRead(
            id=user.id,
            email=user.email,
            role=user.role,
            app_metadata=user.app_metadata,
            user_metadata=user.user_metadata,
        )

    return AuthSessionRead(
        enabled=settings.enabled,
        authenticated=user is not None,
        provider=settings.provider,
        user=serialized_user,
        permissions=AuthPermissionsRead(
            **build_permission_flags(get_effective_role(user))
        ),
    )


@router.get("/permissions", response_model=AuthPermissionsRead)
def auth_permissions(request: Request):
    return AuthPermissionsRead(
        **build_permission_flags(get_effective_role(get_request_user(request)))
    )
