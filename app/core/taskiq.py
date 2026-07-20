import taskiq_redis
from taskiq import TaskiqScheduler, TaskiqEvents
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import RedisAsyncResultBackend

from app.core.config import settings

result_backend = RedisAsyncResultBackend(
    redis_url=settings.taskiq_backend_url,
    keep_results=True,
    result_ex_time=settings.taskqi_result_backend_result_ex_time,
)
broker = taskiq_redis.ListQueueBroker(
    url=settings.taskiq_broker_url,
).with_result_backend(result_backend)

redis_source = taskiq_redis.RedisScheduleSource(
    url=settings.taskiq_broker_url,
)
scheduler = TaskiqScheduler(
    broker=broker,
    sources=[
        LabelScheduleSource(broker),
        redis_source,
    ],
)
