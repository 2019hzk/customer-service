import asyncio
import json
import logging
from redis.exceptions import RedisError

from atguigu.app.respositories.realtime import RealTimeOutboxRepository
from atguigu.app.services.realtime import build_realtime_event
from atguigu.common.config import get_settings
from atguigu.common.event_loop import run_async
from atguigu.infrastucture.db import session_factory, db_engine
from atguigu.infrastucture.redis import redis_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger(__name__)


class OutboxWorker:
    """将数据库中的待发布事件依次发送到 Redis。"""

    def __init__(self):
        self.settings = get_settings()
        self.session_factory = session_factory
        self.redis = redis_client

    async def start(self):
        """持续轮询 Outbox 表。"""
        logger.info("RealTimeOutbox Worker 已启动")
        while True:
            try:
                published = await self.publish_next_event()
            except Exception:
                logger.exception("RealTimeOutbox 事件处理失败")
                published = False

            if not published:
                await asyncio.sleep(
                    self.settings.outbox_worker_poll_interval_seconds
                )

    async def publish_next_event(self) -> bool:
        """发布一条事件；没有待处理事件时返回 False。"""
        # 1. 锁定最早的一条待发布事件
        async with self.session_factory() as session:
            outbox_repo = RealTimeOutboxRepository(session)
            event = await outbox_repo.find_next_unpublished()
            if event is None:
                return False

            # 2. 将数据库事件包装为前端需要的统一结构
            event_json = json.dumps(
                build_realtime_event(
                    event_id=event.id,
                    event_type=event.event_type,
                    event_data=event.data,
                    conversation_id=event.conversation_id,
                    event_created_at=event.created_at
                ),
                ensure_ascii=False
            )

            # 3. 发布成功后标记完成；失败则保留等待下轮重试
            try:
                await self.redis.publish(event.channel, event_json)
            except RedisError:
                outbox_repo.mark_publish_failed(event)
                await session.commit()
                logger.exception("RealTimeOutbox 事件 %s 发布失败", event.id)
                return False

            outbox_repo.mark_publish_succeeded(event)
            await session.commit()
            return True


async def main_async() -> None:
    try:
        await OutboxWorker().start()
    finally:
        await redis_client.aclose()
        await db_engine.dispose()


if __name__ == "__main__":
    run_async(main_async())
