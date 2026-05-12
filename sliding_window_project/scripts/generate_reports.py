"""一键生成 unittest、coverage、Pylint 和性能分析报告。"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"


@dataclass
class CommandResult:
    """保存一次命令执行后的结果。"""

    exit_code: int
    stdout_text: str
    stderr_text: str
    command_text: str

    def combined_output(self) -> str:
        """返回标准输出与标准错误拼接后的文本。"""

        return "\n".join(
            text for text in [self.stdout_text, self.stderr_text] if text
        )


def run_command(
    arguments: list[str],
    extra_env: dict[str, str] | None = None,
) -> CommandResult:
    """运行命令，并返回结构化结果。"""

    environment = os.environ.copy()
    if extra_env is not None:
        environment.update(extra_env)

    completed = subprocess.run(
        arguments,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )
    return CommandResult(
        exit_code=completed.returncode,
        stdout_text=completed.stdout.rstrip(),
        stderr_text=completed.stderr.rstrip(),
        command_text=" ".join(arguments),
    )


def write_report(report_name: str, content: str) -> None:
    """将文本报告写入 reports 目录。"""

    report_path = REPORTS_DIR / report_name
    report_path.write_text(content + "\n", encoding="utf-8")


def translate_display_text(text: str) -> str:
    """将可稳定识别的工具输出提示替换为中文。"""

    translated = text
    translated = re.sub(
        r"Ran (\d+) tests? in ([0-9.]+)s",
        r"共运行 \1 个测试，用时 \2 秒",
        translated,
    )
    translated = re.sub(r"^OK$", "通过", translated, flags=re.MULTILINE)
    translated = re.sub(r"^FAILED.*$", "失败", translated, flags=re.MULTILINE)
    translated = re.sub(
        r"Your code has been rated at ([0-9.]+/10)",
        r"代码评分为 \1",
        translated,
    )
    translated = translated.replace(
        "Name                    Stmts   Miss  Cover   Missing",
        "文件                    语句数  未覆盖  覆盖率  未覆盖位置",
    )
    translated = translated.replace("TOTAL", "总计")
    return translated


def build_report(
    title: str,
    result: CommandResult,
    summary_lines: list[str],
) -> str:
    """拼装中文报告正文。"""

    parts = [
        title,
        "=" * len(title),
        f"运行命令：{result.command_text}",
        f"退出码：{result.exit_code}",
        "",
        "结果摘要：",
        *[f"- {line}" for line in summary_lines],
        "",
        "原始标准输出：",
        translate_display_text(result.stdout_text) or "（无）",
        "",
        "原始标准错误：",
        translate_display_text(result.stderr_text) or "（无）",
    ]
    return "\n".join(parts)


def summarize_unittest(output_text: str, exit_code: int) -> list[str]:
    """提取单元测试的关键信息。"""

    match = re.search(r"Ran (\d+) tests? in ([0-9.]+)s", output_text)
    if not match:
        return ["未能从原始输出中提取测试数量与耗时。"]

    case_count = match.group(1)
    elapsed = match.group(2)
    status = "全部通过" if "OK" in output_text and exit_code == 0 else "存在失败"
    return [f"共运行 {case_count} 个测试，用时 {elapsed} 秒。", f"测试结果：{status}。"]


def summarize_coverage(report_text: str) -> list[str]:
    """提取覆盖率报告的关键信息。"""

    total_match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+%)", report_text)
    source_matches = re.findall(
        r"^(src/[^\s]+)\s+\d+\s+\d+\s+(\d+%)",
        report_text,
        flags=re.MULTILINE,
    )
    summary = []
    if total_match:
        summary.append(f"总体语句覆盖率：{total_match.group(1)}。")
    for path, ratio in source_matches:
        summary.append(f"{path} 的覆盖率为 {ratio}。")
    if not summary:
        summary.append("未能从原始输出中提取覆盖率结果。")
    return summary


def summarize_pylint(output_text: str, exit_code: int) -> list[str]:
    """提取 Pylint 的评分结果。"""

    score_match = re.search(r"rated at ([0-9.]+/10)", output_text)
    if not score_match:
        return ["未能从原始输出中提取 Pylint 评分。"]

    passed = "是" if exit_code == 0 else "否"
    return [f"Pylint 评分为 {score_match.group(1)}。", f"检查是否通过：{passed}。"]


def summarize_profile(output_text: str) -> list[str]:
    """提取性能分析报告中的关键指标。"""

    speed_match = re.search(r"加速比：([0-9.]+) 倍", output_text)
    brute_match = re.search(r"暴力算法平均耗时：([0-9.]+) 秒", output_text)
    mono_match = re.search(r"单调队列平均耗时：([0-9.]+) 秒", output_text)

    summary = []
    if brute_match:
        summary.append(f"暴力算法平均耗时：{brute_match.group(1)} 秒。")
    if mono_match:
        summary.append(f"单调队列平均耗时：{mono_match.group(1)} 秒。")
    if speed_match:
        summary.append(
            f"单调队列相对暴力算法的加速比为 {speed_match.group(1)} 倍。"
        )
    if not summary:
        summary.append("未能从原始输出中提取关键性能指标。")
    return summary


def generate_unittest_report() -> int:
    """生成单元测试报告。"""

    result = run_command([sys.executable, "-m", "unittest", "discover", "-s", "tests"])
    write_report(
        "unittest_report.txt",
        build_report(
            title="单元测试报告",
            result=result,
            summary_lines=summarize_unittest(result.combined_output(), result.exit_code),
        ),
    )
    return result.exit_code


def generate_coverage_report() -> list[int]:
    """生成覆盖率执行报告和覆盖率统计报告。"""

    run_result = run_command(
        [sys.executable, "-m", "coverage", "run", "-m", "unittest", "discover", "-s", "tests"]
    )
    report_result = run_command([sys.executable, "-m", "coverage", "report", "-m"])
    content = "\n\n".join(
        [
            build_report(
                title="覆盖率执行报告",
                result=run_result,
                summary_lines=summarize_unittest(
                    run_result.combined_output(),
                    run_result.exit_code,
                ),
            ),
            build_report(
                title="覆盖率统计报告",
                result=report_result,
                summary_lines=summarize_coverage(report_result.stdout_text),
            ),
        ]
    )
    write_report("coverage_report.txt", content)
    return [run_result.exit_code, report_result.exit_code]


def generate_pylint_report() -> int:
    """生成 Pylint 静态检查报告。"""

    result = run_command(
        [sys.executable, "-m", "pylint", "src", "tests", "scripts"],
        extra_env={"PYLINTHOME": str(REPORTS_DIR / ".pylint_cache")},
    )
    write_report(
        "pylint_report.txt",
        build_report(
            title="Pylint 静态检查报告",
            result=result,
            summary_lines=summarize_pylint(result.combined_output(), result.exit_code),
        ),
    )
    return result.exit_code


def generate_profile_driver_report() -> int:
    """生成性能分析脚本的执行记录。"""

    result = run_command([sys.executable, "scripts/run_profile.py"])
    if result.stdout_text or result.stderr_text:
        write_report(
            "profile_driver_output.txt",
            build_report(
                title="性能分析脚本执行记录",
                result=result,
                summary_lines=summarize_profile(result.stdout_text),
            ),
        )
    return result.exit_code


def main() -> int:
    """生成全部实验报告，并返回汇总退出码。"""

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    exit_codes = [generate_unittest_report()]
    exit_codes.extend(generate_coverage_report())
    exit_codes.append(generate_pylint_report())
    exit_codes.append(generate_profile_driver_report())

    print("已在以下目录生成报告：", REPORTS_DIR)
    for report_path in sorted(REPORTS_DIR.iterdir()):
        print("-", report_path.name)

    return 0 if all(code == 0 for code in exit_codes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
