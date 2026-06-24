from typing import Annotated

import loguru
from dependency_injector.containers import DeclarativeContainer
from taskiq import TaskiqDepends

from app.tasks.taskiq.dependencies.context import ContextDependency


def get_container(context: ContextDependency):
    from app.core.container import container as default_container

    return getattr(context.state, "container", default_container)

ContainerDependency = Annotated[DeclarativeContainer, TaskiqDepends(get_container)]




