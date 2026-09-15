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
            return event_data

        raise RuntimeError("AI Service 没有返回最终处理结果")
