from typing import List

from pydantic import BaseModel


class MathCaptchaResult(BaseModel):
    first_digit: int
    second_digit: int
    options: List[int]
    answer: int