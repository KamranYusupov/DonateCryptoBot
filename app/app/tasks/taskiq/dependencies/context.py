from typing import Annotated

from taskiq import Context, TaskiqDepends

ContextDependency = Annotated[Context, TaskiqDepends()]
