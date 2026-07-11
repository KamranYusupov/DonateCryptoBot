from functools import wraps
from uuid import uuid4

import loguru
from dependency_injector.wiring import inject

from app.db.session import scope

def commit_and_close_session(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        scope_token = scope.set(str(uuid4()))
        container = kwargs.get("container")

        db_manager = await container.db_manager()
        session = db_manager.create_session()

        try:
            result = await func(*args, **kwargs)
            await session.commit()
            return result
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await db_manager.remove()
            scope.reset(scope_token)

    return wrapper


def set_scope_session(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        scope_token = scope.set(str(uuid4()))
        container = kwargs.get("container")

        db_manager = await container.db_manager()
        db_manager.create_session()

        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            raise e
        finally:
            await db_manager.remove()
            scope.reset(scope_token)

    return wrapper