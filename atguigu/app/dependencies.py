from typing import Annotated

from fastapi import Depends

from atguigu.app.services.auth import AuthService
from atguigu.app.services.chat.conversation import ConversationService


def get_auth_service():
    return AuthService()


def get_conversation_service():
    return ConversationService()


ConversationServiceDep = Annotated[ConversationService, Depends(get_conversation_service)]
