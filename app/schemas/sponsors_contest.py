from uuid import UUID

from pydantic import BaseModel


class CreateContestPointSchema(BaseModel):
    user_id: int
    contest_id: UUID