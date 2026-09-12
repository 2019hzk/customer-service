from typing import Annotated

from fastapi import APIRouter, Header

from atguigu.app.dependencies import ConversationServiceDep, get_auth_service

router = APIRouter(prefix="/api/v1", tags=["聊天会话路由"])


@router.post("/conversations/current")
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



