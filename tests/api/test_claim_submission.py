from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.main import app
from app.persistence.database import Base, get_session


def create_member_policy_case(
    client: TestClient,
    *,
    policy_number: str = "POL-001",
    coverage_rules: list[dict] | None = None,
    enrollment_start: str = "2026-01-01",
    enrollment_end: str = "2026-12-31",
) -> tuple[dict, dict]:
    member = client.post(
        "/members",
        json={
            "full_name": "Asha Patel",
            "date_of_birth": "1990-01-01",
            "external_member_id": f"MEM-{policy_number}",
        },
    ).json()
    policy = client.post(
        "/policies",
        json={
            "policy_number": policy_number,
            "name": "Standard Health",
            "effective_start_date": "2026-01-01",
            "effective_end_date": "2026-12-31",
        },
    ).json()
    for rule in coverage_rules or []:
        client.post(f"/policies/{policy['id']}/coverage-rules", json=rule)
    client.post(
        f"/members/{member['id']}/policies",
        json={
            "policy_id": policy["id"],
            "effective_start_date": enrollment_start,
            "effective_end_date": enrollment_end,
        },
    )
    return member, policy


def claim_payload(
    *,
    member_id: str,
    policy_id: str,
    line_items: list[dict],
    diagnosis_code: str = "J10",
    provider_name: str = "City Clinic",
) -> dict:
    return {
        "member_id": member_id,
        "policy_id": policy_id,
        "diagnosis_code": diagnosis_code,
        "provider_name": provider_name,
        "line_items": line_items,
    }


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
    member, policy = create_member_policy_case(
        client,
        coverage_rules=[
            {
                "coverage_type": "OPD",
                "annual_limit": "10000",
                "deductible_amount": "1000",
                "covered": True,
            }
        ],
    )

    response = client.post(
        "/claims",
        json=claim_payload(
            member_id=member["id"],
            policy_id=policy["id"],
            line_items=[
                {
                    "coverage_type": "OPD",
                    "service_date": "2026-03-01",
                    "description": "Consultation",
                    "submitted_amount": "2000",
                }
            ],
        ),
    )

    assert response.status_code == 201
    claim = response.json()
    assert claim["status"] == "PARTIALLY_APPROVED"
    assert claim["line_items"][0]["decision_code"] == "PARTIAL_DEDUCTIBLE_APPLIED"
    assert claim["line_items"][0]["deductible_applied"] == "1000.00"
    assert claim["line_items"][0]["approved_amount"] == "1000.00"
    assert "submitted amount" in claim["line_items"][0]["explanation"]


def test_multi_line_claim_consumes_same_coverage_bucket_in_sequence(
    client: TestClient,
) -> None:
    member, policy = create_member_policy_case(
        client,
        policy_number="POL-SEQUENCE",
        coverage_rules=[
            {
                "coverage_type": "OPD",
                "annual_limit": "1000",
                "deductible_amount": "100",
                "covered": True,
            }
        ],
    )

    response = client.post(
        "/claims",
        json=claim_payload(
            member_id=member["id"],
            policy_id=policy["id"],
            line_items=[
                {
                    "coverage_type": "OPD",
                    "service_date": "2026-03-01",
                    "description": "Consultation",
                    "submitted_amount": "600",
                },
                {
                    "coverage_type": "OPD",
                    "service_date": "2026-03-02",
                    "description": "Follow-up treatment",
                    "submitted_amount": "700",
                },
            ],
        ),
    )

    assert response.status_code == 201
    claim = response.json()
    first_line, second_line = claim["line_items"]
    assert claim["status"] == "PARTIALLY_APPROVED"
    assert first_line["approved_amount"] == "500.00"
    assert first_line["deductible_applied"] == "100.00"
    assert first_line["remaining_annual_limit_before_claim"] == "1000.00"
    assert first_line["remaining_annual_limit_after_claim"] == "500.00"
    assert second_line["approved_amount"] == "500.00"
    assert second_line["deductible_applied"] == "0.00"
    assert second_line["decision_code"] == "PARTIAL_LIMIT_REMAINING"
    assert second_line["remaining_annual_limit_before_claim"] == "500.00"
    assert second_line["remaining_annual_limit_after_claim"] == "0.00"


def test_missing_coverage_rule_is_denied_with_explanation(client: TestClient) -> None:
    member, policy = create_member_policy_case(client, policy_number="POL-MISSING-RULE")

    response = client.post(
        "/claims",
        json=claim_payload(
            member_id=member["id"],
            policy_id=policy["id"],
            line_items=[
                {
                    "coverage_type": "VISION",
                    "service_date": "2026-03-01",
                    "description": "Eye exam",
                    "submitted_amount": "250",
                }
            ],
        ),
    )

    assert response.status_code == 201
    claim = response.json()
    assert claim["status"] == "DENIED"
    assert claim["line_items"][0]["decision_code"] == "DENIED_NOT_COVERED"
    assert "not covered" in claim["line_items"][0]["explanation"]


