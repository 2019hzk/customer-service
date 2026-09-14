from typing import Annotated

from fastapi import APIRouter, Header

from atguigu.app.dependencies import get_auth_service, MessageServiceDep
from atguigu.app.schemas.message import ChatMessageRequest, AcceptUserMessageResponse

router = APIRouter(tags=["聊天路由"], prefix="/api/v1/chat")


@router.post("/messages", response_model=AcceptUserMessageResponse)
async def accept_user_message(
        chat_message: ChatMessageRequest,
        message_service: MessageServiceDep,
        authorization: Annotated[str | None, Header()] = None
):
    authorized_user = get_auth_service().get_authorized_user(authorization, "customer")

    result = await message_service.accept_user_message(chat_message, authorized_user.user_id)

    return  result
