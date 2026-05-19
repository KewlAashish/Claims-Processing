from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import ClaimStatus, DisputeStatus, EnrollmentStatus, PolicyStatus
from app.persistence.database import Base

MONEY_TYPE = Numeric(12, 2)


def new_id() -> str:
    return str(uuid4())


class Member(Base):
    __tablename__ = "members"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    external_member_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    enrollments: Mapped[list["MemberPolicy"]] = relationship(back_populates="member")
    claims: Mapped[list["Claim"]] = relationship(back_populates="member")


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    policy_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    effective_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    effective_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default=PolicyStatus.ACTIVE, nullable=False)

    coverage_rules: Mapped[list["CoverageRule"]] = relationship(
        back_populates="policy", cascade="all, delete-orphan"
    )
    enrollments: Mapped[list["MemberPolicy"]] = relationship(back_populates="policy")


class CoverageRule(Base):
    __tablename__ = "coverage_rules"
    __table_args__ = (UniqueConstraint("policy_id", "coverage_type"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.id"), nullable=False)
    coverage_type: Mapped[str] = mapped_column(String(80), nullable=False)
    annual_limit: Mapped[Decimal] = mapped_column(MONEY_TYPE, nullable=False)
    deductible_amount: Mapped[Decimal] = mapped_column(MONEY_TYPE, nullable=False)
    covered: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    policy: Mapped["Policy"] = relationship(back_populates="coverage_rules")


class MemberPolicy(Base):
    __tablename__ = "member_policies"
    __table_args__ = (UniqueConstraint("member_id", "policy_id"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    member_id: Mapped[str] = mapped_column(ForeignKey("members.id"), nullable=False)
    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default=EnrollmentStatus.ACTIVE, nullable=False)
    effective_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    effective_end_date: Mapped[date] = mapped_column(Date, nullable=False)

    member: Mapped["Member"] = relationship(back_populates="enrollments")
    policy: Mapped["Policy"] = relationship(back_populates="enrollments")


class CoverageUsage(Base):
    __tablename__ = "coverage_usages"
    __table_args__ = (UniqueConstraint("member_id", "policy_id", "coverage_type", "benefit_year"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    member_id: Mapped[str] = mapped_column(ForeignKey("members.id"), nullable=False)
    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.id"), nullable=False)
    coverage_type: Mapped[str] = mapped_column(String(80), nullable=False)
    benefit_year: Mapped[int] = mapped_column(nullable=False)
    paid_amount_used: Mapped[Decimal] = mapped_column(
        MONEY_TYPE, default=Decimal("0"), nullable=False
    )
    deductible_amount_satisfied: Mapped[Decimal] = mapped_column(
        MONEY_TYPE, default=Decimal("0"), nullable=False
    )


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    member_id: Mapped[str] = mapped_column(ForeignKey("members.id"), nullable=False)
    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default=ClaimStatus.SUBMITTED, nullable=False)
    diagnosis_code: Mapped[str] = mapped_column(String(80), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(200), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    member: Mapped["Member"] = relationship(back_populates="claims")
    line_items: Mapped[list["ClaimLineItem"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan"
    )
    disputes: Mapped[list["ClaimDispute"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan"
    )


class ClaimLineItem(Base):
    __tablename__ = "claim_line_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), nullable=False)
    coverage_type: Mapped[str] = mapped_column(String(80), nullable=False)
    service_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    submitted_amount: Mapped[Decimal] = mapped_column(MONEY_TYPE, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    decision_code: Mapped[str] = mapped_column(String(80), nullable=False)
    deductible_applied: Mapped[Decimal] = mapped_column(MONEY_TYPE, nullable=False)
    eligible_amount: Mapped[Decimal] = mapped_column(MONEY_TYPE, nullable=False)
    approved_amount: Mapped[Decimal] = mapped_column(MONEY_TYPE, nullable=False)
    member_responsibility: Mapped[Decimal] = mapped_column(MONEY_TYPE, nullable=False)
    remaining_annual_limit_before_claim: Mapped[Decimal] = mapped_column(MONEY_TYPE, nullable=False)
    remaining_annual_limit_after_claim: Mapped[Decimal] = mapped_column(MONEY_TYPE, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    claim: Mapped["Claim"] = relationship(back_populates="line_items")


class ClaimDispute(Base):
    __tablename__ = "claim_disputes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default=DisputeStatus.OPEN, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    claim: Mapped["Claim"] = relationship(back_populates="disputes")
