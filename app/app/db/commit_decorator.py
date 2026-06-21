from functools import wraps
from uuid import uuid4

import loguru
from dependency_injector.wiring import inject

from app.core.container import Container
from app.db.session import scope


@inject
def commit_and_close_session(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        scope_token = scope.set(str(uuid4()))
        db = Container.db()
        session = db.create_session()

        try:
            result = await func(*args, **kwargs)
            session.commit()
            return result
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
            db.remove()
            scope.reset(scope_token)

    return wrapper
