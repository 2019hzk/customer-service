import uuid
from typing import Any


class ConversationService:

    async def get_current_conversation(self) -> dict[str, Any]:
        """
        获取当前会话
        :return:
        """
        return {"id": f"conversation_{uuid.uuid4().hex}"}


