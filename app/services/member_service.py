from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.persistence import models
from app.schemas.members import MemberCreate, MemberPolicyCreate
from app.services.errors import ConflictError, NotFoundError, ValidationError


def create_member(session: Session, payload: MemberCreate) -> models.Member:
    member = models.Member(**payload.model_dump())
    session.add(member)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ConflictError("external_member_id already exists") from exc
    session.refresh(member)
    return member


def get_member_detail(session: Session, member_id: str) -> models.Member:
    statement = (
        select(models.Member)
        .options(selectinload(models.Member.enrollments))
        .where(models.Member.id == member_id)
    )
    member = session.scalar(statement)
    if member is None:
        raise NotFoundError("member not found")
    return member


def enroll_member(
    session: Session, member_id: str, payload: MemberPolicyCreate
) -> models.MemberPolicy:
    member = session.get(models.Member, member_id)
    if member is None:
        raise NotFoundError("member not found")

    policy = session.get(models.Policy, payload.policy_id)
    if policy is None:
        raise NotFoundError("policy not found")

    if payload.effective_end_date < payload.effective_start_date:
        raise ValidationError("enrollment end date must be on or after start date")

    enrollment = models.MemberPolicy(member_id=member_id, **payload.model_dump())
    session.add(enrollment)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ConflictError("member is already enrolled in this policy") from exc
    session.refresh(enrollment)
    return enrollment
