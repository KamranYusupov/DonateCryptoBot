from contextlib import asynccontextmanager
from uuid import uuid4

from aiogram import BaseMiddleware

from app.db.session import scope, DBManager


class SQLAlchemySessionMiddleware(BaseMiddleware):
    """Middleware для commit & close  session"""

    def __init__(self, db_manager: DBManager):
        super().__init__()
        self._db_manager = db_manager

    async def __call__(self, handler, event, data):
        async with self.db_session_maker() as session:
            data["session"] = session
            return await handler(event, data)

    @asynccontextmanager
    async def db_session_maker(self):
        scope_token = scope.set(str(uuid4()))
        session = self._db_manager.create_session()

        try:
            yield session
            await session.commit()
        except:
            await session.rollback()
            raise
        finally:
            await self._db_manager.remove()
            scope.reset(scope_token)