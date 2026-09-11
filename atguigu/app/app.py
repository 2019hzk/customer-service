from fastapi import FastAPI
from atguigu.app.routers import hello

app = FastAPI(description="FastAPI集成的客服服务")

app.include_router(hello.router)
