from __future__ import annotations

import os
import time

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ["AUTH_ENABLED"] = "false"

from app.db.database import Base
from fastapi_app.app.auth import clear_auth_settings_cache
from fastapi_app.app.db import get_db
from fastapi_app.main import app

# HS256 secret the auth layer verifies test tokens against (SUPABASE_JWT_SECRET).
TEST_JWT_SECRET = "test-jwt-secret-at-least-32-bytes-long!!"


def make_jwt(
    *, sub: str, email: str, role: str | None, top_role: str = "authenticated"
) -> str:
    """Mint a Supabase-style HS256 access token signed with TEST_JWT_SECRET."""
    now = int(time.time())
    claims: dict = {
        "sub": sub,
        "email": email,
        "aud": "authenticated",
        "role": top_role,
        "app_metadata": {"role": role} if role else {},
        "user_metadata": {},
        "iat": now,
        "exp": now + 3600,
    }
    return jwt.encode(claims, TEST_JWT_SECRET, algorithm="HS256")


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


WORKER = _bearer(
    make_jwt(sub="user-worker", email="worker@example.com", role="case_worker")
)
SUPERVISOR = _bearer(
    make_jwt(sub="user-supervisor", email="supervisor@example.com", role="supervisor")
)


@pytest.fixture(autouse=True)
def _reset_cache():
    clear_auth_settings_cache()
    yield
    clear_auth_settings_cache()


@pytest.fixture
def auth_client(monkeypatch: pytest.MonkeyPatch):
    """TestClient with AUTH_ENABLED=true and local HS256 JWT verification."""
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "sb_key_example")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    clear_auth_settings_cache()

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    clear_auth_settings_cache()


# ─── Permission flag assertions ───────────────────────────────────────────────


def test_case_worker_permission_flags(auth_client: TestClient):
    resp = auth_client.get("/api/auth/permissions", headers=WORKER)
    assert resp.status_code == 200
    assert resp.json() == {
        "can_read": True,
        "can_write": True,
        "can_run_analysis": True,
        "can_delete_records": False,
        "can_clear_map": False,
        "can_delete_cases": False,
        "can_manage_users": False,
    }


def test_supervisor_permission_flags(auth_client: TestClient):
    resp = auth_client.get("/api/auth/permissions", headers=SUPERVISOR)
    assert resp.status_code == 200
    assert all(resp.json().values())


def test_authenticated_jwt_role_has_operator_permissions(auth_client: TestClient):
    """The 'authenticated' JWT role with no app_metadata.role override is treated as operator."""
    plain = _bearer(
        make_jwt(sub="user-plain", email="plain@example.com", role=None)
    )

    resp = auth_client.get("/api/auth/permissions", headers=plain)
    assert resp.status_code == 200
    data = resp.json()
    assert data["can_read"] is True
    assert data["can_write"] is True
    assert data["can_run_analysis"] is True
    assert data["can_delete_records"] is False
    assert data["can_manage_users"] is False


def test_unauthenticated_request_blocked(auth_client: TestClient):
    resp = auth_client.get("/api/cases/")
    assert resp.status_code == 401
    assert resp.headers["www-authenticate"] == "Bearer"


# ─── Cases ────────────────────────────────────────────────────────────────────


def test_case_worker_cannot_delete_case(auth_client: TestClient):
    case = auth_client.post("/api/cases/", json={"patient_name": "Protected"}, headers=WORKER).json()
    resp = auth_client.delete(f"/api/cases/{case['id']}", headers=WORKER)
    assert resp.status_code == 403
    assert "Insufficient role" in resp.json()["detail"]


def test_supervisor_can_delete_case(auth_client: TestClient):
    case = auth_client.post("/api/cases/", json={"patient_name": "To Delete"}, headers=WORKER).json()
    assert auth_client.delete(f"/api/cases/{case['id']}", headers=SUPERVISOR).status_code == 204
    assert auth_client.get(f"/api/cases/{case['id']}", headers=WORKER).status_code == 404


