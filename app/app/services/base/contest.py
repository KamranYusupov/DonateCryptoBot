import uuid
from datetime import datetime, time
from typing import TypeVar, Generic, List, Tuple, Dict

import loguru

from app.core.config import settings
from app.domain.contest_calculator import ContestResultCalculator
from app.repositories.base.contest import RepositoryContestBase, RepositoryContestPointBase
from app.schemas.contest_domain import ContestUpdateSchema, ContestUserItemSchema
from app.utils.datetime import get_start_of_week, to_main_tz
from app.models.mixins import AbstractContest, AbstractContestPoint

ContestRepositoryType = TypeVar(
    "ContestRepositoryType",
    bound=RepositoryContestPointBase,
)
ContestPointRepositoryType = TypeVar(
    "ContestPointRepositoryType",
    bound=RepositoryContestPointBase,
)
ContestModelType = TypeVar(
    "ContestModelType",
    bound=AbstractContest,
)
ContestPointModelType = TypeVar(
    "ContestPointModelType",
    bound=AbstractContestPoint
)


class BaseContestService(Generic[ContestRepositoryType, ContestPointRepositoryType]):
    """Базовый сервис с механикой конкурсов"""

    def __init__(
            self,
            repository_contest: ContestRepositoryType,
            repository_contest_point: ContestPointRepositoryType
    ) -> None:
        self._repository_contest = repository_contest
        self._repository_contest_point = repository_contest_point

    def _get_period_start(self) -> datetime:
        """
        Определяет точку отсчета для текущего конкурса.
        По умолчанию - понедельник 00:00. Наследники могут переопределить.
        """
        today = get_start_of_week()

        dt = datetime.combine(
            today,
            time(0, 0, 0),
            tzinfo=settings.timezone_info
        )
        return to_main_tz(dt)

    async def get_current_contest(self) -> ContestModelType:
        period_start = self._get_period_start()
        return await self._repository_contest.get(start_at=period_start)

    async def get_or_create_current_contest(self) -> Tuple[ContestModelType, bool]:
        current_contest = await self.get_current_contest()
        if current_contest:
            return current_contest, False

        period_start = self._get_period_start()
        current_contest = await self._repository_contest.create(
            {"start_at": period_start}
        )
        return current_contest, True

    async def get_contest_points(self, *args, **kwargs) -> List[ContestPointModelType]:
        return await self._repository_contest_point.list(*args, **kwargs)

    async def contest_exists(self, *args, **kwargs) -> bool:
        return await self._repository_contest.exists(*args, **kwargs)

    async def get_contest(self, *args, **kwargs) -> ContestModelType:
        return await self._repository_contest.get(*args, **kwargs)

    async def get_contests_list(self, *args, **kwargs) -> List[ContestModelType]:
        return await self._repository_contest.get_ordered_list(*args, **kwargs)

    async def get_ids(self, *args, **kwargs) -> List[uuid.UUID]:
        return await self._repository_contest.get_ordered_ids(*args, **kwargs)

    async def get_last_contest(self, *args, **kwarg) -> ContestModelType:
        return await self._repository_contest.get_last(*args, **kwarg)

    async def get_previous_active_contest(self, current_contest_id: uuid.UUID):
        return await self._repository_contest.get_previous_active_contest(
            current_contest_id=current_contest_id
        )

    async def _get_user_str_map(
            self,
            user_ids: set[int]
    ) -> Dict[int, str]:
        raise NotImplementedError

    def _calculate_prize_fund(
            self,
            init_prize_fund: int,
            total_points: int
    ) -> int:
        return init_prize_fund

    async def update_results(self, contest_id: uuid.UUID) -> None:
        """Единый оркестратор обновления для ВСЕХ типов конкурсов."""
        contest = await self._repository_contest.get(id=contest_id)
        if not contest:
            return

        users_points = await self._repository_contest_point.get_grouped_points(contest_id=contest.id)
        if not users_points:
            return

        user_points_schemas = []
        user_ids_set = set()
        for inx, (user_id, points_count) in enumerate(users_points):
            contest_item = ContestUserItemSchema(
                user_id=user_id,
                points_count=points_count
            )

            user_ids_set.add(user_id)
            user_points_schemas.append(contest_item)

        user_str_map = await self._get_user_str_map(user_ids_set)
        calculated_result = ContestResultCalculator.calculate(
            grouped_user_points=user_points_schemas,
            user_str_map=user_str_map,
        )

        update_schema = ContestUpdateSchema()
        if calculated_result.total_points:
            update_schema.prize_fund = self._calculate_prize_fund(
                init_prize_fund=contest.init_prize_fund,
                total_points=calculated_result.total_points
            )

        if contest.top_10_rating != calculated_result.top_10_rating:
            update_schema.top_10_rating = calculated_result.top_10_rating

        if contest.results != calculated_result.results:
            update_schema.results = calculated_result.results


        update_data = update_schema.model_dump(exclude_unset=True)
        if update_data:
            await self._repository_contest.update(
                obj_id=contest.id,
                obj_in=update_data
            )

    async def process_periodic_update(self) -> None:
        """Оркестратор жизненного цикла: обновляет текущий и закрывает прошлый."""

        current_contest, _ = await self.get_or_create_current_contest()
        await self.update_results(current_contest.id)

        previous_contest = await self.get_previous_active_contest(
            current_contest_id=current_contest.id,
        )
        if previous_contest:
            await self.update_results(previous_contest.id)
            await self._repository_contest.update(
                obj_id=previous_contest.id,
                obj_in={"is_archived": True}
            )
