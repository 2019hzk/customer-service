from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.app.respositories.outbox import OutboxRepository
from atguigu.app.schemas.event import RealTimeOutBoxType
from atguigu.models.models import (
    Conversation,
    Handoff,
    Message,
    RealtimeOutbox,
)

STAFF_CHANNEL = "customer-service:staff"
USER_CHANNEL_PREFIX = "customer-service:user:"


def user_channel(user_id: str) -> str:
    """返回指定用户的实时事件频道。"""
    return f"{USER_CHANNEL_PREFIX}{user_id}"


def build_message_created_data(message: Message) -> dict[str, Any]:
    """构建消息创建事件的数据。"""
    return {
        "message": {
            "message_id": message.message_id,
            "role": message.role,
            "content": message.content,
        }
    }


def build_handoff_changed_data(handoff: Handoff, conversation: Conversation) -> dict[str, Any]:
    """构建工单状态变化事件的数据。"""
    return {
        "handoff_id": handoff.id,
        "status": handoff.status,
        "summary": handoff.summary,
        "assigned_agent_id": handoff.assigned_agent_id,
        "conversation_mode": conversation.mode
    }


class RealTimeOutBoxService:
    """负责在当前业务事务中创建待发布事件。"""

    def __init__(self, session: AsyncSession):
        self.outbox_repository = OutboxRepository(session)

    def add_message_created_events(
            self, conversation: Conversation,
            message: Message,
            *,
            notify_user: bool,
            notify_staff: bool
    ):
        """按指定接收端写入消息创建事件"""
        channels: list[str] = []
        if notify_user:
            channels.append(user_channel(conversation.user_id))
        if notify_staff:
            channels.append(STAFF_CHANNEL)

        for channel in channels:
            self._add_outbox_event(
                channel,
                RealTimeOutBoxType.MESSAGE_CREATED,
                build_message_created_data(message),
                conversation_id=conversation.id
            )

    def add_handoff_changed_events(self, conversation: Conversation, handoff: Handoff):
        """向用户端和客服端写入工单状态事件"""
        for channel in (
                user_channel(conversation.user_id),
                STAFF_CHANNEL,
        ):
            self._add_outbox_event(
                channel,
                RealTimeOutBoxType.HANDOFF_CHANGED,
                build_handoff_changed_data(
                    handoff,
                    conversation,
                ),
                conversation_id=conversation.id
            )

    def _add_outbox_event(
            self,
            channel: str,
            event_type: RealTimeOutBoxType,
            event_data: dict[str, Any],
            *,
            conversation_id: str
    ) -> RealtimeOutbox:
        """将事件写入 Outbox，等待后续 Worker 发布。"""
        event = RealtimeOutbox(
            channel=channel,
            event_type=event_type,
            conversation_id=conversation_id,
            data=event_data
        )
        self.outbox_repository.add(event)
        return event
