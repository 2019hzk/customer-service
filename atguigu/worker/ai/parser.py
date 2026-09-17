from typing import Any

from atguigu.app.schemas.event import AgentEventType


class AIEventParser:

    @staticmethod
    def find_run_id(event: dict[str, Any]) -> str:
        run_id = event.get("event_data", {}).get("run_id")

        if run_id:
            return run_id

        raise ValueError(f"AI Service 没有返回run_id")

    @staticmethod
    def has_prepared_decision(event: dict[str, Any]) -> bool:
        return event.get('event_type') == AgentEventType.RUN_DECISION_PREPARED

    @staticmethod
    def parser_outcome(event: dict[str, Any]) -> dict[str, Any]:
        event_type = event["event_type"]
        event_data = event.get("event_data", {})

        if event_type == AgentEventType.RUN_FAILED:
            raise RuntimeError(
                str(event_data.get('message') or "AI Service 处理失败")
            )

        if event_type == AgentEventType.RUN_COMPLETED:
            return {**event_data, "outcome_type": "message"}

        if event_type == AgentEventType.RUN_HANDOFF_REQUESTED:
            return {
                **event_data,
                "outcome_type": "handoff",
                "summary": str(event_data.get("summary") or "用户请求人工客服"),
                # summary：给人工客服看的工单摘要(例如：用户希望取消订单 order_123，但订单已发货，现在无法直接取消，需要人工确认后续处理方式。)
                "content": {
                    "text": str(event_data.get("message") or "正在为你转接人工客服，请稍候。")
                    # message：给用户看的转人工提示 简短、不包含细节(例如：您的订单已经发货，需要人工客服进一步处理，正在为您转接，请稍候。)
                },
            }
        raise RuntimeError("AI Service 没有返回最终处理结果")
