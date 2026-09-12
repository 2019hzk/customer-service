import uuid
from typing import Any


class ConversationService:

    async def get_current_conversation(self, user_id: str) -> dict[str, Any]:
        """
        获取当前会话
        :return:
        """
        return {"id": f"conversation_{user_id}"}
