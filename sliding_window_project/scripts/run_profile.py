"""为两种滑动窗口求解器生成耗时与 cProfile 报告。"""

from __future__ import annotations

import cProfile
import io
import pstats
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.sliding_window import (  # pylint: disable=wrong-import-position
    BaseWindowMaxSolver,
    BruteForceWindowMaxSolver,
    MonotonicQueueBaselineWindowMaxSolver,
    MonotonicQueueWindowMaxSolver,
)

REPORT_PATH = PROJECT_ROOT / "reports" / "profile_report.txt"


@dataclass
class SolverMeasurement:
    """记录单个求解器的一次测量结果。"""

    result: list[int]
    elapsed: float
    profile_text: str


@dataclass
class ExperimentMeasurements:
    """记录一次实验中三个求解器的测量结果。"""

    brute_force: SolverMeasurement
    baseline: SolverMeasurement
    optimized: SolverMeasurement


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
) -> SolverMeasurement:
    """返回单个求解器的结果、耗时和 cProfile 文本。"""

    result, elapsed = benchmark_solver(solver, nums, k, repeat)
    _, profile_text = collect_profile_stats(solver, nums, k, repeat)
    return SolverMeasurement(result=result, elapsed=elapsed, profile_text=profile_text)


def collect_experiment_measurements(
    nums: list[int],
    k: int,
    repeat: int,
) -> ExperimentMeasurements:
    """收集一次实验中的三组求解器结果。"""

    brute_force = measure_solver(BruteForceWindowMaxSolver(), nums, k, repeat)
    baseline = measure_solver(MonotonicQueueBaselineWindowMaxSolver(), nums, k, repeat)
    optimized = measure_solver(MonotonicQueueWindowMaxSolver(), nums, k, repeat)

    if not brute_force.result == baseline.result == optimized.result:
        raise AssertionError("性能分析过程中，三种求解器的输出结果不一致。")

    return ExperimentMeasurements(
        brute_force=brute_force,
        baseline=baseline,
        optimized=optimized,
    )


def format_experiment(
    label: str,
    nums: list[int],
    k: int,
    repeat: int,
) -> str:
    """运行一次实验，并格式化耗时与性能分析结果。"""

    measurements = collect_experiment_measurements(nums, k, repeat)

    lines = [
        f"=== {label} ===",
        f"数据规模 n = {len(nums)}，窗口大小 k = {k}，重复次数 = {repeat}",
        f"暴力算法总耗时：{measurements.brute_force.elapsed:.6f} 秒",
        f"暴力算法平均耗时：{measurements.brute_force.elapsed / repeat:.6f} 秒",
        f"基础单调队列总耗时：{measurements.baseline.elapsed:.6f} 秒",
        f"基础单调队列平均耗时：{measurements.baseline.elapsed / repeat:.6f} 秒",
        f"单调队列总耗时：{measurements.optimized.elapsed:.6f} 秒",
        f"单调队列平均耗时：{measurements.optimized.elapsed / repeat:.6f} 秒",
        (
            "基础单调队列相对暴力算法的加速比："
            f"{measurements.brute_force.elapsed / measurements.baseline.elapsed:.2f} 倍"
        ),
        (
            "小幅优化后单调队列相对暴力算法的加速比："
            f"{measurements.brute_force.elapsed / measurements.optimized.elapsed:.2f} 倍"
        ),
        (
            "小幅优化后单调队列相对基础单调队列的加速比："
            f"{measurements.baseline.elapsed / measurements.optimized.elapsed:.2f} 倍"
        ),
        "",
        "--- cProfile：暴力算法 ---",
        measurements.brute_force.profile_text.strip(),
        "",
        "--- cProfile：基础单调队列算法 ---",
        measurements.baseline.profile_text.strip(),
        "",
        "--- cProfile：单调队列算法 ---",
        measurements.optimized.profile_text.strip(),
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
            "基础单调队列版本通过避免对每个窗口重复扫描，已经显著优于暴力算法；"
            "优化版本进一步通过更直接的输入校验和少量循环常数优化，"
            "在不改变 O(n) 复杂度的前提下获得了小幅提升。"
        ),
    ]
    report_content = "\n".join(report_sections) + "\n"
    REPORT_PATH.write_text(report_content, encoding="utf-8")
    print(report_content)


if __name__ == "__main__":
    main()
