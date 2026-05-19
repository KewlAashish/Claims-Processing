from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output"


def money(value: Any) -> str:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return str(value)
    return f"${amount:,.2f}"


def status_badge(value: Any) -> str:
    return str(value).replace("_", " ").title()


class StagePrinter:
    def __init__(self, title: str, *, base_url: str) -> None:
        self.title = title
        self.base_url = base_url
        self.step_count = 0

    def header(self) -> None:
        line = "=" * 72
        print(f"\n{line}")
        print(f"{self.title}")
        print(f"API: {self.base_url}")
        print(f"{line}")

    def stage(self, title: str, details: list[str] | None = None) -> None:
        self.step_count += 1
        print(f"\n[{self.step_count}] {title}")
        print("-" * (len(title) + 4))
        for detail in details or []:
            print(f"    {detail}")

    def claim_summary(self, claim: dict[str, Any], *, label: str = "Claim result") -> None:
        print(f"\n{label}")
        print(f"    Claim ID: {claim['id']}")
        print(f"    Status:   {status_badge(claim['status'])}")
        for item in claim["line_items"]:
            print(
                "    Line:     "
                f"{item['coverage_type']} | {status_badge(item['status'])} | "
                f"{item['decision_code']} | approved {money(item['approved_amount'])} "
                f"of {money(item['submitted_amount'])}"
            )
            print(f"              {item['explanation']}")

    def success(self, report_path: Path) -> None:
        print("\nDone")
        print(f"    Report: {report_path}")


@dataclass
class ScenarioReport:
    title: str
    scenario_name: str
    run_id: str
    base_url: str
    sections: list[tuple[str, list[str]]] = field(default_factory=list)
    claims: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    disputes: list[dict[str, Any]] = field(default_factory=list)

    def add_section(self, title: str, lines: list[str]) -> None:
        self.sections.append((title, lines))

    def add_claim(self, title: str, claim: dict[str, Any]) -> None:
        self.claims.append((title, claim))

    def add_dispute(self, dispute: dict[str, Any]) -> None:
        self.disputes.append(dispute)

    def write(self) -> Path:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        path = OUTPUT_DIR / f"{self.scenario_name}-{timestamp}.md"
        path.write_text(self._markdown(), encoding="utf-8")
        return path

    def _markdown(self) -> str:
        lines = [
            f"# {self.title}",
            "",
            f"- Run ID: `{self.run_id}`",
            f"- API: `{self.base_url}`",
            f"- Generated At UTC: `{datetime.utcnow().isoformat(timespec='seconds')}Z`",
            "",
        ]

        for title, body_lines in self.sections:
            lines.extend([f"## {title}", ""])
            lines.extend(f"- {line}" for line in body_lines)
            lines.append("")

        for title, claim in self.claims:
            lines.extend(_claim_markdown(title, claim))

        if self.disputes:
            lines.extend(["## Disputes", ""])
            for dispute in self.disputes:
                lines.extend(
                    [
                        f"- Dispute ID: `{dispute['id']}`",
                        f"  - Status: `{dispute['status']}`",
                        f"  - Reason: {dispute['reason']}",
                    ]
                )
            lines.append("")

        return "\n".join(lines).rstrip() + "\n"


def _claim_markdown(title: str, claim: dict[str, Any]) -> list[str]:
    lines = [
        f"## {title}",
        "",
        f"- Claim ID: `{claim['id']}`",
        f"- Status: `{claim['status']}`",
        f"- Member ID: `{claim['member_id']}`",
        f"- Policy ID: `{claim['policy_id']}`",
        "",
        "| Coverage | Status | Decision | Submitted | Deductible | Approved | Member Owes |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for item in claim["line_items"]:
        lines.append(
            f"| {item['coverage_type']} | {item['status']} | {item['decision_code']} | "
            f"{money(item['submitted_amount'])} | {money(item['deductible_applied'])} | "
            f"{money(item['approved_amount'])} | {money(item['member_responsibility'])} |"
        )
    lines.extend(["", "### Explanations", ""])
    for item in claim["line_items"]:
        lines.append(f"- `{item['coverage_type']}`: {item['explanation']}")
    lines.append("")
    return lines
