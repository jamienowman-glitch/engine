from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import get_auth_context, require_tenant_membership
from engines.three_wise.service import get_three_wise_service
from pydantic import BaseModel


class ThreeWiseQuestion(BaseModel):
    question: str
    context: Optional[str] = None


router = APIRouter(prefix="/three-wise", tags=["three_wise"])


@router.post("/questions")
def submit_question(
    payload: ThreeWiseQuestion,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    return get_three_wise_service().submit_question(context, payload.question, payload.context)


@router.get("/questions")
def list_questions(
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    return get_three_wise_service().list_records(context)


@router.get("/questions/{record_id}")
def get_question(
    record_id: str,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    return get_three_wise_service().get_record(context, record_id)
