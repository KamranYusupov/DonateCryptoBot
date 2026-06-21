from contextlib import asynccontextmanager
from uuid import uuid4

from aiogram import BaseMiddleware

from app.db.session import scope, SyncSession


class SQLAlchemySessionMiddleware(BaseMiddleware):
    """Middleware для commit & close  session"""

    def __init__(self, sync_session: SyncSession):
        super().__init__()
        self._sync_session = sync_session

    async def __call__(self, handler, event, data):
        async with self.db_session_maker() as session:
            data["session"] = session
            return await handler(event, data)

    @asynccontextmanager
    async def db_session_maker(self):
        scope_token = scope.set(str(uuid4()))
        session = self._sync_session.create_session()

        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
            self._sync_session.remove()
            scope.reset(scope_token)