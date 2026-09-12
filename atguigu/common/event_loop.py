import asyncio
import selectors
from collections.abc import Coroutine


def run_async[ResultT](
        coro: Coroutine
) -> ResultT:
    return asyncio.run(coro,
                       loop_factory=lambda:
                       asyncio.SelectorEventLoop(selectors.SelectSelector()))
