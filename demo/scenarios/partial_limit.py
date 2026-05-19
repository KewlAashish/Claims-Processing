from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from demo.lib.api_client import ClaimsDemoClient, DemoApiError
from demo.lib.rendering import ScenarioReport, StagePrinter, money, status_badge
from demo.lib.scenario_support import claim_payload, create_member_policy_case, run_id

SCENARIO_NAME = "partial-limit"
TITLE = "Partial Approval From Annual Limit Demo"


def main() -> int:
    client = ClaimsDemoClient()
    printer = StagePrinter(TITLE, base_url=client.base_url)
    run_id_value = run_id("limit")
    report = ScenarioReport(TITLE, SCENARIO_NAME, run_id_value, client.base_url)

    try:
        printer.header()
        client.check_health()
        printer.stage("API health check", ["Service is reachable."])

        case = create_member_policy_case(
            client,
            run_id_value=run_id_value,
            member_name="Maya Iyer",
            policy_name="Pharmacy Limit Plan",
            coverage_rules=[
                {
                    "coverage_type": "RX",
                    "annual_limit": "1000",
                    "deductible_amount": "0",
                    "covered": True,
                }
            ],
        )
        printer.stage(
            "Created annual-limit setup",
            [
                f"Member ID: {case['member']['id']}",
                f"Policy ID: {case['policy']['id']}",
                "RX has a $1,000 annual limit and no deductible.",
            ],
        )
        report.add_section(
            "Setup",
            [
                f"Member `{case['member']['id']}` was enrolled in policy `{case['policy']['id']}`.",
                "Coverage rule: RX, annual limit $1,000, deductible $0, covered.",
            ],
        )

        prior_claim = client.submit_claim(
            claim_payload(
                member_id=case["member"]["id"],
                policy_id=case["policy"]["id"],
                coverage_type="RX",
                amount="700",
                description="Prior prescription refill",
                service_date="2026-02-10",
            )
        )
        printer.stage(
            "Created prior usage through the API",
            [
                "Prior claim approved amount: "
                f"{money(prior_claim['line_items'][0]['approved_amount'])}",
                "This consumes part of the annual RX limit before the demo claim.",
            ],
        )
        report.add_claim("Prior Usage Claim", prior_claim)

        claim = client.submit_claim(
            claim_payload(
                member_id=case["member"]["id"],
                policy_id=case["policy"]["id"],
                coverage_type="RX",
                amount="600",
                description="New prescription refill",
                service_date="2026-03-20",
            )
        )
        printer.stage(
            "Submitted annual-limit claim",
            [
                f"Submitted amount: {money('600')}",
                f"Adjudicated status: {status_badge(claim['status'])}",
            ],
        )
        printer.claim_summary(claim)
        report.add_claim("Annual Limit Claim", claim)

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
