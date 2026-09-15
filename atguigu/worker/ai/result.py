from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.app.respositories.message import MessageRepository
from atguigu.app.schemas.event import RealTimeOutBoxType
from atguigu.app.services.realtime import RealTimeOutBoxService, user_channel, build_message_event_data
from atguigu.common.utils import get_uid, get_utcnow
from atguigu.models.models import Conversation, ConversationTurn, Message


class AIResultService:
    def __init__(self, session: AsyncSession):
        self.message_repo = MessageRepository(session)
        self.real_service = RealTimeOutBoxService(session)

    def save_ai_result_message(self,
                               conversation: Conversation,
                               turn: ConversationTurn,
                               request_message_id: str,
                               content: dict[str, Any],
                               *,
                               message_id: str | None = None
                               ) -> Message:
        message = Message(
            message_id=message_id or get_uid("msg"),
            conversation_id=conversation.id,
            role="ai",
            message_type="text",
            content=content,
            agent_run_id=turn.run_id,
            agent_outcome_seq=1
        )

        self.message_repo.add(message)
        conversation.last_active_at = get_utcnow()

        self.real_service.add_realtime_outbox(
            user_channel(conversation.user_id),
            RealTimeOutBoxType.MESSAGE_CREATE,
            build_message_event_data(message),
            conversation_id=conversation.id,
            message_id=request_message_id

        )

        return message
