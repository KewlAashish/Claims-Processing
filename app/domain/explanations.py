from decimal import Decimal

from app.domain.enums import DecisionCode, LineItemStatus


def money(value: Decimal) -> str:
    return f"{value:.2f}"


def build_line_item_explanation(
    *,
    coverage_type: str,
    submitted_amount: Decimal,
    deductible_applied: Decimal,
    eligible_amount: Decimal,
    approved_amount: Decimal,
    member_responsibility: Decimal,
    remaining_annual_limit_before_claim: Decimal,
    remaining_annual_limit_after_claim: Decimal,
    status: LineItemStatus,
    decision_code: DecisionCode,
) -> str:
    if decision_code == DecisionCode.DENIED_NOT_COVERED:
        return (
            f"Denied. {coverage_type} is not covered by the policy, so the "
            f"submitted amount of {money(submitted_amount)} is the member's responsibility."
        )

    if decision_code == DecisionCode.DENIED_LIMIT_EXHAUSTED:
        return (
            f"Denied. The remaining annual {coverage_type} limit before this claim was "
            f"{money(remaining_annual_limit_before_claim)}, so no reimbursement is available."
        )

    if decision_code == DecisionCode.DENIED_DEDUCTIBLE_NOT_MET:
        return (
            f"Denied. The submitted amount was {money(submitted_amount)} and "
            f"{money(deductible_applied)} was applied to the remaining {coverage_type} "
            "deductible, leaving no eligible reimbursable amount."
        )

    prefix = "Approved" if status == LineItemStatus.APPROVED else "Partially approved"
    message = (
        f"{prefix}. The submitted amount was {money(submitted_amount)}. "
        f"{money(deductible_applied)} was applied to the remaining {coverage_type} "
        f"deductible, leaving {money(eligible_amount)} eligible for reimbursement. "
        f"The remaining annual {coverage_type} limit before this claim was "
        f"{money(remaining_annual_limit_before_claim)}, so {money(approved_amount)} "
        f"was approved."
    )

    if member_responsibility > Decimal("0"):
        message += f" The member responsibility is {money(member_responsibility)}."

    if remaining_annual_limit_after_claim == Decimal("0"):
        message += f" The annual {coverage_type} limit is now exhausted."

    return message
