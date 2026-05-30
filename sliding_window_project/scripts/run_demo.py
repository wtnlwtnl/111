"""运行一个简短示例，展示两种滑动窗口策略的结果。"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.sliding_window import (  # pylint: disable=wrong-import-position
    BruteForceWindowMaxSolver,
    MonotonicQueueBaselineWindowMaxSolver,
    MonotonicQueueWindowMaxSolver,
    max_sliding_window,
)


def main() -> None:
    """执行示例并打印两种算法的对比结果。"""

    nums = [1, 3, -1, -3, 5, 3, 6, 7]
    window_size = 3

    brute_force_result = max_sliding_window(
        nums,
        window_size,
        solver=BruteForceWindowMaxSolver(),
    )
    baseline_result = max_sliding_window(
        nums,
        window_size,
        solver=MonotonicQueueBaselineWindowMaxSolver(),
    )
    monotonic_result = max_sliding_window(
        nums,
        window_size,
        solver=MonotonicQueueWindowMaxSolver(),
    )

    print("输入序列：", nums)
    print("窗口大小：", window_size)
    print("暴力算法结果：", brute_force_result)
    print("基础单调队列结果：", baseline_result)
    print("单调队列结果：", monotonic_result)
    print("默认接口结果：", max_sliding_window(nums, window_size))
    print("三种算法结果是否一致：", brute_force_result == baseline_result == monotonic_result)


if __name__ == "__main__":
    main()
