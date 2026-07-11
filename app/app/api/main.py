from contextlib import asynccontextmanager
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI

from app.core.config import settings
from app.api.endpoints.routers import api_router
from app.core.container import Container
from app.api.middlewares.session import SQLAlchemySessionMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    container = Container()
    await container.init_resources()

    app.state.container = container

    yield

    await container.shutdown_resources()


def create_app() -> FastAPI:
    app_kwargs: Dict[str, Any] = {"lifespan": lifespan}
    if not settings.debug:
       app_kwargs.update({
           "docs_url": None,
           "redoc_url": None,
           "openapi_url": None
       })

    fastapi_app = FastAPI(**app_kwargs)
    fastapi_app.add_middleware(SQLAlchemySessionMiddleware)
    fastapi_app.include_router(api_router, prefix=settings.api_prefix)

    return fastapi_app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(app="app.api.main:app", host="0.0.0.0", reload=settings.debug)