from typing import Any

import httpx

from atguigu.common.config import Settings, get_settings


class AIServiceGateway:
    """调用真实 AI Service，并解析单个 JSON 事件。"""

    def __init__(
        self,
        settings: Settings | None = None
    ):
        self.settings = settings or get_settings()

    async def start_run(
        self,
        token: str,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        """启动 AI Run，返回计算结果或待提交决策。"""
        return await self._post_json(
            "/internal/v1/agent/runs",
            token,
            request,
        )

    async def commit_run(
        self,
        token: str,
        run_id: str,
        input_revision: int,
    ) -> dict[str, Any]:
        """提交快照校验通过的业务决策。"""
        return await self._post_json(
            f"/internal/v1/agent/runs/{run_id}/commit",
            token,
            {"input_revision": input_revision},
        )

    async def cancel_run(
        self,
        token: str,
        run_id: str,
    ) -> None:
        """取消快照已经过期或处理失败的 AI Run。"""
        await self._post(
            f"/internal/v1/agent/runs/{run_id}/cancel",
            token,
        )

    async def _post_json(
        self,
        path: str,
        token: str,
        request: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = await self._post(path, token, request)
        event = response.json()
        if not isinstance(event, dict):
            raise RuntimeError("AI Service 返回的事件格式错误")
        return event

    async def _post(
        self,
        path: str,
        token: str,
        request: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """发送 AI Service JSON 请求。"""
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Internal-Service-Token": self.settings.internal_service_token,
            "Accept": "application/json",
        }
        timeout = httpx.Timeout(
            self.settings.ai_timeout_seconds,
            connect=5,
        )

        async with httpx.AsyncClient(
            timeout=timeout,
            trust_env=False,
        ) as client:
            response = await client.post(
                f"{self.settings.ai_service_url}{path}",
                headers=headers,
                json=request,
            )
            response.raise_for_status()
            return response
