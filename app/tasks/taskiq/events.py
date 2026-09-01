import loguru
from taskiq import TaskiqEvents

from app.core.taskiq import broker

@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def on_worker_startup(state):
    from app.core.container import Container

    container = Container()
    await container.init_resources()
    state.container = container
    loguru.logger.info("Worker is starting...")


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def on_worker_startup(state):
    container = state.container
    await container.shutdown_resources()
    loguru.logger.info("Worker is stoping...")