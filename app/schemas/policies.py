from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import PolicyStatus


class PolicyCreate(BaseModel):
    policy_number: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    effective_start_date: date
    effective_end_date: date
    status: PolicyStatus = PolicyStatus.ACTIVE


class CoverageRuleUpsert(BaseModel):
    coverage_type: str = Field(min_length=1, max_length=80)
    annual_limit: Decimal = Field(ge=0)
    deductible_amount: Decimal = Field(ge=0)
    covered: bool = True

    @field_validator("coverage_type")
    @classmethod
    def normalize_coverage_type(cls, value: str) -> str:
        return value.strip().upper()


class CoverageRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    coverage_type: str
    annual_limit: Decimal
    deductible_amount: Decimal
    covered: bool


class PolicyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    policy_number: str
    name: str
    effective_start_date: date
    effective_end_date: date
    status: PolicyStatus
    coverage_rules: list[CoverageRuleRead] = []
