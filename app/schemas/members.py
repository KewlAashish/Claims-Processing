from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import EnrollmentStatus


class MemberCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    date_of_birth: date
    external_member_id: str = Field(min_length=1, max_length=100)


class MemberPolicyCreate(BaseModel):
    policy_id: str
    effective_start_date: date
    effective_end_date: date
    status: EnrollmentStatus = EnrollmentStatus.ACTIVE


class MemberPolicyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    policy_id: str
    status: EnrollmentStatus
    effective_start_date: date
    effective_end_date: date


class MemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    full_name: str
    date_of_birth: date
    external_member_id: str
    created_at: datetime
    enrollments: list[MemberPolicyRead] = []
