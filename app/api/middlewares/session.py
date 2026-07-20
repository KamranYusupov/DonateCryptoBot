from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware

from app.db.session import scope, DBManager


class SQLAlchemySessionMiddleware(BaseHTTPMiddleware):
    """Middleware для commit & close session"""

    async def dispatch(self, request, call_next):
        container = request.app.state.container

        db_manager = await container.db_manager()
        scope_token = scope.set(str(uuid4()))
        session = db_manager.create_session()

        try:
            response = await call_next(request)
            await session.commit()
            return response
        except:
            await session.rollback()
            raise
        finally:
            await db_manager.remove()
            scope.reset(scope_token)
