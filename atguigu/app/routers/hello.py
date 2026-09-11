from fastapi import APIRouter
from pydantic import BaseModel

# pydantic:数据校验  Web/Agent:Pydantic

router = APIRouter()


class User(BaseModel):
    """
    pydantic自动进行类型转换[能转的转换 不能转换的报错]以及参数类型的校验 过滤
    """
    name: str
    age: int



@router.get("/hello", response_model=User)
async def hello():
    return {"name": "hzk", "age": "18","address":"深圳"}
