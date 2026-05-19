from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.enums import EnrollmentStatus, PolicyStatus
from app.persistence import models


def get_member(session: Session, member_id: str) -> models.Member | None:
    return session.get(models.Member, member_id)


def get_policy(session: Session, policy_id: str) -> models.Policy | None:
    return session.get(models.Policy, policy_id)


def get_claim(session: Session, claim_id: str) -> models.Claim | None:
    statement = (
        select(models.Claim)
        .options(selectinload(models.Claim.line_items), selectinload(models.Claim.disputes))
        .where(models.Claim.id == claim_id)
    )
    return session.scalar(statement)


def get_active_enrollment(
    session: Session, *, member_id: str, policy_id: str, service_date: date
) -> models.MemberPolicy | None:
    statement = select(models.MemberPolicy).where(
        models.MemberPolicy.member_id == member_id,
        models.MemberPolicy.policy_id == policy_id,
        models.MemberPolicy.status == EnrollmentStatus.ACTIVE,
        models.MemberPolicy.effective_start_date <= service_date,
        models.MemberPolicy.effective_end_date >= service_date,
    )
    return session.scalar(statement)


def policy_is_active(policy: models.Policy, service_date: date) -> bool:
    return (
        policy.status == PolicyStatus.ACTIVE
        and policy.effective_start_date <= service_date <= policy.effective_end_date
    )


def coverage_rule_by_type(session: Session, *, policy_id: str) -> dict[str, models.CoverageRule]:
    rules = session.scalars(
        select(models.CoverageRule).where(models.CoverageRule.policy_id == policy_id)
    ).all()
    return {rule.coverage_type: rule for rule in rules}


def get_or_create_usage(
    session: Session,
    *,
    member_id: str,
    policy_id: str,
    coverage_type: str,
    benefit_year: int,
) -> models.CoverageUsage:
    statement = select(models.CoverageUsage).where(
        models.CoverageUsage.member_id == member_id,
        models.CoverageUsage.policy_id == policy_id,
        models.CoverageUsage.coverage_type == coverage_type,
        models.CoverageUsage.benefit_year == benefit_year,
    )
    usage = session.scalar(statement)
    if usage is not None:
        return usage

    usage = models.CoverageUsage(
        member_id=member_id,
        policy_id=policy_id,
        coverage_type=coverage_type,
        benefit_year=benefit_year,
        paid_amount_used=Decimal("0"),
        deductible_amount_satisfied=Decimal("0"),
    )
    session.add(usage)
    session.flush()
    return usage
