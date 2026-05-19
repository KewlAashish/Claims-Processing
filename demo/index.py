from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from demo.lib.api_client import ClaimsDemoClient, DemoApiError

SCENARIOS = [
    ("approved_claim", "Fully approved claim, then payment"),
    ("partial_deductible", "Partial approval because deductible remains"),
    ("partial_limit", "Partial approval because annual limit caps reimbursement"),
    ("denied_not_covered", "Denied claim for an uncovered benefit"),
    ("dispute_flow", "Decided claim moved into dispute"),
]


def main() -> int:
    client = ClaimsDemoClient()
    try:
        client.check_health()
        api_status = "reachable"
    except DemoApiError as exc:
        api_status = f"not reachable: {exc}"
    finally:
        client.close()

    print("\nClaims Processing HTTP Demo")
    print("=" * 72)
    print(f"API base URL: {client.base_url}")
    print(f"API status:   {api_status}")
    print("\nStart the API if needed:")
    print("    uvicorn app.main:app --reload")
    print("\nRun a scenario:")
    for name, description in SCENARIOS:
        print(f"    python demo/scenarios/{name}.py")
        print(f"        {description}")
    print("\nGenerated reports are written to demo/output/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
