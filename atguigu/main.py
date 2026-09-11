from atguigu.common.config import get_settings

import uvicorn

if __name__ == '__main__':
    settings = get_settings()
    uvicorn.run(app="app.app:app", host=settings.api_host, port=settings.api_port)
