import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis.exceptions import RedisError

from atguigu.app.services.realtime import (
    STAFF_CHANNEL,
    user_channel
)
from atguigu.infrastucture.redis import redis_client
from atguigu.app.dependencies import get_auth_service

router = APIRouter()


@router.websocket("/api/v1/realtime")
async def realtime_socket(
        websocket: WebSocket
):
    """认证客户端，并把授权频道中的 Redis 消息转发给它。"""
    await websocket.accept()

    # 1. 验证前端发送的访问令牌
    try:
        auth_message = await websocket.receive_json()
        current_user = get_auth_service().decode_access_token(
            str(auth_message["token"])
        )
    except (KeyError, TypeError):
        await websocket.close(401, "Invalid access token")
        return

    # 2. 根据身份确定唯一允许订阅的频道
    channel = user_channel(current_user.user_id) if current_user.role == "customer" else STAFF_CHANNEL

    # 3. 订阅 Redis，并通知前端连接成功
    pubsub = redis_client.pubsub()
    try:
        await pubsub.subscribe(channel)
        await websocket.send_json({"event_type": "connected"})

        async def forward_events():
            """把 Redis 业务事件转发给前端"""
            try:
                async for item in pubsub.listen():
                    if item["type"] == "message":
                        await websocket.send_text(item["data"])
            except RedisError:
                await websocket.close()

        # 4. 后台转发消息，当前协程只等待前端断开
        forward_task = asyncio.create_task(forward_events())
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            forward_task.cancel()
            await asyncio.gather(
                forward_task,
                return_exceptions=True
            )
    finally:
        # 5. 连接结束后关闭 Redis 订阅
        await pubsub.aclose()
