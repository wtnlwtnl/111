"""为两种滑动窗口求解器生成耗时与 cProfile 报告。"""

from __future__ import annotations

import cProfile
import io
import pstats
import random
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.sliding_window import (  # pylint: disable=wrong-import-position
    BaseWindowMaxSolver,
    BruteForceWindowMaxSolver,
    MonotonicQueueWindowMaxSolver,
)

REPORT_PATH = PROJECT_ROOT / "reports" / "profile_report.txt"


def build_dataset(size: int, seed: int) -> list[int]:
    """构造可复现实验用的确定性伪随机数据。"""

    generator = random.Random(seed)
    return [generator.randint(-10_000, 10_000) for _ in range(size)]


def benchmark_solver(
    solver: BaseWindowMaxSolver,
    nums: list[int],
    k: int,
    repeat: int,
) -> tuple[list[int], float]:
    """统计单个求解器重复执行后的总耗时。"""

    start_time = time.perf_counter()
    last_result: list[int] = []
    for _ in range(repeat):
        last_result = solver.solve(nums, k)
    elapsed = time.perf_counter() - start_time
    return last_result, elapsed


def collect_profile_stats(
    solver: BaseWindowMaxSolver,
    nums: list[int],
    k: int,
    repeat: int,
) -> tuple[list[int], str]:
    """收集单个求解器的可读 cProfile 统计信息。"""

    profiler = cProfile.Profile()
    profiler.enable()
    last_result: list[int] = []
    for _ in range(repeat):
        last_result = solver.solve(nums, k)
    profiler.disable()

    output_buffer = io.StringIO()
    stats = pstats.Stats(profiler, stream=output_buffer).sort_stats(pstats.SortKey.CUMULATIVE)
    stats.print_stats(10)
    return last_result, translate_profile_stats(output_buffer.getvalue())


def translate_profile_stats(profile_text: str) -> str:
    """将 cProfile 文本中的常见英文说明替换为中文。"""

    translated = profile_text
    translated = translated.replace(
        "List reduced from 11 to 10 due to restriction <10>",
        "统计项已从 11 项缩减为 10 项，原因是限制为 <10>",
    )
    translated = translated.replace(
        "List reduced from 14 to 10 due to restriction <10>",
        "统计项已从 14 项缩减为 10 项，原因是限制为 <10>",
    )
    translated = translated.replace("Ordered by: cumulative time", "排序依据：累计时间")
    translated = translated.replace(
        "ncalls  tottime  percall  cumtime  percall filename:lineno(function)",
        "调用次数  本体耗时  单次耗时  累计耗时  单次累计  文件:行号(函数)",
    )
    translated = translated.replace(
        "method 'disable' of '_lsprof.Profiler' objects",
        "_lsprof.Profiler 对象的 disable 方法",
    )
    translated = translated.replace("{built-in method builtins.max}", "{内建方法 builtins.max}")
    translated = translated.replace("{built-in method builtins.any}", "{内建方法 builtins.any}")
    translated = translated.replace(
        "{built-in method builtins.isinstance}",
        "{内建方法 builtins.isinstance}",
    )
    translated = translated.replace("{built-in method builtins.len}", "{内建方法 builtins.len}")
    translated = translated.replace(
        "{method 'append' of 'collections.deque' objects}",
        "{collections.deque 对象的 append 方法}",
    )
    translated = translated.replace(
        "{method 'pop' of 'collections.deque' objects}",
        "{collections.deque 对象的 pop 方法}",
    )
    translated = translated.replace(
        "{method 'popleft' of 'collections.deque' objects}",
        "{collections.deque 对象的 popleft 方法}",
    )
    translated = translated.replace(
        "{method 'append' of 'list' objects}",
        "{list 对象的 append 方法}",
    )
    translated = translated.replace(
        "{built-in method _abc._abc_instancecheck}",
        "{内建方法 _abc._abc_instancecheck}",
    )
    translated = translated.replace(
        "<frozen abc>:117(__instancecheck__)",
        "<冻结模块 abc>:117(__instancecheck__)",
    )
    translated = translated.replace("function calls in", "次函数调用，耗时")
    translated = translated.replace("seconds", "秒")
    translated = translated.replace("second", "秒")
    return translated


def measure_solver(
    solver: BaseWindowMaxSolver,
    nums: list[int],
    k: int,
    repeat: int,
) -> tuple[list[int], float, str]:
    """返回单个求解器的结果、耗时和 cProfile 文本。"""

    result, elapsed = benchmark_solver(solver, nums, k, repeat)
    _, profile_text = collect_profile_stats(solver, nums, k, repeat)
    return result, elapsed, profile_text


def format_experiment(
    label: str,
    nums: list[int],
    k: int,
    repeat: int,
) -> str:
    """运行一次实验，并格式化耗时与性能分析结果。"""

    brute_force_result, brute_force_elapsed, brute_force_profile = measure_solver(
        BruteForceWindowMaxSolver(),
        nums,
        k,
        repeat,
    )
    monotonic_result, monotonic_elapsed, monotonic_profile = measure_solver(
        MonotonicQueueWindowMaxSolver(),
        nums,
        k,
        repeat,
    )
    if brute_force_result != monotonic_result:
        raise AssertionError("性能分析过程中，两种求解器的输出结果不一致。")

    brute_force_average = brute_force_elapsed / repeat
    monotonic_average = monotonic_elapsed / repeat
    speedup_ratio = brute_force_elapsed / monotonic_elapsed

    lines = [
        f"=== {label} ===",
        f"数据规模 n = {len(nums)}，窗口大小 k = {k}，重复次数 = {repeat}",
        f"暴力算法总耗时：{brute_force_elapsed:.6f} 秒",
        f"暴力算法平均耗时：{brute_force_average:.6f} 秒",
        f"单调队列总耗时：{monotonic_elapsed:.6f} 秒",
        f"单调队列平均耗时：{monotonic_average:.6f} 秒",
        f"加速比：{speedup_ratio:.2f} 倍",
        "",
        "--- cProfile：暴力算法 ---",
        brute_force_profile.strip(),
        "",
        "--- cProfile：单调队列算法 ---",
        monotonic_profile.strip(),
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    """生成完整性能分析报告并输出到终端。"""

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    small_dataset = build_dataset(size=20, seed=2026)
    large_dataset = build_dataset(size=12_000, seed=2027)

    report_sections = [
        "滑动窗口最大值性能分析报告",
        "分析环境：Python cProfile + time.perf_counter",
        "",
        format_experiment(
            label="小规模正确性实验",
            nums=small_dataset,
            k=4,
            repeat=10,
        ),
        format_experiment(
            label="大规模性能对比实验",
            nums=large_dataset,
            k=128,
            repeat=10,
        ),
        "结论：",
        (
            "单调队列算法通过维护 O(k) 的候选集合，避免了对每个完整窗口进行重复扫描，"
            "因此在大规模数据集上能够稳定优于暴力算法。"
        ),
    ]
    report_content = "\n".join(report_sections) + "\n"
    REPORT_PATH.write_text(report_content, encoding="utf-8")
    print(report_content)


if __name__ == "__main__":
    main()
