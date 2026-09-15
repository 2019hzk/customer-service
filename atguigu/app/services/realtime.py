from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.app.schemas.event import RealTimeOutBoxType
from atguigu.common.utils import get_uid
from atguigu.models.models import RealtimeOutbox, Message



STAFF_CHANNEL = "customer-service:staff"

USER_CHANNEL_PREFIX = "customer-service:user:"


def user_channel(user_id: str) -> str:
    """返回指定用户的实时事件频道。"""
    return f"{USER_CHANNEL_PREFIX}{user_id}"




def  build_message_event_data(message:Message)->dict[str,Any]:
    return {
        "message":{
            "message_id": message.message_id,
            "role": message.role,
            "content": message.content
        }
    }






class RealTimeOutBoxService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def add_realtime_outbox(self,
                            event_channel: str,
                            event_type: RealTimeOutBoxType,
                            event_data: dict[str, Any],
                            conversation_id: str,
                            message_id: str | None):
        outbox = RealtimeOutbox(
            channel=event_channel,
            event_type=event_type,
            conversation_id=conversation_id,
            request_message_id=message_id or get_uid("conversation_id"),
            data=event_data
        )
        self.session.add(outbox)
