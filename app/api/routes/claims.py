from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.persistence.database import get_session
from app.schemas.claims import ClaimCreate, ClaimDisputeCreate, ClaimDisputeRead, ClaimRead
from app.services import claim_service

router = APIRouter(prefix="/claims", tags=["claims"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.post("", response_model=ClaimRead, status_code=201)
def submit_claim(payload: ClaimCreate, session: SessionDep):
    return claim_service.submit_claim(session, payload)


@router.get("/{claim_id}", response_model=ClaimRead)
def get_claim(claim_id: str, session: SessionDep):
    return claim_service.get_claim(session, claim_id)


@router.post("/{claim_id}/pay", response_model=ClaimRead)
def pay_claim(claim_id: str, session: SessionDep):
    return claim_service.mark_claim_paid(session, claim_id)


@router.post("/{claim_id}/disputes", response_model=ClaimDisputeRead, status_code=201)
def create_dispute(
    claim_id: str,
    payload: ClaimDisputeCreate,
    session: SessionDep,
):
    return claim_service.create_dispute(session, claim_id, payload)
