from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.adjudication import CoverageRuleInput, UsageInput, adjudicate_line_item
from app.domain.enums import ClaimStatus
from app.domain.state_machine import (
    ClaimTransitionError,
    aggregate_claim_status,
    dispute_claim,
    pay_claim,
)
from app.persistence import models, repositories
from app.schemas.claims import ClaimCreate, ClaimDisputeCreate
from app.services.errors import NotFoundError, ValidationError


def submit_claim(session: Session, payload: ClaimCreate) -> models.Claim:
    member = repositories.get_member(session, payload.member_id)
    if member is None:
        raise NotFoundError("member not found")

    policy = repositories.get_policy(session, payload.policy_id)
    if policy is None:
        raise NotFoundError("policy not found")

    service_dates = [item.service_date for item in payload.line_items]
    if any(
        not repositories.policy_is_active(policy, service_date) for service_date in service_dates
    ):
        raise ValidationError("policy is inactive or outside the service date")

    if any(
        repositories.get_active_enrollment(
            session,
            member_id=payload.member_id,
            policy_id=payload.policy_id,
            service_date=service_date,
        )
        is None
        for service_date in service_dates
    ):
        raise ValidationError(
            "member does not have an active policy enrollment for the service date"
        )

    rules_by_type = repositories.coverage_rule_by_type(session, policy_id=payload.policy_id)
    claim = models.Claim(
        member_id=payload.member_id,
        policy_id=payload.policy_id,
        status=ClaimStatus.UNDER_REVIEW,
        diagnosis_code=payload.diagnosis_code,
        provider_name=payload.provider_name,
    )
    session.add(claim)
    session.flush()

    line_statuses = []
    for item in payload.line_items:
        usage = repositories.get_or_create_usage(
            session,
            member_id=payload.member_id,
            policy_id=payload.policy_id,
            coverage_type=item.coverage_type,
            benefit_year=item.service_date.year,
        )
        rule_model = rules_by_type.get(item.coverage_type)
        rule = (
            CoverageRuleInput(
                coverage_type=rule_model.coverage_type,
                annual_limit=rule_model.annual_limit,
                deductible_amount=rule_model.deductible_amount,
                covered=rule_model.covered,
            )
            if rule_model is not None
            else None
        )
        result = adjudicate_line_item(
            coverage_type=item.coverage_type,
            submitted_amount=item.submitted_amount,
            rule=rule,
            usage=UsageInput(
                paid_amount_used=usage.paid_amount_used,
                deductible_amount_satisfied=usage.deductible_amount_satisfied,
            ),
        )
        session.add(
            models.ClaimLineItem(
                claim_id=claim.id,
                coverage_type=item.coverage_type,
                service_date=item.service_date,
                description=item.description,
                submitted_amount=result.submitted_amount,
                status=result.status,
                decision_code=result.decision_code,
                deductible_applied=result.deductible_applied,
                eligible_amount=result.eligible_amount,
                approved_amount=result.approved_amount,
                member_responsibility=result.member_responsibility,
                remaining_annual_limit_before_claim=result.remaining_annual_limit_before_claim,
                remaining_annual_limit_after_claim=result.remaining_annual_limit_after_claim,
                explanation=result.message,
            )
        )
        usage.paid_amount_used = Decimal(usage.paid_amount_used) + result.approved_amount
        usage.deductible_amount_satisfied = (
            Decimal(usage.deductible_amount_satisfied) + result.deductible_applied
        )
        line_statuses.append(result.status)

    claim.status = aggregate_claim_status(line_statuses)
    claim.decided_at = datetime.utcnow()
    session.commit()
    return get_claim(session, claim.id)


def get_claim(session: Session, claim_id: str) -> models.Claim:
    claim = repositories.get_claim(session, claim_id)
    if claim is None:
        raise NotFoundError("claim not found")
    return claim


def mark_claim_paid(session: Session, claim_id: str) -> models.Claim:
    claim = get_claim(session, claim_id)
    try:
        claim.status = pay_claim(ClaimStatus(claim.status))
    except ClaimTransitionError as exc:
        raise ValidationError(str(exc)) from exc
    session.commit()
    return get_claim(session, claim_id)


def create_dispute(
    session: Session, claim_id: str, payload: ClaimDisputeCreate
) -> models.ClaimDispute:
    claim = get_claim(session, claim_id)
    try:
        claim.status = dispute_claim(ClaimStatus(claim.status))
    except ClaimTransitionError as exc:
        raise ValidationError(str(exc)) from exc

    dispute = models.ClaimDispute(claim_id=claim_id, reason=payload.reason)
    session.add(dispute)
    session.commit()
    session.refresh(dispute)
    return dispute