def test_case_worker_cannot_delete_partner(auth_client: TestClient):
    case = auth_client.post("/api/cases/", json={"patient_name": "Index"}, headers=WORKER).json()
    partner = auth_client.post(
        f"/api/cases/{case['id']}/partners", json={"name": "P1"}, headers=WORKER
    ).json()
    resp = auth_client.delete(f"/api/cases/partners/{partner['id']}", headers=WORKER)
    assert resp.status_code == 403


def test_supervisor_can_delete_partner(auth_client: TestClient):
    case = auth_client.post("/api/cases/", json={"patient_name": "Index"}, headers=WORKER).json()
    partner = auth_client.post(
        f"/api/cases/{case['id']}/partners", json={"name": "P1"}, headers=WORKER
    ).json()
    assert auth_client.delete(f"/api/cases/partners/{partner['id']}", headers=SUPERVISOR).status_code == 204
    assert auth_client.get(f"/api/cases/partners/{partner['id']}", headers=WORKER).status_code == 404


# ─── Labs ─────────────────────────────────────────────────────────────────────


def test_case_worker_cannot_delete_lab(auth_client: TestClient):
    case = auth_client.post("/api/cases/", json={"patient_name": "Lab Index"}, headers=WORKER).json()
    lab = auth_client.post(
        f"/api/cases/{case['id']}/labs",
        json={"test_category": "Non-treponemal", "test_type": "RPR", "collection_date": "2024-01-01"},
        headers=WORKER,
    ).json()
    assert auth_client.delete(f"/api/cases/labs/{lab['id']}", headers=WORKER).status_code == 403


def test_supervisor_can_delete_lab(auth_client: TestClient):
    case = auth_client.post("/api/cases/", json={"patient_name": "Lab Index"}, headers=WORKER).json()
    lab = auth_client.post(
        f"/api/cases/{case['id']}/labs",
        json={"test_category": "Non-treponemal", "test_type": "RPR", "collection_date": "2024-01-01"},
        headers=WORKER,
    ).json()
    assert auth_client.delete(f"/api/cases/labs/{lab['id']}", headers=SUPERVISOR).status_code == 204
    assert auth_client.get(f"/api/cases/labs/{lab['id']}", headers=WORKER).status_code == 404


# ─── Symptoms ─────────────────────────────────────────────────────────────────


def test_case_worker_cannot_delete_symptom(auth_client: TestClient):
    case = auth_client.post("/api/cases/", json={"patient_name": "Sx Index"}, headers=WORKER).json()
    sx = auth_client.post(
        f"/api/cases/{case['id']}/symptoms",
        json={"symptom_type": "Penile LX", "onset_date": "2024-01-01", "date_kind": "Onset reported"},
        headers=WORKER,
    ).json()
    assert auth_client.delete(f"/api/cases/symptoms/{sx['id']}", headers=WORKER).status_code == 403


def test_supervisor_can_delete_symptom(auth_client: TestClient):
    case = auth_client.post("/api/cases/", json={"patient_name": "Sx Index"}, headers=WORKER).json()
    sx = auth_client.post(
        f"/api/cases/{case['id']}/symptoms",
        json={"symptom_type": "Penile LX", "onset_date": "2024-01-01", "date_kind": "Onset reported"},
        headers=WORKER,
    ).json()
    assert auth_client.delete(f"/api/cases/symptoms/{sx['id']}", headers=SUPERVISOR).status_code == 204
    assert auth_client.get(f"/api/cases/symptoms/{sx['id']}", headers=WORKER).status_code == 404


# ─── Ghostings ────────────────────────────────────────────────────────────────


def test_case_worker_cannot_delete_ghosting(auth_client: TestClient):
    case = auth_client.post("/api/cases/", json={"patient_name": "Ghost Index"}, headers=WORKER).json()
    ghosting = auth_client.post(
        f"/api/cases/{case['id']}/ghostings",
        json={"ghosting_type": "Ghosting a Source"},
        headers=WORKER,
    ).json()
    assert auth_client.delete(f"/api/cases/ghostings/{ghosting['id']}", headers=WORKER).status_code == 403


