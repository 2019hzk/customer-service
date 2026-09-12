from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.app.services.auth import AuthService
from atguigu.app.services.chat.conversation import ConversationService
from atguigu.infrastucture.db import get_db_session


def get_auth_service():
    return AuthService()


def get_conversation_service(session: Annotated[AsyncSession, Depends(get_db_session)]):
    return ConversationService(session=session)


ConversationServiceDep = Annotated[ConversationService, Depends(get_conversation_service)]
