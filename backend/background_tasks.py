"""Fire-and-forget background task registry.

`asyncio.create_task()` returns tasks that Python only holds a *weak* reference
to — if no strong reference is kept, the garbage collector may cancel a task
mid-flight. Additionally, a graceful FastAPI shutdown should wait for these
tasks to complete so we don't drop e.g. an in-flight approved-proposal email.

Usage:
    from background_tasks import spawn
    spawn(_deliver_email(...))

At shutdown call `await drain(timeout=10)` to await any outstanding work.
"""
import asyncio
from typing import Set, Coroutine, Any

from core import logger

_TASKS: Set[asyncio.Task] = set()


def spawn(coro: Coroutine[Any, Any, Any], *, name: str | None = None) -> asyncio.Task:
    """Schedule *coro* on the current loop and hold a strong reference until done."""
    task = asyncio.create_task(coro, name=name)
    _TASKS.add(task)
    task.add_done_callback(_TASKS.discard)
    return task


async def drain(timeout: float = 10.0) -> None:
    """Await outstanding tasks (up to *timeout* seconds). Never raises."""
    if not _TASKS:
        return
    logger.info(f"draining {len(_TASKS)} background task(s), timeout={timeout}s")
    try:
        await asyncio.wait_for(
            asyncio.gather(*list(_TASKS), return_exceptions=True),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        logger.warning(f"drain timeout — {len(_TASKS)} background task(s) still running")
    except Exception as e:  # defensive; gather with return_exceptions shouldn't raise
        logger.error(f"drain error: {e}")


def outstanding_count() -> int:
    """For diagnostics / tests."""
    return len(_TASKS)
