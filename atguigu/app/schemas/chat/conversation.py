from datetime import datetime
from enum import  StrEnum
from typing import Literal, Any

from pydantic import BaseModel


class ConversationMode(StrEnum):
    AI = "AI"  # 用户端显示“AI 客服”
    QUEUED = "QUEUED"  # 用户端显示“等待人工”
    HUMAN = "HUMAN"  # 用户端显示“人工服务中”
    CLOSED = "CLOSED"  # 用户端显示“已结束”


class CurrentConversationResponse(BaseModel):
    id: str
    mode: ConversationMode
    is_processing: bool


class ConversationMessageResponse(BaseModel):
    message_id: str
    role: Literal["user", "ai", "human"]
    content: dict[str, Any]
    created_at: datetime


class ConversationDetailResponse(BaseModel):
    messages: list[ConversationMessageResponse]
