import loguru
from taskiq import TaskiqEvents

from app.core.taskiq import broker
from app.core.container import Container


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def on_worker_startup(state):
    container = Container()
    state.container = container