import random
import uuid
from datetime import datetime, timedelta
from typing import List

from app.core.config import settings
from app.models.matrix import MatrixEngineType
from app.repositories.matrix import RepositoryAddBotToMatrixTaskModel
from app.schemas.matrix import AddBotToMatrixTaskSchema


class AddBotToMatrixTaskService:

    def __init__(
            self,
            repository_matrix_task: RepositoryAddBotToMatrixTaskModel,
    ) -> None:
        self._repository_matrix_task = repository_matrix_task

    async def get_list(self, *args, **kwargs):
        return self._repository_matrix_task.list(*args, **kwargs)

    async def create_tasks(
            self,
            obj_id: uuid.UUID,
            donate_sum: int,
            engine_type: MatrixEngineType,
            create_donates: bool = True,
            first_task_minutes_delay: int | None = None,
            second_task_minutes_delay: int | None = None,
    ):
        now = datetime.now()

        task_data = {
            "obj_id": obj_id,
            "donate_sum": donate_sum,
            "engine_type": engine_type,
            "create_donates": create_donates
        }

        if not first_task_minutes_delay:
            first_task_minutes_delay = random.randint(
                settings.add_bot_to_matrix_first_task_interval.min_minutes,
                settings.add_bot_to_matrix_first_task_interval.max_minutes
            )

        if not second_task_minutes_delay:
            second_task_minutes_delay = random.randint(
                settings.add_bot_to_matrix_second_task_interval.min_minutes,
                settings.add_bot_to_matrix_second_task_interval.max_minutes
            )

        first_task_execute_at = now + timedelta(minutes=first_task_minutes_delay)
        second_task_execute_at = now + timedelta(minutes=second_task_minutes_delay)

        first_task = AddBotToMatrixTaskSchema(
            execute_at=first_task_execute_at,
            **task_data
        )
        second_task = AddBotToMatrixTaskSchema(
            execute_at=second_task_execute_at,
            **task_data
        )

        tasks_data = [
            first_task.model_dump(),
            second_task.model_dump(),
        ]

        self._repository_matrix_task.bulk_create(tasks_data)

    async def set_executed(self, ids: List[uuid.UUID], commit: bool = False,):
        return self._repository_matrix_task.set_executed(ids, commit)
