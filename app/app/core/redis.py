from typing import AsyncIterator

from redis.asyncio import Redis


async def init_redis_pool(
        redis_url: str,
        decode_responses: bool = True,
        health_check_interval: int = 30,
) -> AsyncIterator[Redis]:
    client = Redis.from_url(
        redis_url,
        decode_responses=decode_responses,
        health_check_interval=health_check_interval
    )
    yield client

    await client.close()