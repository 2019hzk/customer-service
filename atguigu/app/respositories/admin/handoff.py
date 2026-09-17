from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.models.models import Handoff, Conversation


class HandoffRepository:
    """封装人工工单的数据访问。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    def add(self, handoff: Handoff) -> None:
        """将人工工单加入当前数据库事务。"""
        self.session.add(handoff)

    async def find_open_by_user_id(self, user_id: str) -> Handoff | None:
        """查询用户仍处于等待或服务中的工单。"""
        return await self.session.scalar(
            select(Handoff).where(
                Handoff.user_id == user_id,
                Handoff.status.in_(["waiting", "active"])
            )
        )

    async def list_open(self) -> list[Handoff]:
        """按创建时间返回所有开放工单。"""
        records = await self.session.scalars(
            select(Handoff)
            .where(Handoff.status.in_(["waiting", "active"]))
            .order_by(Handoff.created_at)
        )
        return list(records.all())

    async def find_and_lock_with_conversation_by_id(
            self,
            handoff_id: str
    ) -> tuple[Handoff, Conversation]:
        """按 ID 查询并锁定工单及其所属会话"""
        result = await self.session.execute(
            select(Handoff, Conversation)
            .join(
                Conversation,
                Conversation.id == Handoff.conversation_id
            )
            .where(Handoff.id == handoff_id)
            .with_for_update()
        )
        return result.tuples().one()
