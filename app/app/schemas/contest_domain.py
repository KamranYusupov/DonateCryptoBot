# app/schemas/contest_domain.py

from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class ContestUserItemSchema(BaseModel):
    """Схема для входящих агрегированных данных из БД"""

    user_id: int
    points_count: int


class ContestUserResultSchema(BaseModel):
    """Статистика конкретного пользователя в конкурсе"""

    points_count: int
    user_str: str
    place: int


class ContestTop10ItemSchema(BaseModel):
    """Элемент рейтинга ТОП-10"""

    user_str: str
    points_count: int


class ContestCalculationResultSchema(BaseModel):
    """Результат работы калькулятора"""

    total_points: int
    results: Dict[int, ContestUserResultSchema] = Field(default_factory=dict)
    top_10_rating: List[ContestTop10ItemSchema] = Field(default_factory=list)


class ContestUpdateSchema(BaseModel):
    """Схема для обновления модели конкурса в БД"""

    prize_fund: Optional[int] = None
    top_10_rating: Optional[List[ContestTop10ItemSchema]] = None
    results: Optional[Dict[int, ContestUserResultSchema]] = None
