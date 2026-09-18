"""
Turn(AI)Worker
"""
import asyncio
import logging
import os
import socket
from typing import Any

from atguigu.app.schemas.admin.user import CurrentUser
from atguigu.app.services.admin.auth import AuthService
from atguigu.app.services.chat.turn import TurnService
from atguigu.common.event_loop import run_async
from atguigu.infrastucture.db import session_factory
from atguigu.worker.ai.gateway import AIServiceGateway
from atguigu.worker.ai.parser import AIEventParser
from atguigu.worker.ai.result import AIResultService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger(__name__)
from atguigu.common.config import get_settings


class TurnProcessor:
    """
    轮次处理器
    """

    def __init__(self):
        self.setting = get_settings()
        self.auth_service = AuthService()
        self.ai_gateway = AIServiceGateway()
        self.event_parser = AIEventParser()

    async def process(self,
                      request_data: dict[str, Any],
                      user_id: str
                      ):
        # 1. 创建令牌
        access_token = self.auth_service.encode_access_token(
            CurrentUser(user_id=user_id)
        )

        # 2. (发送请求给AI_SERVICE/解析AI_SERVICE的事件类型以及数据/校验【二阶段】)
        error: Exception | None = None
        run_id: str | None = None
        run_result: dict[str, Any] | None = None
        try:
            run_id, run_result = await self.run_ai_pipeline(access_token, request_data)
        except Exception as exec:
            error = exec
            logger.exception(f"{request_data['turn_id']}运行失败,原因:{exec}")

        # 3. 修改Turn状态、结果的保存
        # self.finalize_result(run_id, run_result,error,request_message_id)
        await self._finalize_turn(request_data["turn_id"], run_id, run_result, error)

    async def run_ai_pipeline(self,
                              token: str,
                              request_data: dict[str, Any]) -> tuple[str, dict[str, Any] | None] | None:
        """
        调用 AI Service，并在准备结果返回后执行二阶段确认。

        commit：Customer Service 确认输入快照仍然有效。
        cancel：输入快照已经过期，取消待发布结果。

        :param token:
        :param request_data:
        :return:
        """

        # 1. 调用start_run(第一阶段)
        event = await self.ai_gateway.start_run(token, request_data)

        # 2. 找到run_id
        run_id = self.event_parser.find_run_id(event)

        # 3. 根据事件查询事件类型是否是run_decision_prepared
        prepared = self.event_parser.has_prepared_decision(event)

        commit = False
        # 4. 决策准备好了
        try:
            if prepared:
                # a) 校验快照版本是否过期了，如果要过期了，cancel_run 如果没有过期 调用 commit_run
                if not await self._validate_before_commit(request_data['turn_id'], run_id):
                    await self.ai_gateway.cancel_run(token, run_id)
                    return run_id, None
                # b) 调用commit_run
                event = await self.ai_gateway.commit_run(token, run_id)
                commit = True  # 变量

            return run_id, self.event_parser.parser_outcome(event)
        except Exception as exec:
            if prepared and not commit:  # 控制二阶段（cancel 只能针对二阶段）
                await self.ai_gateway.cancel_run(token, run_id)
            raise exec

    async def _validate_before_commit(self,
                                     turn_id: str,
                                     run_id: str
                                     ) -> bool:

        async  with session_factory() as session:
            turn_service = TurnService(session)

            # 1. 获取turn轮次和会话
            turn_and_conversation = await turn_service.find_turn_conversation_by_id(turn_id)

            # 2. 解包
            turn, conversation = turn_and_conversation

            if run_id:
                turn.run_id = run_id

            # 3. 校验
            if turn.snapshot_revision != conversation.input_revision:
                # 标记当前turn过期了SUPERSEDED(修改turn的状态)
                turn_service.mark_superseded(turn)
                await session.commit()  # 数据库更新以及释放锁
                return False

            await session.commit()
            return True

    async def _finalize_turn(
            self,
            turn_id: str,
            run_id: str | None,
            run_result: dict[str, Any] | None,
            error: Exception | None
    ):
        """结算 Turn 状态并保存 AI 响应及 Outbox 事件。"""
        async with session_factory() as session:
            # 1. 锁定当前 Turn 及其所属会话
            turn_service = TurnService(session)
            result_service = AIResultService(session)
            turn, conversation = (
                await turn_service.find_turn_conversation_by_id(
                    turn_id
                )
            )

            # 2. 记录 AI Service 返回的 Run ID
            if run_id is not None:
                turn.run_id = run_id

            # 3. 输入快照过期时标记 Turn 失效并结束结算
            if conversation.input_revision != turn.snapshot_revision:
                turn_service.mark_superseded(turn)
                await session.commit()
                return

            # 4. 调用失败时执行重试，达到上限后保存失败消息
            if error is not None:
                if turn_service.retry_or_fail(turn, error):
                    await session.commit()
                    return
                await result_service.save_ai_result(
                    conversation,
                    turn,
                    {
                        "kind": "error",
                        "text": "AI 处理失败，请稍后重试。",
                    }
                )
            else:
                # 5. 调用成功时完成 Turn，并按结果类型保存 AI 结果
                turn_service.mark_completed(turn)
                if run_result["outcome_type"] == "handoff":
                    await result_service.save_handoff_result(
                        conversation,
                        turn,
                        run_result
                    )
                else:
                    await result_service.save_ai_result(
                        conversation,
                        turn,
                        run_result["content"],
                        message_id=run_result["message_id"]
                    )

            # 6. 推进会话已经处理完成的输入版本
            conversation.answered_revision = turn.snapshot_revision

            # 7. 原子提交 Turn、会话、消息、工单和 Outbox 事件
            await session.commit()


