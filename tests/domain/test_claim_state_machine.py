import pytest

from app.domain.enums import ClaimStatus, LineItemStatus
from app.domain.state_machine import (
    ClaimTransitionError,
    aggregate_claim_status,
    dispute_claim,
    pay_claim,
)


def test_all_approved_line_items_aggregate_to_approved() -> None:
    assert aggregate_claim_status([LineItemStatus.APPROVED]) == ClaimStatus.APPROVED


def test_all_denied_line_items_aggregate_to_denied() -> None:
    assert (
        aggregate_claim_status([LineItemStatus.DENIED, LineItemStatus.DENIED]) == ClaimStatus.DENIED
    )


def test_mixed_line_item_results_aggregate_to_partially_approved() -> None:
    assert (
        aggregate_claim_status([LineItemStatus.APPROVED, LineItemStatus.DENIED])
        == ClaimStatus.PARTIALLY_APPROVED
    )


def test_paid_transition_only_allows_approved_or_partial_claims() -> None:
    assert pay_claim(ClaimStatus.APPROVED) == ClaimStatus.PAID
    assert pay_claim(ClaimStatus.PARTIALLY_APPROVED) == ClaimStatus.PAID

    with pytest.raises(ClaimTransitionError):
        pay_claim(ClaimStatus.DENIED)


def test_dispute_transition_rejects_submitted_and_under_review_claims() -> None:
    assert dispute_claim(ClaimStatus.DENIED) == ClaimStatus.DISPUTED

    with pytest.raises(ClaimTransitionError):
        dispute_claim(ClaimStatus.SUBMITTED)

    with pytest.raises(ClaimTransitionError):
        dispute_claim(ClaimStatus.UNDER_REVIEW)
