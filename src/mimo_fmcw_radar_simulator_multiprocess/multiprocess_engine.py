"""多进程执行的小型封装。

仿真最耗时的部分是逐 chirp、逐通道、逐散射点合成复数信号。
这里不把并行逻辑写进信号模型内部，而是提供三个通用工具：
默认 worker 数、索引切块、并行 map。这样主流程可以保持清楚。

这个模块只负责“怎么把任务分出去”，不理解雷达物理含义。
这样可以保证并行策略和业务计算解耦：未来即使换成线程池、joblib、
Ray 或批处理队列，也不用重写信号合成公式。
"""

from __future__ import annotations

import math
import os
from concurrent.futures import ProcessPoolExecutor
from typing import Callable, Iterable, TypeVar

T = TypeVar("T")
R = TypeVar("R")


def default_worker_count() -> int:
    """给出保守的默认进程数。

    使用一半 CPU 核心是为了避免把桌面机器完全打满；雷达仿真通常还会
    占用大量内存带宽，worker 过多未必更快。
    """

    cpu_total = os.cpu_count() or 1
    return max(1, cpu_total // 2)


def split_indices(total: int, parts: int) -> list[tuple[int, int]]:
    """把 `[0, total)` 切成若干连续区间。

    在本项目中主要用于把 `num_chirps` 切给多个进程。连续切分的好处是
    每个进程写回 RDC 时可以直接落到 `start:stop` 的慢时间片段。
    """

    if total <= 0:
        return []
    chunk = math.ceil(total / max(parts, 1))
    ranges = []
    for start in range(0, total, chunk):
        stop = min(total, start + chunk)
        ranges.append((start, stop))
    return ranges


def parallel_map(function: Callable[[T], R], tasks: Iterable[T], max_workers: int) -> list[R]:
    """根据 worker 数选择串行或多进程执行。

    `max_workers <= 1` 时保持串行，便于调试和复现异常栈；多进程时使用
    `ProcessPoolExecutor`，避开 Python GIL 对 CPU 密集型 numpy 外层循环的影响。
    """

    if max_workers <= 1:
        return [function(task) for task in tasks]
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(function, tasks))
