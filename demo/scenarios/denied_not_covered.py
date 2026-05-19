from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from demo.lib.api_client import ClaimsDemoClient, DemoApiError
from demo.lib.rendering import ScenarioReport, StagePrinter, money, status_badge
from demo.lib.scenario_support import claim_payload, create_member_policy_case, run_id

SCENARIO_NAME = "denied-not-covered"
TITLE = "Denied Not Covered Demo"


def main() -> int:
    client = ClaimsDemoClient()
    printer = StagePrinter(TITLE, base_url=client.base_url)
    run_id_value = run_id("denied")
    report = ScenarioReport(TITLE, SCENARIO_NAME, run_id_value, client.base_url)

    try:
        printer.header()
        client.check_health()
        printer.stage("API health check", ["Service is reachable."])

        case = create_member_policy_case(
            client,
            run_id_value=run_id_value,
            member_name="Nisha Rao",
            policy_name="Core Medical Plan",
            coverage_rules=[
                {
                    "coverage_type": "DENTAL",
                    "annual_limit": "0",
                    "deductible_amount": "0",
                    "covered": False,
                }
            ],
        )
        printer.stage(
            "Created uncovered benefit setup",
            [
                f"Member ID: {case['member']['id']}",
                f"Policy ID: {case['policy']['id']}",
                "DENTAL exists on the policy but is explicitly not covered.",
            ],
        )
        report.add_section(
            "Setup",
            [
                f"Member `{case['member']['id']}` was enrolled in policy `{case['policy']['id']}`.",
                "Coverage rule: DENTAL, covered=false.",
            ],
        )

        claim = client.submit_claim(
            claim_payload(
                member_id=case["member"]["id"],
                policy_id=case["policy"]["id"],
                coverage_type="DENTAL",
                amount="450",
                description="Dental cleaning",
                diagnosis_code="K03",
                provider_name="Downtown Dental",
            )
        )
        printer.stage(
            "Submitted uncovered claim",
            [
                f"Submitted amount: {money('450')}",
                f"Adjudicated status: {status_badge(claim['status'])}",
            ],
        )
        printer.claim_summary(claim)
        report.add_claim("Denied Claim", claim)

        report_path = report.write()
        printer.success(report_path)
        return 0
    except DemoApiError as exc:
        print(f"\nDemo failed: {exc}")
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
