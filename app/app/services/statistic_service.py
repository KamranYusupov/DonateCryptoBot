from typing import Any

from sqlalchemy.util import await_only

from app.repositories.matrix_statistic import RepositoryMatrixStatistic
from app.repositories.admin_statistic import RepositoryAdminStatistic
from app.repositories.registration_statistic import RepositoryRegistrationStatistic
from app.schemas.statistic import AdminStatisticSchema, UpdateAdminStatisticSchema


class StatisticService:
    def __init__(
            self,
            repository_admin_statistic: RepositoryAdminStatistic,
            repository_matrix_statistic: RepositoryMatrixStatistic,
            repository_registration_statistic: RepositoryRegistrationStatistic,
    ):
        self._repository_admin_statistic = repository_admin_statistic
        self._repository_matrix_statistic = repository_matrix_statistic
        self._repository_registration_statistic = repository_registration_statistic

    async def get_admin_statistic(self) -> AdminStatisticSchema:
        admin_statistic = await self._repository_admin_statistic.get()
        return AdminStatisticSchema.model_validate(admin_statistic)

    async def update_admin_statistic(self, **kwargs) -> None:
        obj_in = UpdateAdminStatisticSchema(**kwargs)
        return await self._repository_admin_statistic.update(
            obj_id=1,
            obj_in=obj_in,
        )

    async def get_matrix_activations_count(self) -> int:
        return await self._repository_matrix_statistic.get_activation_count()

    async def increment_matrix_activations_count(self) -> int:
        return await (
            self._repository_matrix_statistic
            .increment_activations_count()
        )

    async def get_registrations_count(self) -> int:
        return await self._repository_registration_statistic.get_count()

    async def increment_registrations_count(self) -> int:
        return await (
            self._repository_registration_statistic
            .increment_count()
        )


