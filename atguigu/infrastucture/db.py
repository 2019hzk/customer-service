"""
创建数据库异步引擎
创建数据库连接(session对象)
# session对象执行crud的sql语句 commit rollback

"""
import asyncio
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (AsyncEngine,
                                    create_async_engine,
                                    async_sessionmaker,
                                    AsyncSession

                                    )
from atguigu.common.config import get_settings
from atguigu.common.event_loop import run_async

db_engine: AsyncEngine = create_async_engine(
    url=get_settings().database_url,
    echo=False
)
#
# expire_on_commit: 提交后是否过期（上一步查询的数据提交之后是否还保留在内存中，
# 如果是True:提交之后改数据不在内存中，会重新用异步连接重新从数据库获取
session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=db_engine,
    expire_on_commit=False  # 用异步数据库连接对象的情况下 该属性一定要设置为False
)
async def get_db_session() -> AsyncGenerator[AsyncSession]:
    """
    1. 调用该方法的调用者：fast_api在处理路由请求的时候调用
    2. 方法返回的session要用yield,不能return
    :return:
    """
    async with session_factory() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise e


async def get_db_session_test():
    """
     session.execute(SQL):用session对象执行SQL语句"select 1"
     text("SQL"):标准写法：把SQL语句放到text中包一下
    :return:
    """
    async  for session in get_db_session():
        # CursorResult
        result = await session.execute(text("select 1"))

        print(result.scalars())


if __name__ == '__main__':
    # ProactorEventLoop:windows平台  linux:epoll()机制的select：最底层、最高效
    # 经常会和第三方的依赖包有冲突
    # psycopg：pgsql的数据库引擎三方出现了冲突
    # 解法：如何解？ 不用windows平台提供的ProactorEventLoop，用能够兼容各个平台的事件循环即可解决
    # asyncio.SelectorEventLoop(selectors.SelectSelector())
    # asyncio.run(get_db_session_test())

    run_async(get_db_session_test())
