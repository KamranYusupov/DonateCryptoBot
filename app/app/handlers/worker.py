import asyncio
from typing import Callable, List, Awaitable, Optional

import loguru

from app.core.config import settings
from app.tasks.contest import (
    update_sponsors_contest_task,
    update_registration_contest_task,
)


async def update_contests_task_worker(delay: Optional[int] = None) -> None:
    delay = delay or settings.update_contests_task_delay
    while True:
        try:
            await update_sponsors_contest_task()
            await update_registration_contest_task()
        except Exception as e:
            loguru.logger.error(
                f"Error during update_contest_tasks: {e}",
                exc_info=True,
            )

        await asyncio.sleep(delay)


def get_workers() -> List[Callable[..., Awaitable[None]]]:
    return [
        update_contests_task_worker
    ]


















