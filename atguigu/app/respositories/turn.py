from sqlalchemy import select, exists
from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.models.models import ConversationTurn


class ConversationTurnRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def is_activate_turn(self, conversation_id: str) -> bool:
        # result = await self.session.scalar(
        #     select(ConversationTurn).where(ConversationTurn.conversation_id == conversation_id)
        # )
        # return True if result else False

        return bool(await self.session.scalar(
            select(
                exists()
                .where(ConversationTurn.conversation_id == conversation_id,
                       ConversationTurn.status.in_(["COLLECTING", "RUNNING"]))
            )
        ))
