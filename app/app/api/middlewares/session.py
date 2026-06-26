from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware

from app.db.session import scope, SyncSession


class SQLAlchemySessionMiddleware(BaseHTTPMiddleware):
    """Middleware для commit & close session"""

    def __init__(self, app, sync_session: SyncSession):
        super().__init__(app)
        self._sync_session = sync_session

    async def dispatch(self, request, call_next):
        scope_token = scope.set(str(uuid4()))
        session = self._sync_session.create_session()

        try:
            request.state.session = session
            response = await call_next(request)
            session.commit()
            return response
        except:
            session.rollback()
            raise
        finally:
            self._sync_session.remove()
            scope.reset(scope_token)
