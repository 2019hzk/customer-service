from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.app.respositories.turn import ConversationTurnRepository
from atguigu.common.utils import get_utcnow
from atguigu.models.models import Message, Conversation, ConversationTurn
from atguigu.common.config import get_settings


class TurnService:
    def __init__(self, session: AsyncSession):
        self.setting = get_settings()
        self.session = session
        self.turn_repo = ConversationTurnRepository(session)

    async def add_message_to_turn(self,
                                  message: Message,
                                  conversation: Conversation) -> ConversationTurn:
        """
        职责：将消息保存到turn中
        1. 查询当前会话的轮次状态是不是RUNNING状态
        如果是RUNNING状态，代表轮次已经被turn_worker领取走，准备交给AI_SERVICE处理--做法：创建一个新的轮次Turn
        如果是COLLECTION状态，代表轮次还没被turn_worker领取走，交给AI_SERVICE处理--做法： 修改这一轮的收集事件。collect_until
        :param message:
        :param conversation:
        :return:
        """
        conversation.input_revision += 1
        message.input_revision = conversation.input_revision

        # 1. 先查询正在收集的会话轮次
        turn = await self.turn_repo.find_conversation_by_id(conversation.id)
        # 2. 如果查询到
        now = get_utcnow()
        delay = timedelta(milliseconds=self.setting.message_merge_delay_ms)
        if turn:
            # a) 修改turn的collect_util
            turn.collect_until = min(
                now + delay,
                turn.max_collect_until,
            )
            # b) 返回
            return turn

        # 3. 没有查询到,创建
        turn = ConversationTurn(
            conversation_id=conversation.id,
            user_id=conversation.user_id,
            status="COLLECTING",
            collect_until=now + delay,
            start_revision=conversation.answered_revision+1,
            max_collect_until=now + timedelta(milliseconds=self.setting.message_merge_max_wait_ms)
        )

        self.turn_repo.add_turn(turn)

        return  turn

