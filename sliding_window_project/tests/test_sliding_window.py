"""滑动窗口最大值实现的单元测试。"""

# pylint: disable=too-many-public-methods

from __future__ import annotations

import unittest

from src.sliding_window import (
    BruteForceWindowMaxSolver,
    MonotonicQueueWindowMaxSolver,
    max_sliding_window,
    validate_window_input,
)


class SlidingWindowTestCase(unittest.TestCase):
    """测试正常输入、边界输入和异常处理。"""

    def setUp(self) -> None:
        """创建各测试方法共用的求解器实例。"""

        self.brute_force_solver = BruteForceWindowMaxSolver()
        self.monotonic_solver = MonotonicQueueWindowMaxSolver()

    def assert_both_solvers_equal(
        self,
        nums: list[int],
        k: int,
        expected: list[int],
    ) -> None:
        """验证两个求解器都能得到相同的期望结果。"""

        self.assertEqual(self.brute_force_solver.solve(nums, k), expected)
        self.assertEqual(self.monotonic_solver.solve(nums, k), expected)

    def test_problem_example(self) -> None:
        """题目给出的经典样例应返回已知结果。"""

        nums = [1, 3, -1, -3, 5, 3, 6, 7]
        self.assert_both_solvers_equal(nums, 3, [3, 3, 5, 5, 6, 7])

    def test_window_size_one(self) -> None:
        """当窗口大小为 1 时，结果应与原序列一致。"""

        self.assert_both_solvers_equal([4, 2, 5], 1, [4, 2, 5])

    def test_window_size_equals_sequence_length(self) -> None:
        """当窗口覆盖整个序列时，应只返回一个最大值。"""

        self.assert_both_solvers_equal([4, 2, 5], 3, [5])

    def test_increasing_sequence(self) -> None:
        """递增序列用于验证单调队列的队尾更新逻辑。"""

        self.assert_both_solvers_equal([1, 2, 3, 4], 2, [2, 3, 4])

    def test_decreasing_sequence(self) -> None:
        """递减序列用于验证队首候选项保持有效。"""

        self.assert_both_solvers_equal([4, 3, 2, 1], 2, [4, 3, 2])

    def test_duplicate_values(self) -> None:
        """重复元素不应影响最大值跟踪。"""

        self.assert_both_solvers_equal([2, 2, 2], 2, [2, 2])

    def test_negative_values(self) -> None:
        """负数输入也应得到正确结果。"""

        self.assert_both_solvers_equal([-4, -2, -5], 2, [-2, -2])

    def test_single_element_sequence(self) -> None:
        """最小合法输入也应返回正确结果。"""

        self.assert_both_solvers_equal([9], 1, [9])

    def test_default_entry_point_uses_monotonic_solver(self) -> None:
        """默认入口函数应使用优化后的单调队列实现。"""

        result = max_sliding_window([8, 1, 6, 4], 2)
        self.assertEqual(result, [8, 6, 6])

    def test_custom_solver_matches_reference(self) -> None:
        """多组数据下两种求解器应保持结果一致。"""

        cases = [
            ([9, 7, 2, 4, 6, 8], 3),
            ([5, 5, 5, 5], 2),
            ([-1, -3, -2, -7, -6], 2),
            ([10, 3, 12, 4, 5, 8, 6], 4),
        ]

        for nums, k in cases:
            with self.subTest(nums=nums, k=k):
                expected = self.brute_force_solver.solve(nums, k)
                actual = max_sliding_window(nums, k, solver=self.monotonic_solver)
                self.assertEqual(actual, expected)

    def test_validate_window_input_returns_list_copy(self) -> None:
        """校验函数应将元组等输入标准化为列表。"""

        self.assertEqual(validate_window_input((1, 2, 3), 2), [1, 2, 3])

    def test_empty_sequence_raises_value_error(self) -> None:
        """空序列应在算法执行前被拒绝。"""

        with self.assertRaises(ValueError):
            max_sliding_window([], 1)

    def test_zero_window_raises_value_error(self) -> None:
        """窗口大小为 0 属于非法输入。"""

        with self.assertRaises(ValueError):
            max_sliding_window([1, 2], 0)

    def test_negative_window_raises_value_error(self) -> None:
        """负窗口大小属于非法输入。"""

        with self.assertRaises(ValueError):
            max_sliding_window([1, 2], -1)

    def test_window_larger_than_sequence_raises_value_error(self) -> None:
        """窗口大小不能超过输入序列长度。"""

        with self.assertRaises(ValueError):
            max_sliding_window([1, 2], 3)

    def test_non_integer_window_raises_type_error(self) -> None:
        """接口应拒绝非整数窗口大小。"""

        with self.assertRaises(TypeError):
            max_sliding_window([1, 2, 3], 1.5)

    def test_non_integer_element_raises_type_error(self) -> None:
        """输入序列中的元素必须全部为整数。"""

        with self.assertRaises(TypeError):
            max_sliding_window([1, "2", 3], 2)

    def test_non_sequence_input_raises_type_error(self) -> None:
        """输入必须是具体序列，不能是任意对象。"""

        with self.assertRaises(TypeError):
            max_sliding_window(42, 1)

    def test_string_input_raises_type_error(self) -> None:
        """虽然字符串属于序列，但本题中也应视为非法输入。"""

        with self.assertRaises(TypeError):
            max_sliding_window("1234", 2)

    def test_invalid_solver_object_raises_type_error(self) -> None:
        """当求解器对象格式错误时，入口函数应快速失败。"""

        with self.assertRaises(TypeError):
            max_sliding_window([1, 2, 3], 2, solver=object())


if __name__ == "__main__":
    unittest.main()
