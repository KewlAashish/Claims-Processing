from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.enums import ClaimStatus, DecisionCode, DisputeStatus, LineItemStatus


class ClaimLineItemCreate(BaseModel):
    coverage_type: str = Field(min_length=1, max_length=80)
    service_date: date
    description: str = Field(min_length=1, max_length=300)
    submitted_amount: Decimal = Field(gt=0)

    @field_validator("coverage_type")
    @classmethod
    def normalize_coverage_type(cls, value: str) -> str:
        return value.strip().upper()


class ClaimCreate(BaseModel):
    member_id: str
    policy_id: str
    diagnosis_code: str = Field(min_length=1, max_length=80)
    provider_name: str = Field(min_length=1, max_length=200)
    line_items: list[ClaimLineItemCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def reject_duplicate_line_items(self) -> "ClaimCreate":
        seen = set()
        for item in self.line_items:
            key = (
                item.coverage_type,
                item.service_date,
                item.description.strip().lower(),
                item.submitted_amount,
            )
            if key in seen:
                raise ValueError("Duplicate claim line items are not allowed")
            seen.add(key)
        return self


class ClaimLineItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    coverage_type: str
    service_date: date
    description: str
    submitted_amount: Decimal
    status: LineItemStatus
    decision_code: DecisionCode
    deductible_applied: Decimal
    eligible_amount: Decimal
    approved_amount: Decimal
    member_responsibility: Decimal
    remaining_annual_limit_before_claim: Decimal
    remaining_annual_limit_after_claim: Decimal
    explanation: str


class ClaimDisputeCreate(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class ClaimDisputeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    claim_id: str
    reason: str
    status: DisputeStatus
    created_at: datetime


class ClaimRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    member_id: str
    policy_id: str
    status: ClaimStatus
    diagnosis_code: str
    provider_name: str
    submitted_at: datetime
    decided_at: datetime | None
    line_items: list[ClaimLineItemRead]
    disputes: list[ClaimDisputeRead] = []
