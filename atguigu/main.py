from atguigu.common.config import get_settings

import uvicorn

from atguigu.common.event_loop import run_async


async def server():
    settings = get_settings()
    server = uvicorn.Server(
        uvicorn.Config(
            app="app.app:app",
            host=settings.api_host,
            port=settings.api_port,
            loop="none"
        )
    )

    await server.serve()


if __name__ == '__main__':
    uvicorn.run(run_async(server()))
