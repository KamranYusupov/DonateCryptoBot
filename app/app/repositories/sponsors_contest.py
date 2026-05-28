import uuid
from typing import List

from sqlalchemy import select, delete, update, func
from sqlalchemy.orm import selectinload

from app.models.contest import SponsorsContest, SponsorsContestPoint
from app.repositories.base.contest import RepositoryContestBase, RepositoryContestPointBase


class RepositorySponsorsContest(
    RepositoryContestBase[SponsorsContest]):
    pass


class RepositorySponsorsContestPoint(
    RepositoryContestPointBase[SponsorsContestPoint]
):
    pass
