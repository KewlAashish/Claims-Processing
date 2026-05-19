from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.persistence import models
from app.schemas.policies import CoverageRuleUpsert, PolicyCreate
from app.services.errors import ConflictError, NotFoundError, ValidationError


def create_policy(session: Session, payload: PolicyCreate) -> models.Policy:
    if payload.effective_end_date < payload.effective_start_date:
        raise ValidationError("policy end date must be on or after start date")

    policy = models.Policy(**payload.model_dump())
    session.add(policy)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ConflictError("policy_number already exists") from exc
    session.refresh(policy)
    return policy


def upsert_coverage_rule(
    session: Session, policy_id: str, payload: CoverageRuleUpsert
) -> models.CoverageRule:
    policy = session.get(models.Policy, policy_id)
    if policy is None:
        raise NotFoundError("policy not found")

    statement = select(models.CoverageRule).where(
        models.CoverageRule.policy_id == policy_id,
        models.CoverageRule.coverage_type == payload.coverage_type,
    )
    rule = session.scalar(statement)
    if rule is None:
        rule = models.CoverageRule(policy_id=policy_id, **payload.model_dump())
        session.add(rule)
    else:
        for field, value in payload.model_dump().items():
            setattr(rule, field, value)

    session.commit()
    session.refresh(rule)
    return rule


def get_policy_detail(session: Session, policy_id: str) -> models.Policy:
    statement = (
        select(models.Policy)
        .options(selectinload(models.Policy.coverage_rules))
        .where(models.Policy.id == policy_id)
    )
    policy = session.scalar(statement)
    if policy is None:
        raise NotFoundError("policy not found")
    return policy
