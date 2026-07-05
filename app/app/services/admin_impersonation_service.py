from typing import Tuple

from redis.asyncio import Redis

class AdminImpersonationService:
    def __init__(
            self,
            redis_client: Redis,
            impersonation_user_id_key: str
    ):
        self._redis_client = redis_client
        self.impersonation_user_id_key = impersonation_user_id_key

    async def get_impersonated_user_id(self) -> int | None:
        user_id = await self._redis_client.get(self.impersonation_user_id_key)
        return int(user_id) if user_id else None

    async def start_impersonation(
            self,
            user_id: int,
            ttl_seconds: int = 600,
    ) -> None:
        await self._redis_client.setex(
            self.impersonation_user_id_key,
            time=ttl_seconds,
            value=str(user_id),
        )

    async def end_impersonation(self) -> None:
        await self._redis_client.delete(
            self.impersonation_user_id_key,
        )