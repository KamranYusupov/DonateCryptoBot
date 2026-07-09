from contextvars import ContextVar
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    async_scoped_session,
    AsyncSession,
)

scope: ContextVar = ContextVar("db_session_scope")


def scopefunc():
    try:
        return scope.get()
    except LookupError:
        raise LookupError("Scope is not set.")


class DBManager:
    def __init__(self, db_url: str):
        self.engine = create_async_engine(
            url=str(db_url),
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
        )
        self.scoped_session = async_scoped_session(
            self.session_factory,
            scopefunc=scopefunc,
        )

    def create_session(self):
        return self.scoped_session()

    async def remove(self):
        await self.scoped_session.remove()

async def init_db_pool(db_url: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    db_manager = DBManager(db_url)

    yield db_manager

    await db_manager.engine.dispose()