from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.main import app
from app.persistence.database import Base, get_session


@pytest.fixture()
def client(tmp_path) -> Generator[TestClient, None, None]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_session() -> Generator[Session, None, None]:
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_get_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_submit_claim_adjudicates_and_persists_usage(client: TestClient) -> None:
    member = client.post(
        "/members",
        json={
            "full_name": "Asha Patel",
            "date_of_birth": "1990-01-01",
            "external_member_id": "MEM-001",
        },
    ).json()
    policy = client.post(
        "/policies",
        json={
            "policy_number": "POL-001",
            "name": "Standard Health",
            "effective_start_date": "2026-01-01",
            "effective_end_date": "2026-12-31",
        },
    ).json()
    client.post(
        f"/policies/{policy['id']}/coverage-rules",
        json={
            "coverage_type": "OPD",
            "annual_limit": "10000",
            "deductible_amount": "1000",
            "covered": True,
        },
    )
    client.post(
        f"/members/{member['id']}/policies",
        json={
            "policy_id": policy["id"],
            "effective_start_date": "2026-01-01",
            "effective_end_date": "2026-12-31",
        },
    )

    response = client.post(
        "/claims",
        json={
            "member_id": member["id"],
            "policy_id": policy["id"],
            "diagnosis_code": "J10",
            "provider_name": "City Clinic",
            "line_items": [
                {
                    "coverage_type": "OPD",
                    "service_date": "2026-03-01",
                    "description": "Consultation",
                    "submitted_amount": "2000",
                }
            ],
        },
    )

    assert response.status_code == 201
    claim = response.json()
    assert claim["status"] == "PARTIALLY_APPROVED"
    assert claim["line_items"][0]["decision_code"] == "PARTIAL_DEDUCTIBLE_APPLIED"
    assert claim["line_items"][0]["deductible_applied"] == "1000.00"
    assert claim["line_items"][0]["approved_amount"] == "1000.00"
    assert "submitted amount" in claim["line_items"][0]["explanation"]


def test_duplicate_line_items_are_rejected(client: TestClient) -> None:
    response = client.post(
        "/claims",
        json={
            "member_id": "member-id",
            "policy_id": "policy-id",
            "diagnosis_code": "J10",
            "provider_name": "City Clinic",
            "line_items": [
                {
                    "coverage_type": "OPD",
                    "service_date": "2026-03-01",
                    "description": "Consultation",
                    "submitted_amount": "2000",
                },
                {
                    "coverage_type": "OPD",
                    "service_date": "2026-03-01",
                    "description": "Consultation",
                    "submitted_amount": "2000",
                },
            ],
        },
    )

    assert response.status_code == 422


def test_unknown_member_cannot_submit_claim(client: TestClient) -> None:
    policy = client.post(
        "/policies",
        json={
            "policy_number": "POL-002",
            "name": "Standard Health",
            "effective_start_date": "2026-01-01",
            "effective_end_date": "2026-12-31",
        },
    ).json()

    response = client.post(
        "/claims",
        json={
            "member_id": "missing",
            "policy_id": policy["id"],
            "diagnosis_code": "J10",
            "provider_name": "City Clinic",
            "line_items": [
                {
                    "coverage_type": "OPD",
                    "service_date": "2026-03-01",
                    "description": "Consultation",
                    "submitted_amount": "2000",
                }
            ],
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "member not found"
