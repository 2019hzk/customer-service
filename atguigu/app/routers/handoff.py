from typing import Annotated

from fastapi import APIRouter, Header, status

from atguigu.app.dependencies import HandoffServiceDep, get_auth_service
from atguigu.app.schemas.handoff import OpenHandoffResponse


router = APIRouter(
    prefix="/api/v1/handoffs",
    tags=["人工工单路由"]
)


@router.get("", response_model=list[OpenHandoffResponse])
async def list_handoffs(
        handoff_service: HandoffServiceDep,
        authorization: Annotated[str | None, Header()] = None
):
    """返回客服可以处理的开放工单。"""
    get_auth_service().auth_service.get_authorized_user(authorization, "agent")
    return await handoff_service.list_open_handoffs()