class AIWorker:

    def __init__(self):
        self.setting = get_settings()
        self.worker_id = f"{socket.gethostname()}:{os.getpid()}"
        self.turn_processor = TurnProcessor()
        self.session_factory = session_factory

    async def start(self):
        """
        循环执行turn的处理
        :return:
        """
        logger.info("AI Worker 已启动：%s", self.worker_id)
        while True:
            try:
                processed = await self.poll_and_process()

                if not processed:
                    await asyncio.sleep(self.setting.ai_worker_poll_interval_ms / 1000)
            except Exception:
                logger.exception("AI Worker 本轮轮询失败")
                await asyncio.sleep(1)

    async def poll_and_process(self) -> bool:

        await self._recover_expired_turns()

        # 1. 领取 Turn，并获取 AI Service 请求数据和用户 ID
        claimed_turn = await self.claim_turn()

        # 2. 如果没有领取到返回False
        if claimed_turn is None:
            return False

        # 3. 如果领取到了
        request_data, user_id = claimed_turn

        # 3. 调用轮次处理器处理
        await self.turn_processor.process(request_data, user_id)
        return True

    async def claim_turn(self) -> tuple[dict[str, Any], str] | None:
        """
        1.领取Turn
        2.构建AI_SERVICE请求的上下文
        :return:
        """
        async  with  self.session_factory() as session:
            turn_service = TurnService(session)
            # 1. 领取turn
            claimed_turn = await turn_service.claim_turn(self.worker_id)

            if claimed_turn is None:
                return None

            # 2. 构建上下文请求（当前轮次的消息给AI）
            request_data, user_id = await turn_service.build_ai_request_data(
                claimed_turn
            )
            await  session.commit()

            # 3. 返回
            return request_data, user_id

    async def _recover_expired_turns(self) -> None:
        """回收 Worker 中断遗留的过期租约。"""
        async with self.session_factory() as session:
            turn_service = TurnService(session)
            turns_and_conversations = await turn_service.list_expired_running_turns_with_conversations()

            for turn, conversation in turns_and_conversations:
                if conversation.input_revision != turn.snapshot_revision:
                    turn_service.mark_superseded(turn)
                else:
                    turn_service.requeue(
                        turn,
                        RuntimeError("Worker 租约超时")
                    )

            if turns_and_conversations:
                await session.commit()


async def main_async():
    await AIWorker().start()


if __name__ == "__main__":
    run_async(main_async())
