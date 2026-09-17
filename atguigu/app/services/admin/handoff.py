from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.app.respositories.admin.handoff import HandoffRepository
from atguigu.app.respositories.chat.message import MessageRepository
from atguigu.app.services.realtime import RealTimeOutBoxService
from atguigu.common.utils import get_utcnow, get_uid
from atguigu.models.models import Conversation, Handoff, Message


class HandoffService:
    """管理人工工单的创建、接单、回复和结束。"""

    def __init__(self, session: AsyncSession):
        # 1. 保存当前请求使用的数据库会话
        self.session = session

        # 2. 初始化工单业务需要的 Repository 和实时事件服务
        self.handoff_repository = HandoffRepository(session)
        self.message_repository = MessageRepository(session)
        self.real_service = RealTimeOutBoxService(session)

    async def get_or_create_open_handoff(
            self,
            conversation: Conversation,
            *,
            summary: str
    ) -> Handoff:
        """查询开放工单，不存在时创建 waiting 工单。"""
        # 1. 查询当前用户已有的 waiting 或 active 工单
        handoff = await self.handoff_repository.find_open_by_user_id(
            conversation.user_id
        )

        # 2. 已有开放工单时更新摘要并直接复用
        if handoff is not None:
            handoff.summary = summary
            return handoff

        # 3. 没有开放工单时创建 waiting 工单
        handoff = Handoff(
            conversation_id=conversation.id,
            user_id=conversation.user_id,
            summary=summary,
            status="waiting"
        )
        self.handoff_repository.add(handoff)

        # 4. 刷新到数据库
        await self.session.flush()
        return handoff

    async def list_open_handoffs(self) -> list[Handoff]:
        """返回等待中和服务中的工单。"""
        # 1. 查询客服工作台需要展示的 waiting 和 active 工单
        return await self.handoff_repository.list_open()

    async def accept_handoff(
            self,
            handoff_id: str,
            agent_id: str
    ):
        """由客服接单，并将会话切换为 HUMAN。"""
        # 1. 锁定工单及其所属会话
        handoff, conversation = await self._get_open_handoff(handoff_id)

        # 2. active 工单只允许原负责人重复接单
        if handoff.status == "active":
            self._require_owner(handoff, agent_id)
            return

        # 3. 将工单切换为 active 并记录负责人
        handoff.status = "active"
        handoff.assigned_agent_id = agent_id
        handoff.accepted_at = get_utcnow()

        # 4. 将会话切换为人工处理模式
        conversation.mode = "HUMAN"
        conversation.last_active_at = get_utcnow()

        # 5. 为用户端和客服端创建工单状态事件
        self.real_service.add_handoff_changed_events(
            conversation,
            handoff
        )

        # 6. 原子提交工单、会话和 Outbox 事件
        await self.session.commit()

    async def reply_handoff(
            self,
            handoff_id: str,
            agent_id: str,
            *,
            message_id: str,
            text: str
    ) -> None:
        """由当前负责人保存人工回复。"""
        # 1. 锁定工单和会话，并校验当前客服是负责人
        handoff, conversation = await self._get_open_handoff(handoff_id)
        self._require_owner(handoff, agent_id)

        # 2. 保存人工回复消息
        message = self._add_human_message(
            conversation,
            text,
            message_id=message_id
        )

        # 3. 刷新消息序号和创建时间，再创建消息事件
        await self.session.flush()
        self.real_service.add_message_created_events(
            conversation,
            message,
            notify_user=True,
            notify_staff=True
        )

        # 4. 原子提交消息和 Outbox 事件
        await self.session.commit()


    async def resolve_handoff(
            self,
            handoff_id: str,
            agent_id: str,
    ) -> None:
        """结束当前客服负责的工单，并将会话切回 AI"""
        # 1. 锁定工单和会话，并校验当前客服是负责人
        handoff, conversation = await self._get_open_handoff(handoff_id)
        self._require_owner(handoff, agent_id)

        # 2. 结束工单并记录结束时间
        handoff.status = "resolved"
        handoff.resolved_at = get_utcnow()

        # 3. 将会话切回 AI 处理模式
        conversation.mode = "AI"
        conversation.last_active_at = get_utcnow()

        # 4. 保存服务端生成的人工结束语
        message = self._add_human_message(
            conversation,
            "人工客服已结束服务，后续将由 AI 客服继续为您服务。"
        )

        # 5. 刷新消息序号和创建时间，再创建用户端消息事件
        await self.session.flush()
        self.real_service.add_message_created_events(
            conversation,
            message,
            notify_user=True,
            notify_staff=False,
        )

        # 6. 为用户端和客服端创建工单状态事件
        self.real_service.add_handoff_changed_events(
            conversation,
            handoff
        )

        # 7. 原子提交工单、会话、消息和 Outbox 事件
        await self.session.commit()


    async def _get_open_handoff(
            self,
            handoff_id: str
    ) -> tuple[Handoff, Conversation]:
        """锁定开放工单及其所属会话。"""

        # 1. 查询并锁定工单及其所属会话
        handoff_and_conversation = await self.handoff_repository.find_and_lock_with_conversation_by_id(
            handoff_id
        )
        handoff, conversation = handoff_and_conversation
        # 2. 校验工单尚未结束
        if handoff.status == "resolved":
            raise HTTPException(status_code=409, detail="工单已经结束")

        # 3. 返回已经锁定的工单和会话
        return handoff, conversation

    @staticmethod
    def _require_owner(handoff: Handoff, agent_id: str):
        """校验工单属于当前客服。"""
        # 1. 非负责人不能重复接单、回复或结束工单
        if handoff.assigned_agent_id != agent_id:
            raise HTTPException(
                status_code=403,
                detail="工单不属于当前客服",
            )

    def _add_human_message(
            self,
            conversation: Conversation,
            text: str,
            *,
            message_id: str | None = None
    ) -> Message:
        """创建人工消息并加入当前事务。"""
        # 1. 构建 human 角色的文本消息
        message = Message(
            message_id=message_id or get_uid("msg"),
            conversation_id=conversation.id,
            role="human",
            message_type="text",
            content={"text": text}
        )

        # 2. 将消息加入当前事务并更新会话活跃时间
        self.message_repository.add(message)
        conversation.last_active_at = get_utcnow()
        return message
