from typing import Annotated

from fastapi import APIRouter, Header

from atguigu.app.dependencies import AdminMetricsServiceDep, get_auth_service
from atguigu.app.schemas.admin.admin import AdminMetricsResponse

router = APIRouter(tags=["管理员路由"], prefix="/api/v1/admin")


@router.get("/metrics", response_model=AdminMetricsResponse)
async def get_admin_metrics(
        metrics_service: AdminMetricsServiceDep,
        authorization: Annotated[str | None, Header()] = None
):
    """返回仅管理员可访问的客户服务指标。"""
    get_auth_service().get_authorized_user(authorization, "admin")
    return await metrics_service.get_metrics()
