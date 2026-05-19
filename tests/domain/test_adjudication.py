from decimal import Decimal

from app.domain.adjudication import CoverageRuleInput, UsageInput, adjudicate_line_item
from app.domain.enums import DecisionCode, LineItemStatus


def test_uncovered_coverage_type_is_denied() -> None:
    result = adjudicate_line_item(
        coverage_type="DENTAL",
        submitted_amount=Decimal("500"),
        rule=CoverageRuleInput(
            coverage_type="DENTAL",
            annual_limit=Decimal("1000"),
            deductible_amount=Decimal("100"),
            covered=False,
        ),
        usage=UsageInput(
            paid_amount_used=Decimal("0"),
            deductible_amount_satisfied=Decimal("0"),
        ),
    )

    assert result.status == LineItemStatus.DENIED
    assert result.decision_code == DecisionCode.DENIED_NOT_COVERED
    assert result.approved_amount == Decimal("0.00")
    assert "not covered" in result.message


def test_deductible_absorbs_full_amount() -> None:
    result = adjudicate_line_item(
        coverage_type="OPD",
        submitted_amount=Decimal("300"),
        rule=CoverageRuleInput(
            coverage_type="OPD",
            annual_limit=Decimal("10000"),
            deductible_amount=Decimal("1000"),
            covered=True,
        ),
        usage=UsageInput(
            paid_amount_used=Decimal("0"),
            deductible_amount_satisfied=Decimal("500"),
        ),
    )

    assert result.status == LineItemStatus.DENIED
    assert result.decision_code == DecisionCode.DENIED_DEDUCTIBLE_NOT_MET
    assert result.deductible_applied == Decimal("300.00")
    assert result.eligible_amount == Decimal("0.00")


def test_deductible_partially_applies_and_remaining_amount_is_approved() -> None:
    result = adjudicate_line_item(
        coverage_type="OPD",
        submitted_amount=Decimal("2000"),
        rule=CoverageRuleInput(
            coverage_type="OPD",
            annual_limit=Decimal("10000"),
            deductible_amount=Decimal("1000"),
            covered=True,
        ),
        usage=UsageInput(
            paid_amount_used=Decimal("2000"),
            deductible_amount_satisfied=Decimal("600"),
        ),
    )

    assert result.status == LineItemStatus.PARTIALLY_APPROVED
    assert result.decision_code == DecisionCode.PARTIAL_DEDUCTIBLE_APPLIED
    assert result.deductible_applied == Decimal("400.00")
    assert result.eligible_amount == Decimal("1600.00")
    assert result.approved_amount == Decimal("1600.00")
    assert result.remaining_annual_limit_before_claim == Decimal("8000.00")
    assert result.remaining_annual_limit_after_claim == Decimal("6400.00")


def test_annual_limit_caps_reimbursement() -> None:
    result = adjudicate_line_item(
        coverage_type="RX",
        submitted_amount=Decimal("700"),
        rule=CoverageRuleInput(
            coverage_type="RX",
            annual_limit=Decimal("1000"),
            deductible_amount=Decimal("0"),
            covered=True,
        ),
        usage=UsageInput(
            paid_amount_used=Decimal("600"),
            deductible_amount_satisfied=Decimal("0"),
        ),
    )

    assert result.status == LineItemStatus.PARTIALLY_APPROVED
    assert result.decision_code == DecisionCode.PARTIAL_LIMIT_REMAINING
    assert result.approved_amount == Decimal("400.00")
    assert result.member_responsibility == Decimal("300.00")


def test_exhausted_annual_limit_denies_line_item() -> None:
    result = adjudicate_line_item(
        coverage_type="RX",
        submitted_amount=Decimal("100"),
        rule=CoverageRuleInput(
            coverage_type="RX",
            annual_limit=Decimal("1000"),
            deductible_amount=Decimal("0"),
            covered=True,
        ),
        usage=UsageInput(
            paid_amount_used=Decimal("1000"),
            deductible_amount_satisfied=Decimal("0"),
        ),
    )

    assert result.status == LineItemStatus.DENIED
    assert result.decision_code == DecisionCode.DENIED_LIMIT_EXHAUSTED
    assert result.approved_amount == Decimal("0.00")
