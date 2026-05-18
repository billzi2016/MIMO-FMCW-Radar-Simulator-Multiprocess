from __future__ import annotations

import math
import os
from concurrent.futures import ProcessPoolExecutor
from typing import Callable, Iterable, TypeVar

T = TypeVar("T")
R = TypeVar("R")


def default_worker_count() -> int:
    cpu_total = os.cpu_count() or 1
    return max(1, cpu_total // 2)


def split_indices(total: int, parts: int) -> list[tuple[int, int]]:
    if total <= 0:
        return []
    chunk = math.ceil(total / max(parts, 1))
    ranges = []
    for start in range(0, total, chunk):
        stop = min(total, start + chunk)
        ranges.append((start, stop))
    return ranges


def parallel_map(function: Callable[[T], R], tasks: Iterable[T], max_workers: int) -> list[R]:
    if max_workers <= 1:
        return [function(task) for task in tasks]
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(function, tasks))
