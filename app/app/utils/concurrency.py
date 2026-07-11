import asyncio
import logging
from typing import Iterable, Awaitable, Any
from itertools import batched

logger = logging.getLogger(__name__)


async def gather_by_batches(
        coroutines: Iterable[Awaitable[Any]],
        chunk_size: int = 100,
        sleep_after_chunk: int = 0,
) -> None:
    """
    Конкурентно выполняет корутины пачками, не блокируя Event Loop.
    """
    for chunk in batched(coroutines, chunk_size):

        results = await asyncio.gather(*chunk, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Ошибка при выполнении задачи в батче: {result}")

        await asyncio.sleep(sleep_after_chunk)
