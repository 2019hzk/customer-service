import redis.asyncio as redis

from atguigu.common.config import get_settings

redis_client = redis.from_url(
    get_settings().redis_url,
    decode_responses=True
)
