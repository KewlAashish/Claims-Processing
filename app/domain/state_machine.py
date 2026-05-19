from app.domain.enums import ClaimStatus, LineItemStatus


class ClaimTransitionError(ValueError):
    pass


def aggregate_claim_status(line_statuses: list[LineItemStatus]) -> ClaimStatus:
    if not line_statuses:
        raise ValueError("At least one line item is required")

    unique_statuses = set(line_statuses)
    if unique_statuses == {LineItemStatus.APPROVED}:
        return ClaimStatus.APPROVED
    if unique_statuses == {LineItemStatus.DENIED}:
        return ClaimStatus.DENIED
    return ClaimStatus.PARTIALLY_APPROVED


def pay_claim(status: ClaimStatus) -> ClaimStatus:
    if status in {ClaimStatus.APPROVED, ClaimStatus.PARTIALLY_APPROVED}:
        return ClaimStatus.PAID
    raise ClaimTransitionError(f"Claim in {status} status cannot be paid")


def dispute_claim(status: ClaimStatus) -> ClaimStatus:
    if status in {ClaimStatus.SUBMITTED, ClaimStatus.UNDER_REVIEW}:
        raise ClaimTransitionError(f"Claim in {status} status cannot be disputed")
    return ClaimStatus.DISPUTED
