from typing import Annotated

from fastapi import APIRouter, Header

from atguigu.app.dependencies import ConversationServiceDep, get_auth_service
from atguigu.app.schemas.chat.conversation import CurrentConversationResponse, ConversationDetailResponse

router = APIRouter(prefix="/api/v1", tags=["聊天会话路由"])


@router.post("/conversations/current",
             response_model=CurrentConversationResponse)
async def get_current_conversation(conversation_service: ConversationServiceDep,
                                   authorization: Annotated[str | None, Header()] = None):
    """
    权限限制：
    1. 对应的用户信息
    2. 用户身份角色是否是接口允许的角色("customer")
    :param conversation_service:
    :return:
    """
    authorized_user = get_auth_service().get_authorized_user(authorization, "customer")
    result = await conversation_service.get_current_conversation(authorized_user.user_id)
    return result


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse
)
async def get_conversation_detail(
        conversation_id: str,
        conversation_service: ConversationServiceDep,
        authorization: Annotated[str | None, Header()] = None
):
    """返回客服工作台所需的完整会话详情。"""

    get_auth_service().get_authorized_user(authorization, "agent")

    conversation_detail = await conversation_service.get_conversation_detail(conversation_id)

    return conversation_detail