def test_supervisor_can_delete_ghosting(auth_client: TestClient):
    case = auth_client.post("/api/cases/", json={"patient_name": "Ghost Index"}, headers=WORKER).json()
    ghosting = auth_client.post(
        f"/api/cases/{case['id']}/ghostings",
        json={"ghosting_type": "Ghosting a Source"},
        headers=WORKER,
    ).json()
    assert auth_client.delete(f"/api/cases/ghostings/{ghosting['id']}", headers=SUPERVISOR).status_code == 204
    assert auth_client.get(f"/api/cases/ghostings/{ghosting['id']}", headers=WORKER).status_code == 404


# ─── Arrow links ──────────────────────────────────────────────────────────────


def test_case_worker_cannot_delete_arrow_link(auth_client: TestClient):
    case = auth_client.post("/api/cases/", json={"patient_name": "Link Index"}, headers=WORKER).json()
    auth_client.post(f"/api/cases/{case['id']}/partners", json={"name": "P1"}, headers=WORKER)
    link = auth_client.post(
        f"/api/cases/{case['id']}/links",
        json={"from_ref": "OP", "to_ref": "1"},
        headers=WORKER,
    ).json()
    assert auth_client.delete(f"/api/cases/links/{link['id']}", headers=WORKER).status_code == 403


def test_supervisor_can_delete_arrow_link(auth_client: TestClient):
    case = auth_client.post("/api/cases/", json={"patient_name": "Link Index"}, headers=WORKER).json()
    auth_client.post(f"/api/cases/{case['id']}/partners", json={"name": "P1"}, headers=WORKER)
    link = auth_client.post(
        f"/api/cases/{case['id']}/links",
        json={"from_ref": "OP", "to_ref": "1"},
        headers=WORKER,
    ).json()
    assert auth_client.delete(f"/api/cases/links/{link['id']}", headers=SUPERVISOR).status_code == 204
    assert auth_client.get(f"/api/cases/links/{link['id']}", headers=WORKER).status_code == 404


# ─── Relationships ────────────────────────────────────────────────────────────


def _create_relationship(auth_client: TestClient) -> tuple[dict, dict, dict]:
    case = auth_client.post("/api/cases/", json={"patient_name": "Rel Index"}, headers=WORKER).json()
    partner = auth_client.post(
        f"/api/cases/{case['id']}/partners", json={"name": "P1"}, headers=WORKER
    ).json()
    rel = auth_client.post(
        f"/api/cases/{case['id']}/partners/{partner['id']}/relationship",
        json={},
        headers=WORKER,
    ).json()
    return case, partner, rel


def test_case_worker_cannot_delete_relationship(auth_client: TestClient):
    _, _, rel = _create_relationship(auth_client)
    assert (
        auth_client.delete(f"/api/cases/relationships/{rel['id']}", headers=WORKER).status_code == 403
    )


def test_supervisor_can_delete_relationship(auth_client: TestClient):
    case, partner, rel = _create_relationship(auth_client)
    assert (
        auth_client.delete(f"/api/cases/relationships/{rel['id']}", headers=SUPERVISOR).status_code == 204
    )
    assert (
        auth_client.get(
            f"/api/cases/{case['id']}/partners/{partner['id']}/relationship",
            headers=WORKER,
        ).status_code
        == 404
    )


def test_case_worker_cannot_delete_relationship_report(auth_client: TestClient):
    _, _, rel = _create_relationship(auth_client)
    report = auth_client.post(
        f"/api/cases/relationships/{rel['id']}/reports",
        json={"reporter": "OP"},
        headers=WORKER,
    ).json()
    assert (
        auth_client.delete(f"/api/cases/relationships/reports/{report['id']}", headers=WORKER).status_code
        == 403
    )


def test_supervisor_can_delete_relationship_report(auth_client: TestClient):
    _, _, rel = _create_relationship(auth_client)
    report = auth_client.post(
        f"/api/cases/relationships/{rel['id']}/reports",
        json={"reporter": "OP"},
        headers=WORKER,
    ).json()
    assert (
        auth_client.delete(
            f"/api/cases/relationships/reports/{report['id']}", headers=SUPERVISOR
        ).status_code
        == 204
    )
    assert (
        auth_client.get(
            f"/api/cases/relationships/reports/{report['id']}", headers=WORKER
        ).status_code
        == 404
    )
