"""
Turn(AI)Worker
"""
import asyncio
import logging
import os
import socket
from typing import Any

from atguigu.app.schemas.user import CurrentUser
from atguigu.app.services.auth import AuthService
from atguigu.app.services.chat.turn import TurnService
from atguigu.infrastucture.db import session_factory
from atguigu.worker.ai.gateway import  AIServiceGateway
from atguigu.worker.ai.parser import  AIEventParser

logging.basicConfig(level=logging.INFO)
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
        self.event_parser=AIEventParser()

    async def process(self,
                      request_data: dict[str, Any],
                      request_message_id: str
                      ):
        # 1. 创建令牌
        access_token = self.auth_service.encode_access_token(CurrentUser(user_id=request_data['user_id']))

        # 2. (发送请求给AI_SERVICE/解析AI_SERVICE的事件类型以及数据/校验【二阶段】)
        error:Exception | None=None
        run_id:str | None=None
        run_result: dict[str,Any] | None=None
        try:
            run_id, run_result = await self.run_ai_pipeline(access_token, request_data)
        except Exception as  exec:
            error=exec
            logger.exception(f"{request_data['turn_id']}运行失败,原因:{exec}")

        # 3. 修改Turn状态、结果的保存
        self.finalize_result(run_id, run_result, request_message_id,error)


    async  def run_ai_pipeline(self,
                               token:str,
                               request_data:dict[str,Any])->tuple[str,dict[str,Any] | None] | None:
        """
        1. 发送两个节个阶段的请求以及对于第二个阶段的取消

        commit
        rollback

        commit:用户的一种确认
        cancel:用户不做了，取消

        :param token:
        :param request_data:
        :return:
        """

        # 1. 调用start_run(第一阶段)
        event=await self.ai_gateway.start_run(token,request_data)

        # 2. 找到run_id
        run_id=self.event_parser.find_run_id(event)

        # 3. 根据事件查询事件类型是否是run_decision_prepared
        prepared=self.event_parser.has_prepared_decision(event)

        commit=False
        # 4. 决策准备好了
        try:
            if prepared:
                # a) 校验快照版本是否过期了，如果要过期了，cancel_run 如果没有过期 调用 commit_run
                if not await self.validate_before_commit(request_data['turn_id'], run_id):
                    await self.ai_gateway.cancel_run(token, run_id)
                    return run_id, None
                # b) 调用commit_run
                event = await self.ai_gateway.commit_run(token, run_id, request_data['input_revision'])
                commit = True  # 变量

            return run_id, self.event_parser.parser_outcome(event)
        except Exception as  exec:
            if prepared and not commit:  # 控制二阶段（cancel 只能针对二阶段）
                await self.ai_gateway.cancel_run(token, run_id)
            raise exec

    async def validate_before_commit(self,
                                     turn_id:str,
                                     run_id:str
                                     )->bool:

        async  with session_factory() as session:
            turn_service= TurnService(session)

            # 1. 获取turn轮次和会话
            turn_and_conversation=await turn_service.find_turn_conversation_by_id(turn_id)

            # 2. 解包
            turn, conversation =turn_and_conversation

            if run_id:
                turn.run_id=run_id

            # 3. 校验
            if turn.snapshot_revision!= conversation.input_revision:
                # 标记当前turn过期了SUPERSEDED(修改turn的状态)
                turn_service.mark_superseded(turn)
                await session.commit()   # 数据库更新以及释放锁
                return False

            await session.commit()
            return True













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
        while True:
            try:
                processed = await self.poll_and_process()

                if not processed:
                    await asyncio.sleep(self.setting.ai_worker_poll_interval_ms / 1000)
            except Exception as exec:
                logger.exception("%s 执行失败了 原因:%s", self.worker_id, exec)
                await asyncio.sleep(1)

    async def poll_and_process(self) -> bool:

        # 1. 负责领取turn(request_data:调用AI_Service的上下文信息【当前消息、用户消息...】,request_message_id:用户当前消息的ID)
        claimed_turn = await self.claim_turn()

        # 2. 如果没有领取到返回False
        if claimed_turn is None:
            return False

        # 3. 如果领取到了
        request_data, request_message_id = claimed_turn

        # 3. 调用轮次处理器处理
        await self.turn_processor.process(request_data, request_message_id)
        return True

    async def claim_turn(self) -> tuple[dict[str, Any], str] | None:
        """
        1.领取Turn
        2.构建AI_SERVICE请求的上下文
        :return:
        """
        with   self.session_factory() as session:
            turn_service = TurnService(session)
            # 1. 领取turn
            claimed_turn = await turn_service.claim_turn(self.worker_id)

            if claimed_turn is None:
                return None

            # 2. 构建上下文请求（当前轮次的消息给AI）
            request_data, request_message_id = await turn_service.build_ai_request_data(claimed_turn)
            await  session.commit()

            # 3. 返回
            return request_data, request_message_id
