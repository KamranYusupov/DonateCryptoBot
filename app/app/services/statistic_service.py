from typing import Any

from app.repositories.statistic import RepositoryAdminStatistic
from app.models.statistic import AdminStatistic
from app.schemas.statistic import AdminStatisticSchema, UpdateAdminStatisticSchema


class AdminStatisticService:
    def __init__(
            self,
            repository_admin_statistic: RepositoryAdminStatistic,
    ):
        self._repository_admin_statistic = repository_admin_statistic

    def get_statistic(self) -> AdminStatisticSchema:
        db_statistic = self._repository_admin_statistic.get()
        return AdminStatisticSchema.model_validate(db_statistic)

    def update(self, **kwargs) -> None:
        obj_in = UpdateAdminStatisticSchema(**kwargs)
        return self._repository_admin_statistic.update(
            obj_id=1,
            obj_in=obj_in,
        )

