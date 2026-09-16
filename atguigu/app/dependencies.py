from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.app.services.auth import AuthService
from atguigu.app.services.chat.conversation import ConversationService
from atguigu.app.services.chat.message import MessageService
from atguigu.app.services.chat.turn import TurnService
from atguigu.app.services.handoff import HandoffService
from atguigu.app.services.realtime import RealTimeOutBoxService
from atguigu.infrastucture.db import get_db_session


def get_auth_service():
    return AuthService()


def get_conversation_service(session: Annotated[AsyncSession, Depends(get_db_session)]):
    return ConversationService(session=session)


ConversationServiceDep = Annotated[ConversationService, Depends(get_conversation_service)]


def get_turn_service(session: Annotated[AsyncSession, Depends(get_db_session)]):
    return TurnService(session=session)


TurnServiceDep = Annotated[TurnService, Depends(get_turn_service)]


def get_outbox_service(session: Annotated[AsyncSession, Depends(get_db_session)]):
    return RealTimeOutBoxService(session=session)


RealTimeOutBoxServiceDep = Annotated[RealTimeOutBoxService, Depends(get_outbox_service)]


def get_message_service(session: Annotated[AsyncSession, Depends(get_db_session)],
                        conv_service: ConversationServiceDep,
                        turn_service: TurnServiceDep,
                        outbox_service: RealTimeOutBoxServiceDep

                        ):
    return MessageService(session,
                          conv_service,
                          outbox_service,
                          turn_service
                          )


MessageServiceDep = Annotated[MessageService, Depends(get_message_service)]


async def get_handoff_service(
        session: Annotated[AsyncSession, Depends(get_db_session)]
) -> HandoffService:
    return HandoffService(session)


HandoffServiceDep = Annotated[
    HandoffService,
    Depends(get_handoff_service)
]
