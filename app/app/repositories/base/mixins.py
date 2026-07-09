from typing import List, Dict, Any, Optional, Sequence

from sqlalchemy import insert, update, select, func
from sqlalchemy.ext.asyncio import AsyncSession


class BulkCreateMixin:
    """Примесь для массовой вставки записей."""

    _model: Any
    _session: AsyncSession

    async def bulk_create(self, objects_in: List[Dict]) -> None:
        if not objects_in:
            return

        statement = insert(self._model).values(objects_in)
        await self._session.execute(statement)
        await self._session.flush()


class BulkUpdateMixin:
    """Примесь для массового обновления записей."""

    _model: Any
    _session: AsyncSession

    async def bulk_update(
            self,
            objects_in: List[Dict],
            return_objects: bool = False
    ) -> Optional[Sequence[Any]]:
        if not objects_in:
            return [] if return_objects else None

        statement = update(self._model)

        if return_objects:
            statement = statement.returning(self._model)
            result = await self._session.execute(statement, objects_in)
            await self._session.flush()
            return result.scalars().all()

        await self._session.execute(statement, objects_in)
        await self._session.flush()
        return None


class CountMixin:
    """Примесь для получения числа записей."""

    _model: Any
    _session: AsyncSession

    async def get_count(self, **kwargs) -> None:
        statement = (
            select(func.count(self._model.id))
            .filter_by(**kwargs)
        )

        result = await self._session.execute(statement)
        return result.scalar()
