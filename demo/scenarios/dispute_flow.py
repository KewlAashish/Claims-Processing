from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from demo.lib.api_client import ClaimsDemoClient, DemoApiError
from demo.lib.rendering import ScenarioReport, StagePrinter, money, status_badge
from demo.lib.scenario_support import claim_payload, create_member_policy_case, run_id

SCENARIO_NAME = "dispute-flow"
TITLE = "Dispute Flow Demo"


def main() -> int:
    client = ClaimsDemoClient()
    printer = StagePrinter(TITLE, base_url=client.base_url)
    run_id_value = run_id("dispute")
    report = ScenarioReport(TITLE, SCENARIO_NAME, run_id_value, client.base_url)

    try:
        printer.header()
        client.check_health()
        printer.stage("API health check", ["Service is reachable."])

        case = create_member_policy_case(
            client,
            run_id_value=run_id_value,
            member_name="Kabir Shah",
            policy_name="Member Advocacy Plan",
            coverage_rules=[
                {
                    "coverage_type": "OPD",
                    "annual_limit": "2000",
                    "deductible_amount": "300",
                    "covered": True,
                }
            ],
        )
        printer.stage(
            "Created dispute-ready setup",
            [
                f"Member ID: {case['member']['id']}",
                f"Policy ID: {case['policy']['id']}",
                "OPD has a deductible, creating a decision the member can dispute.",
            ],
        )
        report.add_section(
            "Setup",
            [
                f"Member `{case['member']['id']}` was enrolled in policy `{case['policy']['id']}`.",
                "Coverage rule: OPD, annual limit $2,000, deductible $300, covered.",
            ],
        )

        claim = client.submit_claim(
            claim_payload(
                member_id=case["member"]["id"],
                policy_id=case["policy"]["id"],
                coverage_type="OPD",
                amount="900",
                description="Clinic visit and lab panel",
            )
        )
        printer.stage(
            "Submitted decided claim",
            [
                f"Submitted amount: {money('900')}",
                f"Initial status: {status_badge(claim['status'])}",
            ],
        )
        printer.claim_summary(claim)
        report.add_claim("Original Claim Decision", claim)

        dispute = client.create_dispute(
            claim["id"],
            "Member says the provider submitted additional supporting records.",
        )
        disputed_claim = client.get_claim(claim["id"])
        printer.stage(
            "Opened dispute",
            [
                f"Dispute ID: {dispute['id']}",
                f"Final claim status: {status_badge(disputed_claim['status'])}",
            ],
        )
        printer.claim_summary(disputed_claim, label="Disputed claim")
        report.add_dispute(dispute)
        report.add_claim("Disputed Claim", disputed_claim)

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
