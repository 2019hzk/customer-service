import asyncio
from typing import Any

import uvicorn
from fastapi import FastAPI, Response

from atguigu.common.utils import get_uid

app = FastAPI(title=" AI Service")

prepared_runs: dict[str, dict[str, Any]] = {}


def build_event(
        event_type: str,
        run_id: str,
        **event_data: Any
) -> dict[str, Any]:
    """构建 Customer Service 能够解析的模拟事件。"""
    return {
        "event_type": event_type,
        "event_data": {
            "run_id": run_id,
            **event_data
        }
    }


def get_latest_text(request: dict[str, Any]) -> str:
    """提取当前 Turn 中最后一条文本消息。"""
    return str(request["messages"][-1]["content"].get("text", ""))


def get_order_id(request: dict[str, Any]) -> str | None:
    """从当前消息和历史消息中提取订单 ID。"""
    for message in reversed(
            request.get("history", []) + request.get("messages", [])
    ):
        content = message.get("content", {})
        if content.get("object_type") == "order":
            return str(content["object_id"])
    return None


@app.post("/internal/v1/agent/runs")
async def start_run(request: dict[str, Any]) -> dict[str, Any]:
    """根据测试关键词模拟 AI 的第一阶段结果。"""
    await asyncio.sleep(0.1)

    run_id = get_uid("run")
    text = get_latest_text(request)

    if "我要转人工" in text:  # 模拟转人工结果
        event = build_event(
            "run_handoff_requested",
            run_id,
            summary="用户主动申请人工服务，请客服查看历史会话并接入处理。",
            message="已收到您的请求，正在为您安排人工客服，请稍候。"
        )
    elif "我要取消订单" in text:  # 模拟两阶段业务写操作
        prepared_runs[run_id] = request
        event = build_event("run_decision_prepared", run_id)
    else:  # 模拟一阶段业务读操作
        # 测试 Worker 重试时，临时取消下一行注释
        # raise RuntimeError("模拟 AI Service 处理异常")

        event = build_event(
            "run_completed",
            run_id,
            message_id=get_uid("ai_msg"),
            content={
                "text": f"模拟 AI 回复：{text or '您好，请问有什么可以帮助您？'}"
            }
        )

    return event


@app.post("/internal/v1/agent/runs/{run_id}/commit")
async def commit_run(
        run_id: str
) -> dict[str, Any]:
    """提交已经准备好的模拟业务决策。"""
    request = prepared_runs.pop(run_id)
    order_id = get_order_id(request)
    href = f"/me/orders/{order_id}/cancel" if order_id else "/me"
    event = build_event(
        "run_completed",
        run_id,
        message_id=get_uid("ai_msg"),
        content={
            "text": "取消订单需要您在订单页面确认。",
            "action": {
                "label": "前往取消订单",
                "description": "打开订单页面，确认订单状态后提交取消。",
                "href": href
            }
        }
    )
    return event


@app.post(
    "/internal/v1/agent/runs/{run_id}/cancel",
    status_code=204
)
async def cancel_run(run_id: str) -> Response:
    """取消尚未提交的模拟业务决策。"""
    prepared_runs.pop(run_id)
    return Response(status_code=204)


if __name__ == '__main__':
    uvicorn.run("app:app", host="0.0.0.0", port=8002)
