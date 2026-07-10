from typing import Generic, Optional, TypeVar, Sequence
from uuid import UUID

from app.repositories.base.base import RepositoryBase
from app.db.base import Base

RepositoryType = TypeVar("RepositoryType", bound=RepositoryBase)
ModelType = TypeVar("ModelType", bound=Base)

class CrudServiceMixin(Generic[RepositoryType]):
    """Миксин с crud для сервисов"""

    def __init__(self, repository: RepositoryType) -> None:
        self._repository = repository

    async def create(self, obj_in) -> ModelType:
        return await self._repository.create(obj_in=obj_in)

    async def get(self, *args, **kwargs) -> Optional[ModelType]:
        return await self._repository.get(*args, **kwargs)

    async def list(self, *args, **kwargs) -> Sequence[ModelType]:
        return await self._repository.list(*args, **kwargs)

    async def update(self, *, obj_id: UUID, obj_in) -> ModelType:
        return await self._repository.update(obj_id=obj_id, obj_in=obj_in)

    async def delete(self, *args, obj_id: UUID, **kwargs) -> None:
        return await self._repository.delete(*args, obj_id=obj_id, **kwargs)

    async def exists(self, *args, **kwargs) -> bool:
        return await self._repository.exists(*args, **kwargs)
