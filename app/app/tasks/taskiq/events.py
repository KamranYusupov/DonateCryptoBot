import loguru
from taskiq import TaskiqEvents

from app.core.taskiq import broker


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def on_worker_startup(state):
    from app.core.container import container

    state.container = container
    loguru.logger.info("Worker is starting...")