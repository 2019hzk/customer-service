from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.models.models import Message, Conversation


class MessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_conversation_messages(self, conversation_id: str) -> list[Message]:
        results = await  self.session.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.id.desc())
        )

        return list(results.all())

    async def find_with_conversation_by_message_id(self, message_id: str) -> tuple[Message, Conversation] | None:
        result = await self.session.execute(
            select(Message)
            .join(
                Conversation,
                Message.conversation_id == Conversation.id
            )
            .where(Message.message_id == message_id)
        )

        return result.tuples().scalar_one_or_none()

    def add_message(self, message:Message):
        self.session.add(message)

