from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.domain.enums import EnrollmentStatus, PolicyStatus
from app.persistence.database import SessionLocal, create_all
from app.persistence.models import CoverageRule, Member, MemberPolicy, Policy


def run() -> None:
    create_all()
    session = SessionLocal()
    try:
        existing = session.scalar(select(Member).where(Member.external_member_id == "DEMO-001"))
        if existing is not None:
            print("Seed data already exists")
            return

        member = Member(
            full_name="Demo Member",
            date_of_birth=date(1990, 1, 1),
            external_member_id="DEMO-001",
        )
        policy = Policy(
            policy_number="DEMO-POLICY",
            name="Demo Health Plan",
            effective_start_date=date(2026, 1, 1),
            effective_end_date=date(2026, 12, 31),
            status=PolicyStatus.ACTIVE,
        )
        session.add_all([member, policy])
        session.flush()
        session.add_all(
            [
                CoverageRule(
                    policy_id=policy.id,
                    coverage_type="OPD",
                    annual_limit=Decimal("10000"),
                    deductible_amount=Decimal("1000"),
                    covered=True,
                ),
                CoverageRule(
                    policy_id=policy.id,
                    coverage_type="RX",
                    annual_limit=Decimal("3000"),
                    deductible_amount=Decimal("250"),
                    covered=True,
                ),
                CoverageRule(
                    policy_id=policy.id,
                    coverage_type="DENTAL",
                    annual_limit=Decimal("0"),
                    deductible_amount=Decimal("0"),
                    covered=False,
                ),
                MemberPolicy(
                    member_id=member.id,
                    policy_id=policy.id,
                    status=EnrollmentStatus.ACTIVE,
                    effective_start_date=date(2026, 1, 1),
                    effective_end_date=date(2026, 12, 31),
                ),
            ]
        )
        session.commit()
        print(f"Seeded member_id={member.id}")
        print(f"Seeded policy_id={policy.id}")
    finally:
        session.close()


if __name__ == "__main__":
    run()
