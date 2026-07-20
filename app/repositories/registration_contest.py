import uuid
from typing import List

from sqlalchemy import select, delete, update, func
from sqlalchemy.orm import selectinload

from app.models.contest import RegistrationContest, RegistrationContestPoint
from app.repositories.base.contest import RepositoryContestBase, RepositoryContestPointBase


class RepositoryRegistrationContest(
    RepositoryContestBase[RegistrationContest]):
    pass


class RepositoryRegistrationContestPoint(
    RepositoryContestPointBase[RegistrationContestPoint]
):
    pass
