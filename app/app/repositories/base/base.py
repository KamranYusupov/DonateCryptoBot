from uuid import UUID
from typing import Generic, Optional, Type, TypeVar

from sqlalchemy.exc import NoResultFound, MultipleResultsFound
from sqlalchemy import select, update, delete


ModelType = TypeVar("ModelType")


class RepositoryBase(Generic[ModelType,]):
    """Репозиторий с базовым CRUD"""

    def __init__(self, model: Type[ModelType], session) -> None:
        self._model = model
        self._session = session

    async def create(self, obj_in) -> ModelType:
        obj_in_data = dict(obj_in)
        db_obj = self._model(**obj_in_data)

        self._session.add(db_obj)
        await self._session.flush()

        return db_obj

    async def get(
        self,
        *args,
        **kwargs,
    ) -> Optional[ModelType]:
        statement = (
            select(self._model)
            .filter(*args)
            .filter_by(**kwargs)
        )
        result = await self._session.execute(statement)
        return result.scalars().first()

    async def list(self, *args, **kwargs):
        statement = select(self._model).filter(*args).filter_by(**kwargs)
        result = await self._session.execute(statement)
        return result.scalars().all()

    async def update(self, *, obj_id: UUID, obj_in) -> ModelType:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        statement = (
            update(self._model).where(self._model.id == obj_id).values(**update_data)
        )
        await self._session.execute(statement)

    async def delete(self, *args, obj_id: UUID, **kwargs) -> None:
        statement = delete(self._model).where(self._model.id == obj_id)
        await self._session.execute(statement)

    async def exists(self, *args, **kwargs) -> bool:
        try:
            statement = select(self._model).filter(*args).filter_by(**kwargs)
            result = await self._session.execute(statement)
            result.one()
        except MultipleResultsFound:
            pass
        except NoResultFound:
            return False

        return True