def test_claim_outside_policy_dates_is_rejected(client: TestClient) -> None:
    member, policy = create_member_policy_case(
        client,
        policy_number="POL-OUTSIDE-DATES",
        coverage_rules=[
            {
                "coverage_type": "OPD",
                "annual_limit": "1000",
                "deductible_amount": "0",
                "covered": True,
            }
        ],
    )

    response = client.post(
        "/claims",
        json=claim_payload(
            member_id=member["id"],
            policy_id=policy["id"],
            line_items=[
                {
                    "coverage_type": "OPD",
                    "service_date": "2027-01-01",
                    "description": "Out of policy period visit",
                    "submitted_amount": "100",
                }
            ],
        ),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "policy is inactive or outside the service date"


def test_claim_outside_enrollment_dates_is_rejected(client: TestClient) -> None:
    member, policy = create_member_policy_case(
        client,
        policy_number="POL-OUTSIDE-ENROLLMENT",
        enrollment_start="2026-02-01",
        coverage_rules=[
            {
                "coverage_type": "OPD",
                "annual_limit": "1000",
                "deductible_amount": "0",
                "covered": True,
            }
        ],
    )

    response = client.post(
        "/claims",
        json=claim_payload(
            member_id=member["id"],
            policy_id=policy["id"],
            line_items=[
                {
                    "coverage_type": "OPD",
                    "service_date": "2026-01-15",
                    "description": "Before enrollment visit",
                    "submitted_amount": "100",
                }
            ],
        ),
    )

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "member does not have an active policy enrollment for the service date"
    )


def test_approved_claim_can_be_paid(client: TestClient) -> None:
    member, policy = create_member_policy_case(
        client,
        policy_number="POL-PAYABLE",
        coverage_rules=[
            {
                "coverage_type": "OPD",
                "annual_limit": "1000",
                "deductible_amount": "0",
                "covered": True,
            }
        ],
    )
    claim = client.post(
        "/claims",
        json=claim_payload(
            member_id=member["id"],
            policy_id=policy["id"],
            line_items=[
                {
                    "coverage_type": "OPD",
                    "service_date": "2026-03-01",
                    "description": "Consultation",
                    "submitted_amount": "100",
                }
            ],
        ),
    ).json()

    response = client.post(f"/claims/{claim['id']}/pay")

    assert response.status_code == 200
    assert response.json()["status"] == "PAID"


def test_denied_claim_cannot_be_paid(client: TestClient) -> None:
    member, policy = create_member_policy_case(
        client,
        policy_number="POL-DENIED-PAY",
        coverage_rules=[
            {
                "coverage_type": "DENTAL",
                "annual_limit": "0",
                "deductible_amount": "0",
                "covered": False,
            }
        ],
    )
    claim = client.post(
        "/claims",
        json=claim_payload(
            member_id=member["id"],
            policy_id=policy["id"],
            line_items=[
                {
                    "coverage_type": "DENTAL",
                    "service_date": "2026-03-01",
                    "description": "Dental cleaning",
                    "submitted_amount": "100",
                }
            ],
        ),
    ).json()

    response = client.post(f"/claims/{claim['id']}/pay")

    assert response.status_code == 422
    assert response.json()["detail"] == "Claim in DENIED status cannot be paid"


def test_decided_claim_can_be_disputed(client: TestClient) -> None:
    member, policy = create_member_policy_case(
        client,
        policy_number="POL-DISPUTE",
        coverage_rules=[
            {
                "coverage_type": "OPD",
                "annual_limit": "1000",
                "deductible_amount": "100",
                "covered": True,
            }
        ],
    )
    claim = client.post(
        "/claims",
        json=claim_payload(
            member_id=member["id"],
            policy_id=policy["id"],
            line_items=[
                {
                    "coverage_type": "OPD",
                    "service_date": "2026-03-01",
                    "description": "Consultation",
                    "submitted_amount": "300",
                }
            ],
        ),
    ).json()

    dispute_response = client.post(
        f"/claims/{claim['id']}/disputes",
        json={"reason": "Member believes additional records change the decision."},
    )
    claim_response = client.get(f"/claims/{claim['id']}")

    assert dispute_response.status_code == 201
    assert dispute_response.json()["status"] == "OPEN"
    assert claim_response.json()["status"] == "DISPUTED"
    assert len(claim_response.json()["disputes"]) == 1


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
