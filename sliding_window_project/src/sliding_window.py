"""软件工程作业中的滑动窗口最大值实现。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Sequence


def _is_supported_integer(value: object) -> bool:
    """判断输入是否为整数，并排除布尔值。"""

    return isinstance(value, int) and not isinstance(value, bool)


def _validate_window_input_baseline(nums: Sequence[int], k: int) -> list[int]:
    """保留原始写法的输入校验版本，供基础单调队列实现对照使用。"""

    if isinstance(nums, (str, bytes)) or not isinstance(nums, Sequence):
        raise TypeError("nums 必须是非空整数序列。")

    values = list(nums)
    if not values:
        raise ValueError("nums 不能为空。")

    if not _is_supported_integer(k):
        raise TypeError("k 必须是整数。")

    if k <= 0:
        raise ValueError("k 必须大于 0。")

    if k > len(values):
        raise ValueError("k 不能大于 nums 的长度。")

    if any(not _is_supported_integer(item) for item in values):
        raise TypeError("nums 中的元素必须全部为整数。")

    return values


def validate_window_input(nums: Sequence[int], k: int) -> list[int]:
    """校验滑动窗口输入，并返回标准化后的列表副本。

    参数：
        nums：非空整数序列。
        k：窗口大小。
            本实验只接受普通 ``int``，``bool`` 和其他类型都不视为合法整数。

    返回：
        ``nums`` 的列表副本，便于后续求解器统一处理。

    异常：
        TypeError：当 ``nums`` 不是序列、``k`` 不是整数，或 ``nums``
            中存在非整数元素时抛出。
        ValueError：当 ``nums`` 为空、``k`` 不大于 0，或 ``k`` 大于
            ``len(nums)`` 时抛出。
    """

    if isinstance(nums, (str, bytes)) or not isinstance(nums, Sequence):
        raise TypeError("nums 必须是非空整数序列。")

    values = list(nums)
    if not values:
        raise ValueError("nums 不能为空。")

    # pylint: disable=unidiomatic-typecheck
    if type(k) is not int:
        raise TypeError("k 必须是整数。")

    if k <= 0:
        raise ValueError("k 必须大于 0。")

    if k > len(values):
        raise ValueError("k 不能大于 nums 的长度。")

    for item in values:
        if type(item) is not int:
            raise TypeError("nums 中的元素必须全部为整数。")
    # pylint: enable=unidiomatic-typecheck

    return values


class BaseWindowMaxSolver(ABC):
    """所有滑动窗口最大值策略的抽象基类。"""

    name = "base"

    @abstractmethod
    def solve(self, nums: Sequence[int], k: int) -> list[int]:
        """返回 ``nums`` 每个窗口对应的最大值。"""


class BruteForceWindowMaxSolver(BaseWindowMaxSolver):
    """时间复杂度为 O(nk) 的参考实现。"""

    name = "brute_force"

    def solve(self, nums: Sequence[int], k: int) -> list[int]:
        """直接扫描每个窗口并计算最大值。"""

        values = validate_window_input(nums, k)
        window_count = len(values) - k + 1
        return [max(values[index : index + k]) for index in range(window_count)]


class MonotonicQueueBaselineWindowMaxSolver(BaseWindowMaxSolver):
    """保留原始写法的单调队列基础实现。"""

    name = "monotonic_queue_baseline"

    def solve(self, nums: Sequence[int], k: int) -> list[int]:
        """维护一个单调递减的候选下标双端队列。"""

        values = _validate_window_input_baseline(nums, k)
        candidate_indices: deque[int] = deque()
        maxima: list[int] = []

        for right_index, current_value in enumerate(values):
            left_boundary = right_index - k + 1

            while candidate_indices and candidate_indices[0] < left_boundary:
                candidate_indices.popleft()

            # 保留最新的相等值，可以避免队列中残留失效的重复候选项。
            while candidate_indices and values[candidate_indices[-1]] <= current_value:
                candidate_indices.pop()

            candidate_indices.append(right_index)

            if right_index >= k - 1:
                maxima.append(values[candidate_indices[0]])

        return maxima


class MonotonicQueueWindowMaxSolver(BaseWindowMaxSolver):
    """时间复杂度为 O(n) 的小幅优化实现。"""

    name = "monotonic_queue"

    def solve(self, nums: Sequence[int], k: int) -> list[int]:
        """绑定常用方法并减少循环内的常数开销。"""

        values = validate_window_input(nums, k)
        candidate_indices: deque[int] = deque()
        maxima: list[int] = []

        queue_append = candidate_indices.append
        queue_pop = candidate_indices.pop
        queue_popleft = candidate_indices.popleft
        maxima_append = maxima.append
        first_full_window_index = k - 1

        for right_index, current_value in enumerate(values):
            left_boundary = right_index - k + 1

            if candidate_indices and candidate_indices[0] < left_boundary:
                queue_popleft()

            while candidate_indices and values[candidate_indices[-1]] <= current_value:
                queue_pop()

            queue_append(right_index)

            if right_index >= first_full_window_index:
                maxima_append(values[candidate_indices[0]])

        return maxima


def max_sliding_window(
    nums: Sequence[int],
    k: int,
    solver: BaseWindowMaxSolver | None = None,
) -> list[int]:
    """按指定策略返回滑动窗口最大值结果。

    参数：
        nums：输入整数序列。
        k：窗口大小。
        solver：可选策略对象；若省略，则默认使用单调队列实现。

    返回：
        由每个窗口最大值组成的列表。

    异常：
        TypeError：当 ``solver`` 不提供可调用的 ``solve`` 方法时抛出。
    """

    active_solver = solver or MonotonicQueueWindowMaxSolver()
    solve_method = getattr(active_solver, "solve", None)
    if not callable(solve_method):
        raise TypeError("solver 必须提供可调用的 solve(nums, k) 方法。")
    return active_solver.solve(nums, k)
