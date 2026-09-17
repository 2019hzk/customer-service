from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from atguigu.app.schemas.chat.conversation import ConversationMode


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


class HistoryMessageResponse(BaseModel):
    """聊天历史中的消息及会话开始时间。"""
    sequence: int
    message_id: str
    conversation_id: str
    role: MessageRole
    type: MessageType
    content: dict[str, Any]
    created_at: datetime
    conversation_started_at: datetime
