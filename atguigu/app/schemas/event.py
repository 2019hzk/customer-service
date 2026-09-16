from enum import StrEnum



class RealTimeOutBoxType(StrEnum):
    MESSAGE_CREATED="message_created"
    HANDOFF_CHANGED="handoff_changed"



class AgentEventType(StrEnum):
    """AI Service 返回给 Worker 的内部事件类型。"""

    RUN_DECISION_PREPARED = "run_decision_prepared"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"
    RUN_HANDOFF_REQUESTED = "run_handoff_requested"
