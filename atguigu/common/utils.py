from datetime import datetime, UTC
from typing import Self
from uuid import uuid4


def get_utcnow() -> datetime:
    return datetime.now(UTC)


def get_uid(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class User:
    id: str
    name: str
    age: int

    @classmethod
    def test(cls) ->"User":
        return cls()
