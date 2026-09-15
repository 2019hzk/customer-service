from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from atguigu.app.routers.chat import conversation, message
from atguigu.common.config import get_settings

app = FastAPI(description="FastAPI集成的客服服务")

app.include_router(conversation.router)
app.include_router(message.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,  # 自定义cookie或者认证信息
    allow_methods=["*"],  # 允许任意的请求方式
    allow_headers=["*"],  # 允许自定义请求头
)
