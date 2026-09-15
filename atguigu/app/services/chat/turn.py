from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.app.respositories.conversation import ConversationRepository
from atguigu.app.respositories.message import MessageRepository
from atguigu.app.respositories.turn import ConversationTurnRepository
from atguigu.common.utils import get_utcnow
from atguigu.models.models import Message, Conversation, ConversationTurn
from atguigu.common.config import get_settings


class TurnService:
    def __init__(self, session: AsyncSession):
        self.setting = get_settings()
        self.session = session
        self.turn_repo = ConversationTurnRepository(session)
        self.conver_repo = ConversationRepository(session)
        self.message_repo = MessageRepository(session)

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
            start_revision=conversation.answered_revision + 1,
            max_collect_until=now + timedelta(milliseconds=self.setting.message_merge_max_wait_ms)
        )

        self.turn_repo.add_turn(turn)

        return turn



    async def claim_turn(self, worker_id: str) -> ConversationTurn | None:
        """
        职责：负责从数据库中查询一个Turn
        :return:
        """
        now = get_utcnow()

        # 1. 查询可以被领走的Turn
        turn_and_conversation = await self.turn_repo.find_ready_turn_conversation_by_lock(now)

        # 2. 没有找到
        if turn_and_conversation is None:
            return None

        # 3. 找到Turn
        # 更新Turn中其它的属性(RUNNING)
        claimed_turn, conversation = turn_and_conversation
        claimed_turn.status = "RUNNING"
        claimed_turn.snapshot_revision = conversation.input_revision
        claimed_turn.locked_by = worker_id
        claimed_turn.locked_until = now + timedelta(self.setting.ai_worker_lease_seconds)
        claimed_turn.attempts += 1
        claimed_turn.started_at = claimed_turn.started_at or now

        # 4. 返回
        return claimed_turn

    async def build_ai_request_data(self, claimed_turn: ConversationTurn) -> tuple[dict[str, Any], str]:
        """
        职责：
        1. 根据领取到的Turn,选择将该turn范围内的消息获取---当前消息
        2. 获取历史消息(排序当前消息的历史消息)  Message消息表（当前消息以及历史消息）
        :param claimed_turn:
        :return:
        """

        # 1. 获取当前消息
        snapshot_revision = claimed_turn.snapshot_revision

        current_messages = await self.message_repo.find_current_messages_by_turn_range(
            claimed_turn.conversation_id,
            claimed_turn.start_revision,
            snapshot_revision
        )

        # 2. 获取历史消息
        history_messages = list(
            reversed(await self.message_repo.find_history_message_by_sequence(claimed_turn.conversation_id,current_messages[0].id)))

        # 3. 构建字典，作为最终上下文，返回
        return {
            "conversation_id": claimed_turn.conversation_id,
            "user_id": claimed_turn.user_id,
            "turn_id": claimed_turn.id,
            "request_id": f"{claimed_turn.id}:attempt:{claimed_turn.attempts}",
            "input_revision": snapshot_revision,
            "messages": [
                {
                    "message_id": message.message_id,
                    "type": message.message_type,
                    "content": message.content,
                }
                for message in current_messages
            ],
            "history": [
                {
                    "message_id": message.message_id,
                    "role": message.role,
                    "type": message.message_type,
                    "content": message.content,
                    "created_at": message.created_at.isoformat()
                }
                for message in history_messages
            ],
        }, current_messages[-1].message_id


    async  def find_turn_conversation_by_id(self,turn_id:str)->tuple[ConversationTurn,Conversation]:
       return await self.turn_repo.find_turn_conversation_by_id(turn_id)


    def  mark_superseded(self,turn:ConversationTurn):
        turn.status="SUPERSEDED"   # 终态
        turn.finished_at=get_utcnow()
        TurnService._release_lease(turn) # 清理占用者的信息








    async def list_expired_running_turns_with_conversations(
            self,
    ) -> list[tuple[ConversationTurn, Conversation]]:
        """查询全部过期 Turn，并锁定各自所属会话。"""
        turns = await self.turn_repo.list_expired_running_turns(
            get_utcnow()
        )
        result: list[tuple[ConversationTurn, Conversation]] = []
        for turn in turns:
            conv = await self.conver_repo.get_and_lock_by_id(turn.conversation_id)
            result.append((turn, conv))

        return result

    def retry_or_fail(self,
                      turn: ConversationTurn,
                      error: Exception):
        turn.last_error = str(error)
        self._release_lease(turn)
        if turn.attempts < self.setting.ai_worker_max_attempts:
            turn.status = "COLLECTING"
            turn.collect_until = get_utcnow() + timedelta(
                seconds=self.setting.ai_worker_retry_delay_seconds
            )
            turn.run_id = None
            return True

        turn.status = "FAILED"
        turn.finished_at = get_utcnow()
        return False

    @staticmethod
    def _release_lease(turn: ConversationTurn):
        turn.locked_by = None
        turn.locked_until = None
