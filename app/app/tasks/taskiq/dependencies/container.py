from typing import Annotated, Container

import loguru
from dependency_injector.containers import DeclarativeContainer
from taskiq import TaskiqDepends, Context

from app.tasks.taskiq.dependencies.context import ContextDependency


def get_container(context: ContextDependency) -> Container:
    return getattr(context.state, "container")


ContainerDependency = Annotated[DeclarativeContainer, TaskiqDepends(get_container)]




