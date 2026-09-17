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
            .order_by(Message.id)
        )

        return list(results.all())

    async def find_with_conversation_by_message_id(self, message_id: str) -> tuple[Message, Conversation] | None:
        result = await self.session.execute(
            select(Message, Conversation)
            .join(
                Conversation,
                Message.conversation_id == Conversation.id
            )
            .where(Message.message_id == message_id)
        )

        return result.tuples().one_or_none()

    def add_message(self, message: Message):
        self.session.add(message)

    async def find_current_messages_by_turn_range(self,
                                                  conversation_id: str,
                                                  start_revision: int,
                                                  snapshot_revision: int) -> list[Message]:
        results = await  self.session.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id,
                   Message.input_revision >= start_revision,
                   Message.input_revision <= snapshot_revision,
                   Message.role == "user"
                   )
            .order_by(Message.input_revision)
        )

        return list(results.all())

    async def find_history_message_by_sequence(self,
                                               conversation_id: str,
                                               message_id: int,
                                               limit: int = 30
                                               ) -> list[Message]:
        results = await self.session.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id,
                   Message.id < message_id)
            .order_by(Message.id.desc())
            .limit(limit)
        )
        return list(results.all())

    def add(self, message: Message):
        self.session.add(message)

    async def list_user_history(
            self,
            user_id: str,
            after_sequence: int | None = None
    ) -> list[tuple[Message, Conversation]]:
        """查询当前用户的历史消息，可按消息序号增量读取"""
        statement = (
            select(Message, Conversation)
            .join(
                Conversation,
                Conversation.id == Message.conversation_id,
            )
            .where(Conversation.user_id == user_id)
        )
        if after_sequence is not None:
            statement = statement.where(Message.id > after_sequence)

        result = await self.session.execute(
            statement.order_by(Message.id)
        )
        return list(result.tuples().all())
