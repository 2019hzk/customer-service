from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.models.models import Conversation


class ConversationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_activate_conversation(self, user_id: str, mode: tuple[str, ...]) -> Conversation | None:
        """
        有效的会话：会话模式不是CLOSED状态的[AI QUEUED HUMAN]
        :param user_id:
        select(Conversation):select
        :return:
        """
        return await self.session.scalar(
            select(Conversation)
            .where(Conversation.user_id == user_id,
                   Conversation.mode.in_(mode)
                   )
            .order_by(Conversation.last_active_at.desc())
            .limit(1)
        )

    async def add(self, user_id: str) -> Conversation:
        conversation = Conversation(user_id=user_id, mode="AI")

        self.session.add(conversation)

        await self.session.flush()  # 刷新：当前事务能看到这个对象   其它事务看不到。

        return conversation

    async def get_ai_conversation(self, user_id: str) -> Conversation | None:
        return await self.session.scalar(
            select(Conversation).where(
                Conversation.user_id == user_id,
                Conversation.mode == "AI"
            )
        )

    async def get_conversation(self, conversation_id: str) -> Conversation | None:
        return await self.session.get(Conversation, conversation_id)
