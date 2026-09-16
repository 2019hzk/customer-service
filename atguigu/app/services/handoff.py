from sqlalchemy.ext.asyncio import AsyncSession
from atguigu.app.respositories.handoff import HandoffRepository
from atguigu.models.models import Conversation, Handoff, Message


class HandoffService:
    """管理人工工单的创建、接单、回复和结束。"""

    def __init__(self, session: AsyncSession):
        # 1. 保存当前请求使用的数据库会话
        self.session = session

        # 2. 初始化工单业务需要的 Repository 和实时事件服务
        self.handoff_repository = HandoffRepository(session)

    async def get_or_create_open_handoff(
            self,
            conversation: Conversation,
            *,
            summary: str
    ) -> Handoff:
        """查询开放工单，不存在时创建 waiting 工单。"""
        # 1. 查询当前用户已有的 waiting 或 active 工单
        handoff = await self.handoff_repository.find_open_by_user_id(
            conversation.user_id
        )

        # 2. 已有开放工单时更新摘要并直接复用
        if handoff is not None:
            handoff.summary = summary
            return handoff

        # 3. 没有开放工单时创建 waiting 工单
        handoff = Handoff(
            conversation_id=conversation.id,
            user_id=conversation.user_id,
            summary=summary,
            status="waiting"
        )
        self.handoff_repository.add(handoff)

        # 4. 刷新到数据库
        await self.session.flush()
        return handoff

    async def list_open_handoffs(self) -> list[Handoff]:
        """返回等待中和服务中的工单。"""
        # 1. 查询客服工作台需要展示的 waiting 和 active 工单
        return await self.handoff_repository.list_open()



