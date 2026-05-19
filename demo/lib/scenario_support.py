from __future__ import annotations

from datetime import datetime
from typing import Any

from demo.lib.api_client import ClaimsDemoClient

POLICY_START_DATE = "2026-01-01"
POLICY_END_DATE = "2026-12-31"
MEMBER_DOB = "1990-01-01"


def run_id(prefix: str) -> str:
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    return f"{prefix}-{stamp}"


def create_member_policy_case(
    client: ClaimsDemoClient,
    *,
    run_id_value: str,
    member_name: str,
    policy_name: str,
    coverage_rules: list[dict[str, Any]],
) -> dict[str, Any]:
    member = client.create_member(
        {
            "full_name": member_name,
            "date_of_birth": MEMBER_DOB,
            "external_member_id": f"MEM-{run_id_value}",
        }
    )
    policy = client.create_policy(
        {
            "policy_number": f"POL-{run_id_value}",
            "name": policy_name,
            "effective_start_date": POLICY_START_DATE,
            "effective_end_date": POLICY_END_DATE,
        }
    )
    rules = [client.add_coverage_rule(policy["id"], rule) for rule in coverage_rules]
    enrollment = client.enroll_member(
        member["id"],
        {
            "policy_id": policy["id"],
            "effective_start_date": POLICY_START_DATE,
            "effective_end_date": POLICY_END_DATE,
        },
    )
    return {
        "member": member,
        "policy": policy,
        "rules": rules,
        "enrollment": enrollment,
    }


def claim_payload(
    *,
    member_id: str,
    policy_id: str,
    coverage_type: str,
    amount: str,
    description: str,
    service_date: str = "2026-03-15",
    diagnosis_code: str = "J10",
    provider_name: str = "City Clinic",
) -> dict[str, Any]:
    return {
        "member_id": member_id,
        "policy_id": policy_id,
        "diagnosis_code": diagnosis_code,
        "provider_name": provider_name,
        "line_items": [
            {
                "coverage_type": coverage_type,
                "service_date": service_date,
                "description": description,
                "submitted_amount": amount,
            }
        ],
    }
