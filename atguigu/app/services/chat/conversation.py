from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.app.respositories.conversation import ConversationRepository
from atguigu.app.respositories.message import MessageRepository
from atguigu.app.respositories.turn import ConversationTurnRepository
from atguigu.common.utils import get_utcnow
from atguigu.models.models import Conversation, Message
from atguigu.common.config import get_settings


class ConversationService:
    """
    结论：repo只负责刷新 service统一提交，确保事务的完整性（ACID:原子性）
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.conversation_repo = ConversationRepository(session)
        self.turn_repo = ConversationTurnRepository(session)
        self.message_repo = MessageRepository(session)

    async def get_current_conversation(self, user_id: str) -> dict[str, Any]:
        """
        获取当前会话
        :return:
        """
        # 1. 确保当前用户的有效会话要存在
        conversation = await self.ensure_activate_conversation(user_id)

        # 2. 当前是否有轮次消息
        is_processing = await  self.turn_repo.is_activate_turn(conversation.id)

        await self.session.commit()

        # 3. 返回接口数据模型
        return {
            "id": conversation.id,
            "mode": conversation.mode,
            "is_processing": is_processing  # AI 服务有没有在处理轮次消息
        }

    async def ensure_locked_active_conversation(
            self,
            user_id: str,
    ) -> Conversation:
        # (Conversation,conv_id)->conversation
        # 加锁：两个请求后面一个请求能够从数据库中查询到第一个请求修改后的conversation版本【1--->2】
        # orm框架发现这一次查询的缓存key和上一次一模一样，就没有把这一次查询到最新的conversation版本【1--->2】，返回的上一个请求还没有修改的conversation（1）

        conversation = await self.ensure_activate_conversation(user_id)
        await self.session.refresh(
            conversation,
            with_for_update=True
        )
        return conversation

    async def ensure_activate_conversation(self, user_id: str) -> Conversation:
        """
        职责：1. 当前用户已经超时过期的会话修改状态为关闭【CLOSED】 2. 确保当前用户会话存在

        :param user_id:
        :return:
        """
        # 1. 修改当前用户已经超时过期的会话
        await self._close_timeout_conversation(user_id)

        # 2. 查询当前用户是否存在一个有效的会话，如果查询到直接使用
        conversation = await self.conversation_repo.find_activate_conversation(user_id,
                                                                               ("AI", "QUEUED", "HUMAN")
                                                                               )
        if conversation:
            return conversation

        # 3. 如果没有找到一个有效的会话，创建该用户的新会话 在返回
        return await self.conversation_repo.add_conversation(user_id)

    async def _close_timeout_conversation(self, user_id: str):
        """
        关闭超时过期的当前用户会话
        1. 查询当前用户非CLOSED状态（AI QUEUED HUMAN）的会话
        2. 遍历获取的会话是否超时，如果超时，则修改改会话的状态【CLOSED】以及关闭时间 如果没有超时 不用修改
        :param user_id:
        :return:
        """

        # 1. 查询当前用户会话是AI模式的会话
        conversation = await  self.conversation_repo.get_ai_conversation(user_id)
        if conversation is not None:
            # 2. 遍历 判断 修改
            if _has_idle_timeout(conversation):
                conversation.mode = "CLOSED"
                conversation.ended_at = conversation.last_active_at
                await self.session.flush()

    async def get_conversation_detail(self, conversation_id: str) -> dict[str, list[dict[str, Any]]]:
        """
        职责：获取用户会话下的消息内容
        :param conversation_id: 会话ID
        :return:
        """
        # 1. 根据会话ID获取会话对象
        conversation = await self.conversation_repo.get_conversation(conversation_id)
        if conversation is None:
            raise ValueError("当前用户会话不存在")

        # 2. 获取会话的消息列表
        conversation_messages = await  self.message_repo.get_conversation_messages(conversation_id)

        return {
            "messages": [get_message_payload(message) for message in conversation_messages]
        }


def get_message_payload(message: Message) -> dict[str, Any]:
    return {
        "message_id": message.message_id,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at
    }


def _has_idle_timeout(conversation: Conversation) -> bool:
    # 1. 获取当前时间
    now = get_utcnow()

    # 2. 获取当前会话的最后一次有效时间
    active_at = conversation.last_active_at

    # 3. 阈值
    timout = timedelta(minutes=get_settings().conversation_idle_timeout_minutes)

    return (now - active_at) >= timout
