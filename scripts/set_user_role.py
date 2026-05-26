#!/usr/bin/env python3
"""
Set a Supabase user's role via the Admin API.

Requires the SERVICE ROLE key (not the anon key).
Find it in: Supabase Dashboard → Settings → API → service_role secret

Usage:
    python scripts/set_user_role.py <email> <role>

    role must be one of: case_worker, supervisor

Example:
    python scripts/set_user_role.py remyndayizeye@gmail.com supervisor

Environment variables (or set them in .env):
    SUPABASE_URL          — e.g. https://abcxyz.supabase.co
    SUPABASE_SERVICE_KEY  — service_role JWT (keep this secret, never commit it)
"""

import json
import os
import sys
from urllib import error, request


def load_env() -> None:
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def get_user_by_email(base_url: str, service_key: str, email: str) -> dict:
    url = f"{base_url}/auth/v1/admin/users?email={email}"
    req = request.Request(
        url,
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
        },
    )
    with request.urlopen(req) as resp:
        data = json.loads(resp.read())
    users = data.get("users", [])
    if not users:
        raise SystemExit(f"No user found with email: {email}")
    return users[0]


def set_app_metadata_role(
    base_url: str, service_key: str, user_id: str, role: str
) -> dict:
    url = f"{base_url}/auth/v1/admin/users/{user_id}"
    body = json.dumps({"app_metadata": {"role": role}}).encode()
    req = request.Request(
        url,
        data=body,
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
        },
        method="PUT",
    )
    with request.urlopen(req) as resp:
        return json.loads(resp.read())


VALID_ROLES = {"case_worker", "supervisor"}


def main() -> None:
    load_env()

    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    email, role = sys.argv[1], sys.argv[2]
    if role not in VALID_ROLES:
        raise SystemExit(f"Invalid role '{role}'. Must be one of: {', '.join(sorted(VALID_ROLES))}")

    base_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not base_url or not service_key:
        raise SystemExit("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")

    print(f"Looking up user: {email}")
    try:
        user = get_user_by_email(base_url, service_key, email)
    except error.HTTPError as e:
        raise SystemExit(f"Supabase API error: {e.code} {e.read().decode()}") from e

    user_id = user["id"]
    print(f"Found user id: {user_id}")
    print(f"Setting app_metadata.role = '{role}' ...")

    try:
        updated = set_app_metadata_role(base_url, service_key, user_id, role)
    except error.HTTPError as e:
        raise SystemExit(f"Supabase API error: {e.code} {e.read().decode()}") from e

    actual_role = (updated.get("app_metadata") or {}).get("role")
    if actual_role == role:
        print(f"Done. {email} is now '{role}'.")
    else:
        print(f"Warning: expected role '{role}' but got '{actual_role}'. Full response:")
        print(json.dumps(updated, indent=2))


if __name__ == "__main__":
    main()
