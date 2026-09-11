from typing import Literal

from pydantic import BaseModel


class CurrentUser(BaseModel):
    user_id: str
    role: Literal["customer", "agent", "admin"] = "customer"
