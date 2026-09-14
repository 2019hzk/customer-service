from sqlalchemy import select, exists
from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.models.models import ConversationTurn


class ConversationTurnRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def is_activate_turn(self, conversation_id: str) -> bool:
        return bool(await self.session.scalar(
            select(
                exists()
                .where(ConversationTurn.conversation_id == conversation_id,
                       ConversationTurn.status.in_(["COLLECTING", "RUNNING"]))
            )
        ))

    async def find_conversation_by_id(self, conv_id: str) -> ConversationTurn | None:
        return await self.session.scalar(
            select(ConversationTurn)
            .where(ConversationTurn.conversation_id == conv_id,
                   ConversationTurn.status == "COLLECTING")
            .with_for_update()
        )

    def add_turn(self, turn:ConversationTurn):
        self.session.add(turn)
