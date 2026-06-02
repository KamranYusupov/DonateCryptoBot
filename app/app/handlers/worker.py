import asyncio
from typing import Callable, List, Awaitable, Optional

import loguru

from app.core.config import settings
from app.tasks.matrix import execute_bot_matrix_tasks
from app.tasks.contest import (
    update_sponsors_contest_task,
    update_registration_contest_task,
)


async def add_bot_to_matrix_task_worker(delay: Optional[int] = None) -> None:
    delay = delay or settings.add_bot_to_matrix_task_delay
    while True:
        loguru.logger.info("Executing add_bot_to_matrix_tasks...")
        try:
            await execute_bot_matrix_tasks()
        except Exception as e:
            loguru.logger.error(
                f"Error during update_contest_tasks: {e}",
                exc_info=True,
            )

        await asyncio.sleep(delay)


async def update_contests_task_worker(delay: Optional[int] = None) -> None:
    delay = delay or settings.update_contests_task_delay
    while True:
        loguru.logger.info("Executing update_contests_task...")
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
        add_bot_to_matrix_task_worker,
        update_contests_task_worker
    ]


















