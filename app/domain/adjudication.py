from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.domain.enums import DecisionCode, LineItemStatus
from app.domain.explanations import build_line_item_explanation

MONEY_QUANT = Decimal("0.01")
ZERO = Decimal("0.00")


@dataclass(frozen=True)
class CoverageRuleInput:
    coverage_type: str
    annual_limit: Decimal
    deductible_amount: Decimal
    covered: bool


@dataclass(frozen=True)
class UsageInput:
    paid_amount_used: Decimal
    deductible_amount_satisfied: Decimal


@dataclass(frozen=True)
class AdjudicationResult:
    coverage_type: str
    submitted_amount: Decimal
    deductible_applied: Decimal
    eligible_amount: Decimal
    approved_amount: Decimal
    member_responsibility: Decimal
    remaining_annual_limit_before_claim: Decimal
    remaining_annual_limit_after_claim: Decimal
    status: LineItemStatus
    decision_code: DecisionCode
    message: str


def q(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def adjudicate_line_item(
    *,
    coverage_type: str,
    submitted_amount: Decimal,
    rule: CoverageRuleInput | None,
    usage: UsageInput,
) -> AdjudicationResult:
    submitted_amount = q(submitted_amount)
    paid_amount_used = q(usage.paid_amount_used)
    deductible_satisfied = q(usage.deductible_amount_satisfied)

    if rule is None or not rule.covered:
        return _result(
            coverage_type=coverage_type,
            submitted_amount=submitted_amount,
            deductible_applied=ZERO,
            eligible_amount=ZERO,
            approved_amount=ZERO,
            member_responsibility=submitted_amount,
            remaining_before=ZERO,
            remaining_after=ZERO,
            status=LineItemStatus.DENIED,
            decision_code=DecisionCode.DENIED_NOT_COVERED,
        )

    annual_limit = q(rule.annual_limit)
    deductible_amount = q(rule.deductible_amount)
    remaining_limit_before = max(annual_limit - paid_amount_used, ZERO)
    remaining_deductible = max(deductible_amount - deductible_satisfied, ZERO)
    deductible_applied = min(submitted_amount, remaining_deductible)
    eligible_amount = max(submitted_amount - deductible_applied, ZERO)
    approved_amount = min(eligible_amount, remaining_limit_before)
    member_responsibility = submitted_amount - approved_amount
    remaining_limit_after = max(remaining_limit_before - approved_amount, ZERO)

    if approved_amount == submitted_amount:
        status = LineItemStatus.APPROVED
        decision_code = DecisionCode.COVERED_FULLY
    elif approved_amount == ZERO:
        status = LineItemStatus.DENIED
        if eligible_amount == ZERO and deductible_applied > ZERO:
            decision_code = DecisionCode.DENIED_DEDUCTIBLE_NOT_MET
        else:
            decision_code = DecisionCode.DENIED_LIMIT_EXHAUSTED
    else:
        status = LineItemStatus.PARTIALLY_APPROVED
        deductible_hit = deductible_applied > ZERO
        limit_hit = approved_amount < eligible_amount
        if deductible_hit and limit_hit:
            decision_code = DecisionCode.PARTIAL_DEDUCTIBLE_AND_LIMIT
        elif deductible_hit:
            decision_code = DecisionCode.PARTIAL_DEDUCTIBLE_APPLIED
        else:
            decision_code = DecisionCode.PARTIAL_LIMIT_REMAINING

    return _result(
        coverage_type=coverage_type,
        submitted_amount=submitted_amount,
        deductible_applied=deductible_applied,
        eligible_amount=eligible_amount,
        approved_amount=approved_amount,
        member_responsibility=member_responsibility,
        remaining_before=remaining_limit_before,
        remaining_after=remaining_limit_after,
        status=status,
        decision_code=decision_code,
    )


def _result(
    *,
    coverage_type: str,
    submitted_amount: Decimal,
    deductible_applied: Decimal,
    eligible_amount: Decimal,
    approved_amount: Decimal,
    member_responsibility: Decimal,
    remaining_before: Decimal,
    remaining_after: Decimal,
    status: LineItemStatus,
    decision_code: DecisionCode,
) -> AdjudicationResult:
    message = build_line_item_explanation(
        coverage_type=coverage_type,
        submitted_amount=submitted_amount,
        deductible_applied=deductible_applied,
        eligible_amount=eligible_amount,
        approved_amount=approved_amount,
        member_responsibility=member_responsibility,
        remaining_annual_limit_before_claim=remaining_before,
        remaining_annual_limit_after_claim=remaining_after,
        status=status,
        decision_code=decision_code,
    )
    return AdjudicationResult(
        coverage_type=coverage_type,
        submitted_amount=submitted_amount,
        deductible_applied=q(deductible_applied),
        eligible_amount=q(eligible_amount),
        approved_amount=q(approved_amount),
        member_responsibility=q(member_responsibility),
        remaining_annual_limit_before_claim=q(remaining_before),
        remaining_annual_limit_after_claim=q(remaining_after),
        status=status,
        decision_code=decision_code,
        message=message,
    )
