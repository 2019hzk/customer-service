from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.app.respositories.message import MessageRepository
from atguigu.app.services.handoff import HandoffService
from atguigu.app.services.realtime import RealTimeOutBoxService
from atguigu.common.utils import get_uid, get_utcnow
from atguigu.models.models import Conversation, ConversationTurn, Message, Handoff


class AIResultService:
    def __init__(self, session: AsyncSession):
        self.message_repo = MessageRepository(session)
        self.real_service = RealTimeOutBoxService(session)
        self.handoff_service = HandoffService(session)

    def save_ai_result(self,
                       conversation: Conversation,
                       turn: ConversationTurn,
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
            agent_outcome_seq=1  # turn 运行完，AI-Service给的结果（多个事件）
        )

        self.message_repo.add(message)
        conversation.last_active_at = get_utcnow()

        self.real_service.add_message_created_events(
            conversation,
            message,
            notify_user=True,
            notify_staff=False
        )

        return message

    async def save_handoff_result(
            self,
            conversation: Conversation,
            turn: ConversationTurn,
            event_data: dict[str, Any]
    ) -> Handoff:
        """原子保存转人工提示、开放工单和状态事件。"""
        # 1. 获取或创建当前用户的开放工单
        handoff = await self.handoff_service.get_or_create_open_handoff(
            conversation,
            summary=str(event_data["summary"])
        )

        # 2. 根据工单状态设置会话的处理模式
        conversation.mode = "QUEUED"

        # 3. 保存 AI 转接提示并创建用户端消息事件
        self.save_ai_result(
            conversation,
            turn,
            event_data["content"],
            message_id=event_data.get("message_id")
        )

        # 4. 为用户端和客服端创建工单状态事件
        self.real_service.add_handoff_changed_events(
            conversation,
            handoff
        )
        return handoff
