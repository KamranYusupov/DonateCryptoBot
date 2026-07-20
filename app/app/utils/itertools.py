from itertools import islice
from typing import Iterable, TypeVar, Tuple

T = TypeVar('T')


def batched(iterable: Iterable[T], n: int) -> Iterable[Tuple[T, ...]]:
    """
    Точный аналог itertools.batched для Python 3.11 и ниже.
    Лениво разбивает любой Iterable (включая генераторы) на кортежи длины n.
    """
    if n < 1:
        raise ValueError('n must be at least one')

    it = iter(iterable)
    while batch := tuple(islice(it, n)):
        yield batch