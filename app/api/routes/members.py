from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.persistence.database import get_session
from app.schemas.members import MemberCreate, MemberPolicyCreate, MemberPolicyRead, MemberRead
from app.services import member_service

router = APIRouter(prefix="/members", tags=["members"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.post("", response_model=MemberRead, status_code=201)
def create_member(payload: MemberCreate, session: SessionDep):
    return member_service.create_member(session, payload)


@router.get("/{member_id}", response_model=MemberRead)
def get_member(member_id: str, session: SessionDep):
    return member_service.get_member_detail(session, member_id)


@router.post("/{member_id}/policies", response_model=MemberPolicyRead, status_code=201)
def enroll_member(
    member_id: str,
    payload: MemberPolicyCreate,
    session: SessionDep,
):
    return member_service.enroll_member(session, member_id, payload)
