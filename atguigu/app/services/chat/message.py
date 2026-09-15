from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.app.respositories.message import MessageRepository
from atguigu.app.schemas.event import  RealTimeOutBoxType
from atguigu.app.schemas.message import ChatMessageRequest
from atguigu.app.services.chat.conversation import ConversationService
from atguigu.app.services.chat.turn import TurnService
from atguigu.app.services.realtime import RealTimeOutBoxService, build_message_event_data, STAFF_CHANNEL
from atguigu.common.utils import get_uid, get_utcnow
from atguigu.models.models import Message, Conversation


class MessageService:
    def __init__(self,
                 session: AsyncSession,
                 conversation_service: ConversationService,
                 outbox_service: RealTimeOutBoxService,
                 turn_service: TurnService):
        self.session = session
        self.conversation_service = conversation_service
        self.outbox_service = outbox_service
        self.turn_service = turn_service
        self.message_repo = MessageRepository(session)

    async def accept_user_message(self,
                                  chat_message: ChatMessageRequest,
                                  user_id: str
                                  ) -> dict[str, Any]:
        """
        职责：保存用户消息
        1. 判断当前用户是否发送同一条消息
            1.1 如果是，返回{"conversation_id":"","mode":""}
            1.2 如果没有重复的，创建当前用户的消息
        2. 创建当前用户的消息
        3. 判断会话模式
        # 3.1 如果会话模式是有效会话模式的AI模式，需要管理Turn
        # 3.2 如果会话模式是有效会话模式的QUEUED[客服没接入]/HUMAN[客服接入],需要管理实时消息事件

        # 4. 返回接口要的数据 {"conversation_id":"","mode":""}
        :param chat_message:
        :param user_id:
        :return:
        """

        # 1. 根据消息ID以及该消息所在的会话查询是否存在重复的消息【Message,Conversation】

        duplicate_result = await self.message_repo.find_with_conversation_by_message_id(chat_message.message_id)

        # 1.1 判断重复的消息(一个用户的一个会话中message_id一样)
        if duplicate_result:
            message, conversation = duplicate_result
            return {
                "conversation_id": message.conversation_id,
                "mode": conversation.mode
            }
        # 2. 当前用户消息的会话(串行进来)
        # conversation = await self.conversation_service.ensure_activate_conversation(user_id)
        # 生产环境需要实现---TODO
        conversation = await self.conversation_service.ensure_locked_active_conversation(user_id)

        # 3. 通用的保存消息方法(保存消息之前要先有会话)
        message = self.save_message(
            conversation,
            chat_message.content,
            chat_message.message_id,
            message_role="user",
            message_type=chat_message.type
        )

        # 4. 判断会话的模式
        if conversation.mode == "AI":
            # 管理轮次
            await self.turn_service.add_message_to_turn(message, conversation)
        elif conversation.mode in ("QUEUED", "HUMAN"):
            # 管理端、MESSAGE_CREATE、当前消息
            self.outbox_service.add_realtime_outbox(
                STAFF_CHANNEL,
                RealTimeOutBoxType.MESSAGE_CREATE,
                build_message_event_data(message),
                conversation.id,
                chat_message.message_id
            )
        else:
            raise ValueError(f"当前会话模式{conversation.mode}不支持")

        # 5. 提交保存
        await self.session.commit()

        # 6. 返回接口需要的数据
        return {
            "conversation_id": conversation.id,
            "mode": conversation.mode
        }

    def save_message(self,
                     conversation: Conversation,
                     message_content: dict[str, Any],
                     message_id: str | None,
                     *,
                     message_role: str,
                     message_type: str = "text",
                     ) -> Message:

        # 1. 实例化消息对象
        message = Message(
            conversation_id=conversation.id,
            role=message_role,
            message_id=message_id or get_uid(conversation.id),
            message_type=message_type,
            content=message_content
        )

        # 2. 更新会话的激活时间(判断是否过期)
        conversation.last_active_at = get_utcnow()

        # 3. 保存
        self.message_repo.add_message(message)

        return message
