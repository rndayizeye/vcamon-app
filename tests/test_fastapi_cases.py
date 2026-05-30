from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["AUTH_ENABLED"] = "false"

from app.db.database import Base
from fastapi_app.app.auth import clear_auth_settings_cache
from fastapi_app.app.db import get_db
from fastapi_app.main import app


@pytest.fixture(autouse=True)
def reset_auth_settings_cache():
    clear_auth_settings_cache()
    yield
    clear_auth_settings_cache()


@pytest.fixture
def client():
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
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    clear_auth_settings_cache()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    clear_auth_settings_cache()


def test_health_endpoint(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_auth_status_endpoint_reports_disabled_by_default(client: TestClient):
    response = client.get("/api/auth/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is False
    assert payload["provider"] == "supabase"
    assert payload["ready"] is True
    assert payload["missing_configuration"] == []

    me_response = client.get("/api/auth/me")
    assert me_response.status_code == 200
    assert me_response.json() == {
        "enabled": False,
        "authenticated": False,
        "provider": "supabase",
        "user": None,
        "permissions": {
            "can_read": False,
            "can_write": False,
            "can_run_analysis": False,
            "can_delete_records": False,
            "can_clear_map": False,
            "can_delete_cases": False,
            "can_manage_users": False,
        },
    }


def test_auth_enabled_blocks_private_routes_without_token(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "sb_publishable_example")
    clear_auth_settings_cache()

    private_response = client.get("/api/cases/")
    assert private_response.status_code == 401
    assert private_response.headers["www-authenticate"] == "Bearer"

    me_response = client.get("/api/auth/me")
    assert me_response.status_code == 401

    health_response = client.get("/health")
    assert health_response.status_code == 200

    status_response = client.get("/api/auth/status")
    assert status_response.status_code == 200
    assert status_response.json()["enabled"] is True


def test_auth_enabled_returns_service_unavailable_when_config_missing(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_PUBLISHABLE_KEY", raising=False)
    clear_auth_settings_cache()

    response = client.get(
        "/api/cases/",
        headers={"Authorization": "Bearer token-123"},
    )
    assert response.status_code == 503
    assert "required configuration is missing" in response.json()["detail"]


def test_auth_enabled_allows_cors_preflight_without_token(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "sb_publishable_example")
    clear_auth_settings_cache()

    response = client.options(
        "/api/cases/",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_auth_enabled_allows_authenticated_request_and_me_endpoint(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "sb_publishable_example")
    clear_auth_settings_cache()

    from fastapi_app.app import auth as auth_module

    monkeypatch.setattr(
        auth_module,
        "fetch_supabase_user",
        lambda settings, access_token: {
            "id": "user-123",
            "email": "worker@example.com",
            "role": "authenticated",
            "app_metadata": {"role": "case_worker"},
            "user_metadata": {"display_name": "Case Worker"},
        },
    )

    headers = {"Authorization": "Bearer token-123"}

    me_response = client.get("/api/auth/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json() == {
        "enabled": True,
        "authenticated": True,
        "provider": "supabase",
        "user": {
            "id": "user-123",
            "email": "worker@example.com",
            "role": "case_worker",
            "app_metadata": {"role": "case_worker"},
            "user_metadata": {"display_name": "Case Worker"},
        },
        "permissions": {
            "can_read": True,
            "can_write": True,
            "can_run_analysis": True,
            "can_delete_records": False,
            "can_clear_map": False,
            "can_delete_cases": False,
            "can_manage_users": False,
        },
    }

    permissions_response = client.get("/api/auth/permissions", headers=headers)
    assert permissions_response.status_code == 200
    assert permissions_response.json() == {
        "can_read": True,
        "can_write": True,
        "can_run_analysis": True,
        "can_delete_records": False,
        "can_clear_map": False,
        "can_delete_cases": False,
        "can_manage_users": False,
    }

    cases_response = client.get("/api/cases/", headers=headers)
    assert cases_response.status_code == 200
    assert cases_response.json() == []


def test_supervisor_required_for_case_delete_under_auth(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "sb_publishable_example")
    clear_auth_settings_cache()

    from fastapi_app.app import auth as auth_module

    def fake_fetch_supabase_user(settings, access_token):
        if access_token == "supervisor-token":
            return {
                "id": "user-supervisor",
                "email": "supervisor@example.com",
                "role": "authenticated",
                "app_metadata": {"role": "supervisor"},
                "user_metadata": {"display_name": "Supervisor"},
            }
        return {
            "id": "user-worker",
            "email": "worker@example.com",
            "role": "authenticated",
            "app_metadata": {"role": "case_worker"},
            "user_metadata": {"display_name": "Case Worker"},
        }

    monkeypatch.setattr(auth_module, "fetch_supabase_user", fake_fetch_supabase_user)

    worker_headers = {"Authorization": "Bearer worker-token"}
    supervisor_headers = {"Authorization": "Bearer supervisor-token"}

    created = client.post(
        "/api/cases/",
        json={"patient_name": "Protected Delete Case"},
        headers=worker_headers,
    )
    assert created.status_code == 201
    case_id = created.json()["id"]

    forbidden_delete = client.delete(f"/api/cases/{case_id}", headers=worker_headers)
    assert forbidden_delete.status_code == 403
    assert "Insufficient role" in forbidden_delete.json()["detail"]

    allowed_delete = client.delete(f"/api/cases/{case_id}", headers=supervisor_headers)
    assert allowed_delete.status_code == 204


def test_create_and_fetch_case(client: TestClient):
    create_response = client.post(
        "/api/cases/",
        json={"patient_name": "Doe, Jane", "lot": "710", "case_manager": "Taylor"},
    )
    assert create_response.status_code == 201

    created = create_response.json()
    case_id = created["id"]
    assert created["patient_name"] == "Doe, Jane"
    assert created["lot"] == "710"
    assert created["diagnosis_code"] == "710"

    get_response = client.get(f"/api/cases/{case_id}")
    assert get_response.status_code == 200
    assert get_response.json()["case_manager"] == "Taylor"
    assert get_response.json()["diagnosis_code"] == "710"


def test_create_case_accepts_diagnosis_code_alias(client: TestClient):
    response = client.post(
        "/api/cases/",
        json={"patient_name": "Doe, Jamie", "diagnosis_code": "755"},
    )
    assert response.status_code == 201
    assert response.json()["lot"] == "755"
    assert response.json()["diagnosis_code"] == "755"


def test_search_cases_endpoint(client: TestClient):
    client.post("/api/cases/", json={"patient_name": "Doe, Jane"})
    client.post("/api/cases/", json={"patient_name": "Smith, John"})

    response = client.get("/api/cases/", params={"search": "doe"})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["patient_name"] == "Doe, Jane"


def test_update_case_endpoint(client: TestClient):
    created = client.post("/api/cases/", json={"patient_name": "Doe, Jane"}).json()

    response = client.patch(
        f"/api/cases/{created['id']}",
        json={"case_manager": "Updated Manager", "symptom_ongoing": True},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["case_manager"] == "Updated Manager"
    assert payload["symptom_ongoing"] is True


def test_create_list_update_and_delete_partner(client: TestClient):
    case = client.post("/api/cases/", json={"patient_name": "Index Case"}).json()

    create_partner_response = client.post(
        f"/api/cases/{case['id']}/partners",
        json={"name": "Partner A"},
    )
    assert create_partner_response.status_code == 201
    partner = create_partner_response.json()
    assert partner["partner_number"] == 1
    assert partner["name"] == "Partner A"

    second_partner_response = client.post(
        f"/api/cases/{case['id']}/partners",
        json={"name": "Partner B"},
    )
    assert second_partner_response.status_code == 201
    assert second_partner_response.json()["partner_number"] == 2

    list_response = client.get(f"/api/cases/{case['id']}/partners")
    assert list_response.status_code == 200
    assert [item["partner_number"] for item in list_response.json()] == [1, 2]

    update_response = client.patch(
        f"/api/cases/partners/{partner['id']}",
        json={"name": "Partner A Updated"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Partner A Updated"

    delete_response = client.delete(f"/api/cases/partners/{partner['id']}")
    assert delete_response.status_code == 204

    get_deleted_response = client.get(f"/api/cases/partners/{partner['id']}")
    assert get_deleted_response.status_code == 404


def test_case_and_partner_labs_crud(client: TestClient):
    case = client.post("/api/cases/", json={"patient_name": "Lab Index"}).json()
    partner = client.post(
        f"/api/cases/{case['id']}/partners", json={"name": "Lab Partner"}
    ).json()

    case_lab = client.post(
        f"/api/cases/{case['id']}/labs",
        json={
            "test_category": "Non-treponemal",
            "test_type": "RPR",
            "titer": "1:32",
            "collection_date": "2024-03-10",
        },
    )
    assert case_lab.status_code == 201
    case_lab_payload = case_lab.json()
    assert case_lab_payload["case_id"] == case["id"]
    assert case_lab_payload["partner_id"] is None
    assert case_lab_payload["test_category"] == "Non-treponemal"

    partner_lab = client.post(
        f"/api/cases/partners/{partner['id']}/labs",
        json={
            "test_category": "Treponemal",
            "test_type": "TP-AB",
            "result": "Reactive",
            "collection_date": "2024-03-11",
        },
    )
    assert partner_lab.status_code == 201
    partner_lab_payload = partner_lab.json()
    assert partner_lab_payload["partner_id"] == partner["id"]
    assert partner_lab_payload["case_id"] is None

    list_case_labs = client.get(f"/api/cases/{case['id']}/labs")
    assert list_case_labs.status_code == 200
    assert [item["id"] for item in list_case_labs.json()] == [case_lab_payload["id"]]

    list_partner_labs = client.get(f"/api/cases/partners/{partner['id']}/labs")
    assert list_partner_labs.status_code == 200
    assert [item["id"] for item in list_partner_labs.json()] == [
        partner_lab_payload["id"]
    ]

    update_lab = client.patch(
        f"/api/cases/labs/{case_lab_payload['id']}",
        json={"result": "Reactive", "titer": "1:64"},
    )
    assert update_lab.status_code == 200
    assert update_lab.json()["result"] == "Reactive"
    assert update_lab.json()["titer"] == "1:64"

    get_partner_lab = client.get(f"/api/cases/labs/{partner_lab_payload['id']}")
    assert get_partner_lab.status_code == 200
    assert get_partner_lab.json()["test_type"] == "TP-AB"

    delete_partner_lab = client.delete(f"/api/cases/labs/{partner_lab_payload['id']}")
    assert delete_partner_lab.status_code == 204
    assert client.get(f"/api/cases/labs/{partner_lab_payload['id']}").status_code == 404


def test_case_and_partner_symptoms_crud(client: TestClient):
    case = client.post("/api/cases/", json={"patient_name": "Symptom Index"}).json()
    partner = client.post(
        f"/api/cases/{case['id']}/partners", json={"name": "Symptom Partner"}
    ).json()

    case_symptom = client.post(
        f"/api/cases/{case['id']}/symptoms",
        json={
            "symptom_type": "Penile LX",
            "onset_date": "2024-02-01",
            "date_kind": "Onset reported",
            "duration_days": 7,
        },
    )
    assert case_symptom.status_code == 201
    case_symptom_payload = case_symptom.json()
    assert case_symptom_payload["classification"] == "Primary"
    assert case_symptom_payload["case_id"] == case["id"]
    assert case_symptom_payload["partner_id"] is None
    assert case_symptom_payload["date_kind"] == "Onset reported"
    assert case_symptom_payload["duration_source"] == "Reported"
    assert case_symptom_payload["ongoing"] is False

    partner_symptom = client.post(
        f"/api/cases/partners/{partner['id']}/symptoms",
        json={
            "symptom_type": "Rash",
            "onset_date": "2024-02-10",
            "date_kind": "Observed during exam (onset unknown)",
        },
    )
    assert partner_symptom.status_code == 201
    partner_symptom_payload = partner_symptom.json()
    assert partner_symptom_payload["classification"] == "Secondary"
    assert partner_symptom_payload["partner_id"] == partner["id"]
    assert (
        partner_symptom_payload["date_kind"] == "Observed during exam (onset unknown)"
    )
    assert partner_symptom_payload["duration_source"] == "Assumed max"
    assert partner_symptom_payload["ongoing"] is True

    list_case_symptoms = client.get(f"/api/cases/{case['id']}/symptoms")
    assert list_case_symptoms.status_code == 200
    assert [item["id"] for item in list_case_symptoms.json()] == [
        case_symptom_payload["id"]
    ]

    list_partner_symptoms = client.get(f"/api/cases/partners/{partner['id']}/symptoms")
    assert list_partner_symptoms.status_code == 200
    assert [item["id"] for item in list_partner_symptoms.json()] == [
        partner_symptom_payload["id"]
    ]

    update_symptom = client.patch(
        f"/api/cases/symptoms/{case_symptom_payload['id']}",
        json={
            "symptom_type": "Rash",
            "date_kind": "Observed during exam (onset unknown)",
        },
    )
    assert update_symptom.status_code == 200
    updated_payload = update_symptom.json()
    assert updated_payload["classification"] == "Secondary"
    assert updated_payload["date_kind"] == "Observed during exam (onset unknown)"
    assert updated_payload["duration_source"] == "Reported"
    assert updated_payload["ongoing"] is True

    get_partner_symptom = client.get(
        f"/api/cases/symptoms/{partner_symptom_payload['id']}"
    )
    assert get_partner_symptom.status_code == 200
    assert get_partner_symptom.json()["symptom_type"] == "Rash"

    delete_partner_symptom = client.delete(
        f"/api/cases/symptoms/{partner_symptom_payload['id']}"
    )
    assert delete_partner_symptom.status_code == 204
    assert (
        client.get(f"/api/cases/symptoms/{partner_symptom_payload['id']}").status_code
        == 404
    )


def test_timeline_crud(client: TestClient):
    case = client.post("/api/cases/", json={"patient_name": "Timeline Index"}).json()
    partner = client.post(
        f"/api/cases/{case['id']}/partners", json={"name": "Timeline Partner"}
    ).json()

    created = client.post(
        f"/api/cases/{case['id']}/timeline",
        json={
            "event_date": "2024-04-01",
            "event_type": "Treatment",
            "notes": "Initial timeline event",
            "partner_id": partner["id"],
        },
    )
    assert created.status_code == 201
    event = created.json()
    assert event["case_id"] == case["id"]
    assert event["partner_id"] == partner["id"]

    list_response = client.get(f"/api/cases/{case['id']}/timeline")
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [event["id"]]

    get_response = client.get(f"/api/cases/timeline/{event['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["event_type"] == "Treatment"

    update_response = client.patch(
        f"/api/cases/timeline/{event['id']}",
        json={"event_type": "Lab", "notes": "Updated timeline event"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["event_type"] == "Lab"
    assert update_response.json()["notes"] == "Updated timeline event"

    delete_response = client.delete(f"/api/cases/timeline/{event['id']}")
    assert delete_response.status_code == 204
    assert client.get(f"/api/cases/timeline/{event['id']}").status_code == 404


def test_relationship_and_report_crud(client: TestClient):
    case = client.post(
        "/api/cases/", json={"patient_name": "Relationship Index"}
    ).json()
    partner = client.post(
        f"/api/cases/{case['id']}/partners", json={"name": "Relationship Partner"}
    ).json()

    relationship_response = client.post(
        f"/api/cases/{case['id']}/partners/{partner['id']}/relationship",
        json={
            "exposure_first_date": "2024-01-01",
            "exposure_last_date": "2024-01-15",
            "op_body_parts": ["penis"],
            "partner_body_parts": ["anus"],
        },
    )
    assert relationship_response.status_code == 201
    relationship = relationship_response.json()
    assert relationship["case_id"] == case["id"]
    assert relationship["partner_id"] == partner["id"]
    assert relationship["op_body_parts"] == ["penis"]
    assert relationship["partner_body_parts"] == ["anus"]

    duplicate_response = client.post(
        f"/api/cases/{case['id']}/partners/{partner['id']}/relationship",
        json={},
    )
    assert duplicate_response.status_code == 409

    get_relationship = client.get(
        f"/api/cases/{case['id']}/partners/{partner['id']}/relationship"
    )
    assert get_relationship.status_code == 200
    assert get_relationship.json()["id"] == relationship["id"]

    update_relationship = client.patch(
        f"/api/cases/{case['id']}/partners/{partner['id']}/relationship",
        json={"op_body_parts": ["penis", "mouth"]},
    )
    assert update_relationship.status_code == 200
    assert update_relationship.json()["op_body_parts"] == ["penis", "mouth"]

    report_response = client.post(
        f"/api/cases/relationships/{relationship['id']}/reports",
        json={
            "reporter": "OP",
            "exposure_first_date": "2024-01-02",
            "exposure_last_date": "2024-01-14",
        },
    )
    assert report_response.status_code == 201
    report = report_response.json()
    assert report["relationship_id"] == relationship["id"]
    assert report["reporter"] == "OP"

    list_reports = client.get(f"/api/cases/relationships/{relationship['id']}/reports")
    assert list_reports.status_code == 200
    assert [item["id"] for item in list_reports.json()] == [report["id"]]

    get_report = client.get(f"/api/cases/relationships/reports/{report['id']}")
    assert get_report.status_code == 200
    assert get_report.json()["reporter"] == "OP"

    update_report = client.patch(
        f"/api/cases/relationships/reports/{report['id']}",
        json={"reporter": "Partner 1"},
    )
    assert update_report.status_code == 200
    assert update_report.json()["reporter"] == "Partner 1"

    delete_report = client.delete(f"/api/cases/relationships/reports/{report['id']}")
    assert delete_report.status_code == 204
    assert (
        client.get(f"/api/cases/relationships/reports/{report['id']}").status_code
        == 404
    )

    delete_relationship = client.delete(
        f"/api/cases/relationships/{relationship['id']}"
    )
    assert delete_relationship.status_code == 204
    assert (
        client.get(
            f"/api/cases/{case['id']}/partners/{partner['id']}/relationship"
        ).status_code
        == 404
    )


def test_ghosting_analysis_endpoint(client: TestClient):
    response = client.post(
        "/api/ghosting/analyze",
        json={
            "op_name": "Johnny Smith",
            "op_symptoms": [
                {
                    "type": "Primary Chancre",
                    "onset": "2020-03-05",
                    "duration_days": 0,
                    "anatomical_site": "Penile LX",
                }
            ],
            "op_exposure": {
                "first": "2019-09-03",
                "last": "2020-02-25",
            },
            "op_treatment_date": "2020-03-10",
            "op_body_parts": ["penis"],
            "partner_name": "Samuel",
            "partner_symptoms": [
                {
                    "type": "Primary Chancre",
                    "onset": "2020-02-08",
                    "duration_days": 7,
                    "anatomical_site": "Rectal LX",
                }
            ],
            "partner_exposure": {
                "first": "2019-09-01",
                "last": "2020-02-15",
            },
            "partner_body_parts": ["anus"],
            "partner_treatment_date": "2020-02-15",
        },
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["case1_name"] == "Samuel"
    assert payload["case2_name"] == "Johnny Smith"
    assert payload["case1_symptom"]["type"] == "Primary Chancre"
    assert payload["ghosted_source"]["lesion_type"] == "ghosted_source"
    # Samuel's chancre (2/8) precedes Johnny's (3/5), so the supported direction is
    # Samuel -> Johnny (the spread scenario). A ghosted source onto Johnny in
    # January contradicts his actual March chancre, so the source scenario fails.
    assert (
        payload["spread_scenarios"]["pass_count"]
        >= payload["source_scenarios"]["pass_count"]
    )
    assert "Samuel) is the SOURCE" in payload["verdict"]
    assert payload["suggested_records"] == []


def test_case_partner_ghosting_analysis_uses_saved_data(client: TestClient):
    case = client.post(
        "/api/cases/",
        json={
            "patient_name": "Johnny Smith",
            "treatment_date": "2020-03-10",
        },
    ).json()
    partner = client.post(
        f"/api/cases/{case['id']}/partners",
        json={
            "name": "Samuel",
            "treatment_date": "2020-02-15",
        },
    ).json()

    case_symptom = client.post(
        f"/api/cases/{case['id']}/symptoms",
        json={
            "symptom_type": "Penile LX",
            "onset_date": "2020-03-05",
            "date_kind": "Onset reported",
            "duration_days": 0,
        },
    )
    assert case_symptom.status_code == 201

    partner_symptom = client.post(
        f"/api/cases/partners/{partner['id']}/symptoms",
        json={
            "symptom_type": "Rectal LX",
            "onset_date": "2020-02-15",
            "date_kind": "Observed during exam (onset unknown)",
            "duration_days": 7,
        },
    )
    assert partner_symptom.status_code == 201

    relationship = client.post(
        f"/api/cases/{case['id']}/partners/{partner['id']}/relationship",
        json={
            "exposure_first_date": "2019-09-01",
            "exposure_last_date": "2020-02-25",
            "op_body_parts": ["penis"],
            "partner_body_parts": ["anus"],
        },
    )
    assert relationship.status_code == 201

    response = client.post(
        f"/api/cases/{case['id']}/partners/{partner['id']}/ghosting-analysis",
        json={},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["case1_name"] == "Samuel"
    assert payload["case1_ref"] == "1"
    assert payload["case2_ref"] == "OP"
    assert payload["case1_symptom"]["onset"] == "2020-02-08"
    assert "SOURCE" in payload["verdict"]
    assert len(payload["suggested_records"]) == 2
    assert {record["ghosting_type"] for record in payload["suggested_records"]} == {
        "Ghosting a Source",
        "Ghosting a Spread",
    }
    assert payload["suggested_records"][0]["from_ref"] == "1"
    assert payload["suggested_records"][0]["to_ref"] == "OP"


def test_case_ghostings_crud(client: TestClient):
    case = client.post("/api/cases/", json={"patient_name": "Ghosting Case"}).json()

    minimal_create = client.post(
        f"/api/cases/{case['id']}/ghostings",
        json={"ghosting_type": "Ghosting a Source"},
    )
    assert minimal_create.status_code == 201
    minimal_ghosting = minimal_create.json()
    assert minimal_ghosting["from_ref"] is None
    assert minimal_ghosting["to_ref"] is None
    assert minimal_ghosting["notes"] is None

    created = client.post(
        f"/api/cases/{case['id']}/ghostings",
        json={
            "ghosting_type": "Ghosting a Source",
            "from_ref": "OP",
            "to_ref": "1",
            "notes": "Ghosted source: 2024-01-01 → 2024-01-21. Verdict: manual review.",
        },
    )
    assert created.status_code == 201
    ghosting = created.json()
    assert ghosting["case_id"] == case["id"]
    assert ghosting["ghosting_type"] == "Ghosting a Source"

    listed = client.get(f"/api/cases/{case['id']}/ghostings")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [
        minimal_ghosting["id"],
        ghosting["id"],
    ]

    fetched = client.get(f"/api/cases/ghostings/{ghosting['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["from_ref"] == "OP"

    invalid_update = client.patch(
        f"/api/cases/ghostings/{ghosting['id']}",
        json={"ghosting_type": None},
    )
    assert invalid_update.status_code == 422

    updated = client.patch(
        f"/api/cases/ghostings/{ghosting['id']}",
        json={"ghosting_type": "Ghosting a Spread", "notes": "Updated note"},
    )
    assert updated.status_code == 200
    assert updated.json()["ghosting_type"] == "Ghosting a Spread"
    assert updated.json()["notes"] == "Updated note"

    deleted = client.delete(f"/api/cases/ghostings/{ghosting['id']}")
    assert deleted.status_code == 204
    assert client.get(f"/api/cases/ghostings/{ghosting['id']}").status_code == 404


def test_arrow_link_crud_and_validation(client: TestClient):
    case = client.post("/api/cases/", json={"patient_name": "Analytics Index"}).json()
    client.post(
        f"/api/cases/{case['id']}/partners",
        json={"name": "Partner One", "treatment_date": "2024-01-03"},
    )
    client.post(
        f"/api/cases/{case['id']}/partners",
        json={"name": "Partner Two", "treatment_date": "2024-04-01"},
    )

    created = client.post(
        f"/api/cases/{case['id']}/links",
        json={"from_ref": "OP", "to_ref": "1"},
    )
    assert created.status_code == 201
    link = created.json()
    assert link["case_id"] == case["id"]
    assert link["from_ref"] == "OP"
    assert link["to_ref"] == "1"

    duplicate = client.post(
        f"/api/cases/{case['id']}/links",
        json={"from_ref": "OP", "to_ref": "1"},
    )
    assert duplicate.status_code == 409

    invalid_self = client.post(
        f"/api/cases/{case['id']}/links",
        json={"from_ref": "1", "to_ref": "1"},
    )
    assert invalid_self.status_code == 422
    assert "cannot link to themselves" in " ".join(invalid_self.json()["detail"])

    invalid_ref = client.post(
        f"/api/cases/{case['id']}/links",
        json={"from_ref": "OP", "to_ref": "99"},
    )
    assert invalid_ref.status_code == 422
    assert "Invalid link reference" in invalid_ref.json()["detail"]

    listed = client.get(f"/api/cases/{case['id']}/links")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [link["id"]]

    fetched = client.get(f"/api/cases/links/{link['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["from_ref"] == "OP"

    deleted = client.delete(f"/api/cases/links/{link['id']}")
    assert deleted.status_code == 204
    assert client.get(f"/api/cases/links/{link['id']}").status_code == 404


def test_case_analytics_summary_endpoint(client: TestClient):
    case = client.post(
        "/api/cases/",
        json={
            "patient_name": "Network Index",
            "initial_contact_date": "2024-01-01",
        },
    ).json()
    first_partner = client.post(
        f"/api/cases/{case['id']}/partners",
        json={"name": "Partner One", "treatment_date": "2024-01-03"},
    ).json()
    second_partner = client.post(
        f"/api/cases/{case['id']}/partners",
        json={"name": "Partner Two", "treatment_date": "2024-04-01"},
    ).json()

    link_one = client.post(
        f"/api/cases/{case['id']}/links",
        json={"from_ref": "OP", "to_ref": str(first_partner["partner_number"])},
    )
    assert link_one.status_code == 201

    link_two = client.post(
        f"/api/cases/{case['id']}/links",
        json={
            "from_ref": str(first_partner["partner_number"]),
            "to_ref": str(second_partner["partner_number"]),
        },
    )
    assert link_two.status_code == 201

    response = client.get(f"/api/cases/{case['id']}/analytics")
    assert response.status_code == 200
    payload = response.json()

    assert payload["case_id"] == case["id"]
    assert payload["node_count"] == 3
    assert payload["edge_count"] == 2
    assert [item["ref"] for item in payload["nodes"]] == ["OP", "1", "2"]
    assert [item["node_ref"] for item in payload["centralities"]] == ["OP", "1", "2"]
    assert len(payload["clusters"]["components"]) == 1
    assert payload["clusters"]["cliques"] == []

    filtered = client.get(
        f"/api/cases/{case['id']}/analytics",
        params={"as_of_date": "2024-02-01"},
    )
    assert filtered.status_code == 200
    filtered_payload = filtered.json()

    assert filtered_payload["as_of_date"] == "2024-02-01"
    assert filtered_payload["node_count"] == 2
    assert filtered_payload["edge_count"] == 1
    assert [item["ref"] for item in filtered_payload["nodes"]] == ["OP", "1"]
    assert [item["node_ref"] for item in filtered_payload["centralities"]] == [
        "OP",
        "1",
    ]


def test_map_catalog_endpoint(client: TestClient):
    response = client.get("/api/map/items")
    assert response.status_code == 200
    payload = response.json()

    assert payload["section_order"] == [
        "Social History",
        "Medical History",
        "Partners",
        "Clusters",
        "Risk Reduction",
        "Other",
    ]
    assert payload["items"][0] == {
        "item_number": 1,
        "section": "Social History",
        "label": "Confirm Address",
    }
    assert len(payload["items"]) == 34


def test_case_map_sheet_roundtrip_and_clear(client: TestClient):
    case = client.post("/api/cases/", json={"patient_name": "MAP Index"}).json()

    initial = client.get(f"/api/cases/{case['id']}/map")
    assert initial.status_code == 200
    initial_payload = initial.json()
    assert initial_payload["subject_label"] == "OP — MAP Index"
    assert initial_payload["summary"] == {
        "total_items": 34,
        "checked_p": 0,
        "checked_c": 0,
        "high_priority_flags": 0,
    }
    assert initial_payload["high_priority_comment"] == ""

    updated = client.put(
        f"/api/cases/{case['id']}/map",
        json={
            "items": [
                {
                    "item_number": 1,
                    "p_value": True,
                    "notes": "Verified during intake",
                },
                {
                    "item_number": 12,
                    "c_value": True,
                    "high_priority": True,
                    "notes": "Current exam reason clarified",
                },
            ],
            "high_priority_comment": "Supervisor follow-up needed.",
        },
    )
    assert updated.status_code == 200
    updated_payload = updated.json()
    item_one = next(
        item for item in updated_payload["items"] if item["item_number"] == 1
    )
    item_twelve = next(
        item for item in updated_payload["items"] if item["item_number"] == 12
    )
    assert item_one["p_value"] is True
    assert item_one["notes"] == "Verified during intake"
    assert item_twelve["c_value"] is True
    assert item_twelve["high_priority"] is True
    assert updated_payload["high_priority_comment"] == "Supervisor follow-up needed."
    assert updated_payload["summary"] == {
        "total_items": 34,
        "checked_p": 1,
        "checked_c": 1,
        "high_priority_flags": 1,
    }

    fetched = client.get(f"/api/cases/{case['id']}/map")
    assert fetched.status_code == 200
    assert fetched.json()["summary"]["high_priority_flags"] == 1

    cleared = client.delete(f"/api/cases/{case['id']}/map")
    assert cleared.status_code == 204

    after_clear = client.get(f"/api/cases/{case['id']}/map")
    assert after_clear.status_code == 200
    after_clear_payload = after_clear.json()
    assert after_clear_payload["high_priority_comment"] == ""
    assert after_clear_payload["summary"] == {
        "total_items": 34,
        "checked_p": 0,
        "checked_c": 0,
        "high_priority_flags": 0,
    }


def test_partner_map_sheet_scoping_and_validation(client: TestClient):
    case = client.post("/api/cases/", json={"patient_name": "Partner MAP Index"}).json()
    partner = client.post(
        f"/api/cases/{case['id']}/partners",
        json={"name": "Partner MAP Subject"},
    ).json()

    updated = client.put(
        f"/api/cases/{case['id']}/partners/{partner['id']}/map",
        json={
            "items": [
                {
                    "item_number": 21,
                    "p_value": True,
                    "c_value": True,
                    "high_priority": True,
                    "notes": "Exposure gap discussed",
                }
            ],
            "high_priority_comment": "Escalate partner follow-up.",
        },
    )
    assert updated.status_code == 200
    payload = updated.json()
    assert payload["partner_id"] == partner["id"]
    assert payload["subject_label"] == "Partner 1 — Partner MAP Subject"
    assert payload["summary"] == {
        "total_items": 34,
        "checked_p": 1,
        "checked_c": 1,
        "high_priority_flags": 1,
    }

    op_sheet = client.get(f"/api/cases/{case['id']}/map")
    assert op_sheet.status_code == 200
    assert op_sheet.json()["summary"]["checked_p"] == 0
    assert op_sheet.json()["high_priority_comment"] == ""

    duplicate_item = client.put(
        f"/api/cases/{case['id']}/partners/{partner['id']}/map",
        json={
            "items": [
                {"item_number": 21, "p_value": False},
                {"item_number": 21, "c_value": True},
            ]
        },
    )
    assert duplicate_item.status_code == 422
    assert "Duplicate MAP item 21" in duplicate_item.json()["detail"]

    invalid_item = client.put(
        f"/api/cases/{case['id']}/partners/{partner['id']}/map",
        json={"items": [{"item_number": 8, "p_value": True}]},
    )
    assert invalid_item.status_code == 422
    assert "Unsupported MAP item number" in invalid_item.json()["detail"]

    persisted = client.get(f"/api/cases/{case['id']}/partners/{partner['id']}/map")
    assert persisted.status_code == 200
    persisted_item = next(
        item for item in persisted.json()["items"] if item["item_number"] == 21
    )
    assert persisted_item["p_value"] is True
    assert persisted_item["c_value"] is True

    cleared = client.delete(f"/api/cases/{case['id']}/partners/{partner['id']}/map")
    assert cleared.status_code == 204
    after_clear = client.get(f"/api/cases/{case['id']}/partners/{partner['id']}/map")
    assert after_clear.status_code == 200
    assert after_clear.json()["summary"]["checked_p"] == 0


def test_delete_case_endpoint(client: TestClient):
    created = client.post("/api/cases/", json={"patient_name": "Delete Me"}).json()

    delete_response = client.delete(f"/api/cases/{created['id']}")
    assert delete_response.status_code == 204

    get_response = client.get(f"/api/cases/{created['id']}")
    assert get_response.status_code == 404
