from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.persistence.database import get_session
from app.schemas.policies import CoverageRuleRead, CoverageRuleUpsert, PolicyCreate, PolicyRead
from app.services import policy_service

router = APIRouter(prefix="/policies", tags=["policies"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.post("", response_model=PolicyRead, status_code=201)
def create_policy(payload: PolicyCreate, session: SessionDep):
    return policy_service.create_policy(session, payload)


@router.get("/{policy_id}", response_model=PolicyRead)
def get_policy(policy_id: str, session: SessionDep):
    return policy_service.get_policy_detail(session, policy_id)


@router.post("/{policy_id}/coverage-rules", response_model=CoverageRuleRead, status_code=201)
def upsert_coverage_rule(
    policy_id: str,
    payload: CoverageRuleUpsert,
    session: SessionDep,
):
    return policy_service.upsert_coverage_rule(session, policy_id, payload)
