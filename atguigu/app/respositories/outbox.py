from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.models.models import RealtimeOutbox


class OutboxRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def add(self, event: RealtimeOutbox) -> None:
        """将实时事件加入当前数据库事务。"""
        self.session.add(event)
