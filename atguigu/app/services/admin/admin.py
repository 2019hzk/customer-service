from atguigu.app.respositories.admin.admin import AdminMetricsRepository


class AdminMetricsService:
    """提供管理员可见的客户服务指标。"""

    def __init__(self, repository: AdminMetricsRepository):
        self.repository = repository

    async def get_metrics(self) -> dict[str, int]:
        return await self.repository.get_metrics()
