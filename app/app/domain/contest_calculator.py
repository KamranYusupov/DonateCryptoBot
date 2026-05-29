from typing import List, Dict

from app.schemas.contest_domain import (
    ContestUserItemSchema,
    ContestUserResultSchema,
    ContestTop10ItemSchema,
    ContestCalculationResultSchema
)



class ContestResultCalculator:
    """Вычислитель результатов конкурсов"""

    @staticmethod
    def calculate(
            grouped_user_points: List[ContestUserItemSchema],
            user_str_map: Dict[int, str],
    ) -> ContestCalculationResultSchema:

        results: Dict[int, ContestUserResultSchema] = {}
        top_10_rating: List[ContestTop10ItemSchema] = []
        total_points = 0
        place = 1

        for item in grouped_user_points:
            if not (user_str := user_str_map.get(item.user_id)):
                continue

            total_points += item.points_count

            results[item.user_id] = ContestUserResultSchema(
                points_count=item.points_count,
                user_str=user_str,
                place=place
            )

            if place <= 10:
                top_10_item = ContestTop10ItemSchema(
                    user_str=user_str,
                    points_count=item.points_count,
                )
                top_10_rating.append(top_10_item)

            place += 1

        return ContestCalculationResultSchema(
            results=results,
            top_10_rating=top_10_rating,
            total_points=total_points,
        )