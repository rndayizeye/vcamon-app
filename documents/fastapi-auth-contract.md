# FastAPI Auth Contract

This document describes how the frontend should authenticate to the FastAPI backend
and how to interpret the current role/permission scaffold.

See also:
- `documents/react-auth-bootstrap-example.md`

## Auth model

- Identity provider: **Supabase Auth**
- Backend auth mode: **Bearer token validation against Supabase**
- Required request header for protected routes:

```http
Authorization: Bearer <supabase_access_token>
```

When `AUTH_ENABLED=false`, the backend runs without bearer-token enforcement.
When `AUTH_ENABLED=true`, most `/api/*` routes require a valid Supabase access token.

## Public routes

These routes remain public even when auth is enabled:

- `GET /`
- `GET /health`
- `GET /api`
- `GET /api/auth/status`
- `/docs`
- `/redoc`
- `/openapi.json`

Browser `OPTIONS` preflight requests also bypass auth so CORS-authenticated
frontend calls can complete normally.

## Frontend bootstrap flow

Recommended client startup sequence:

1. Sign in with Supabase on the client.
2. Read the current access token from the Supabase session.
3. Send that token in the `Authorization` header for API calls.
4. Call `GET /api/auth/me` after app bootstrap.
5. Use the returned `permissions` object to show/hide destructive UI actions.

## Auth endpoints

### `GET /api/auth/status`

Purpose:
- Detect whether backend auth is enabled.
- Check whether the backend has the env vars required to validate tokens.

Example response:

```json
{
  "enabled": true,
  "provider": "supabase",
  "environment": "development",
  "ready": true,
  "missing_configuration": [],
  "public_paths": [
    "/",
    "/api",
    "/api/",
    "/api/auth/status",
    "/docs",
    "/health",
    "/openapi.json",
    "/redoc"
  ]
}
```

### `GET /api/auth/me`

Purpose:
- Return the authenticated user context resolved by the backend.
- Return the current permission flags the frontend should use for UI gating.

Example response:

```json
{
  "enabled": true,
  "authenticated": true,
  "provider": "supabase",
  "user": {
    "id": "user-123",
    "email": "worker@example.com",
    "role": "case_worker",
    "app_metadata": {"role": "case_worker"},
    "user_metadata": {"display_name": "Case Worker"}
  },
  "permissions": {
    "can_read": true,
    "can_write": true,
    "can_run_analysis": true,
    "can_delete_records": false,
    "can_clear_map": false,
    "can_delete_cases": false,
    "can_manage_users": false
  }
}
```

### `GET /api/auth/permissions`

Purpose:
- Lightweight permission probe for UI feature flags.

Example response:

```json
{
  "can_read": true,
  "can_write": true,
  "can_run_analysis": true,
  "can_delete_records": false,
  "can_clear_map": false,
  "can_delete_cases": false,
  "can_manage_users": false
}
```

## Current role policy scaffold

The backend currently recognizes these practical roles:

- `authenticated` — fallback operator role during rollout
- `case_worker`
- `supervisor`

### Effective permissions

| Role | Read | Create/Update | Run analytics/ghosting | Delete records | Clear MAP | Delete cases |
|---|---|---:|---:|---:|---:|---:|
| `authenticated` | yes | yes | yes | no | no | no |
| `case_worker` | yes | yes | yes | no | no | no |
| `supervisor` | yes | yes | yes | yes | yes | yes |

## What the frontend should do with these permissions

- Show normal read/edit flows when `can_write=true`.
- Hide or disable destructive actions when:
  - `can_delete_records=false`
  - `can_clear_map=false`
  - `can_delete_cases=false`
- Prefer backend permission flags over hardcoding role names in the UI.

## Current protected behavior by route type

- **Read routes**: require authentication when backend auth is enabled.
- **Create/update routes**: require operator access (`authenticated`, `case_worker`, `supervisor`).
- **Delete / clear routes**: require `supervisor`.

This is a rollout-safe scaffold, not the final RBAC model.
If the project later needs more granular separation, the frontend should continue
relying on `permissions` rather than assuming the permission model is static.
