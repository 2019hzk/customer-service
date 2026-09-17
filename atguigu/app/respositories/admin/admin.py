from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.models.models import Conversation, Handoff, Message


class AdminMetricsRepository:
    """封装管理员指标的聚合查询。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_metrics(self) -> dict[str, int]:
        """一次查询统计服务核心指标。"""
        statement = select(
            select(func.count(Conversation.id))
            .scalar_subquery()
            .label("conversations"),
            select(func.count(Message.id))
            .scalar_subquery()
            .label("messages"),
            select(func.count(Handoff.id))
            .scalar_subquery()
            .label("handoffs"),
            select(func.count(Conversation.id))
            .where(Conversation.mode == "QUEUED")
            .scalar_subquery()
            .label("queued"),
            select(func.count(Conversation.id))
            .where(Conversation.mode == "HUMAN")
            .scalar_subquery()
            .label("human")
        )
        row = (await self.session.execute(statement)).one()
        return {
            "conversations": row.conversations,
            "messages": row.messages,
            "handoffs": row.handoffs,
            "queued": row.queued,
            "human": row.human
        }
