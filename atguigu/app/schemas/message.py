from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from atguigu.app.schemas.conversation import ConversationMode


class MessageType(StrEnum):
    TEXT = "text"
    OBJECT = "object"


class MessageRole(StrEnum):
    USER = "user"
    AI = "ai"
    HUMAN = "human"


class ChatMessageRequest(BaseModel):
    message_id: str = Field(min_length=4, max_length=80)
    type: MessageType
    content: dict[str, Any]


class AcceptUserMessageResponse(BaseModel):
    """用户消息受理结果。"""

    conversation_id: str
    mode: ConversationMode
