from pydantic import BaseModel


class AdminMetricsResponse(BaseModel):
    """客户服务后台的聚合指标。"""

    conversations: int
    messages: int
    handoffs: int
    queued: int
    human: int
