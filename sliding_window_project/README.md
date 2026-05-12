# 滑动窗口最大值项目

本项目围绕“滑动窗口最大值”题目构建了一个完整的软件工程实验样例。项目不仅包含两种算法实现，还补充了单元测试、静态检查、性能分析、覆盖率统计以及可直接编译的 `LaTeX` 报告模板，便于将代码与实验结果一起提交。

## 题目说明

给定整数序列 `nums` 和窗口大小 `k`，窗口从左向右每次移动一位，要求返回每个窗口中的最大值。

示例：

- 输入：`nums = [1, 3, -1, -3, 5, 3, 6, 7]`，`k = 3`
- 输出：`[3, 3, 5, 5, 6, 7]`

## 项目结构

```text
sliding_window_project/
├── src/
│   ├── __init__.py
│   └── sliding_window.py
├── tests/
│   ├── __init__.py
│   └── test_sliding_window.py
├── scripts/
│   ├── run_demo.py
│   ├── run_profile.py
│   └── generate_reports.py
├── reports/
│   └── .gitkeep
├── report.tex
├── requirements.txt
├── pyproject.toml
└── README.md
```

## 安装依赖

执行以下命令安装需要的工具：

```bash
python3 -m pip install -r requirements.txt
```

如果本地环境使用的是 `python` 而不是 `python3`，可以将下列命令中的
`python3` 替换为 `python`。

## 运行示例

```bash
python3 scripts/run_demo.py
```

## 运行单元测试

```bash
python3 -m unittest discover -s tests
```

## 运行覆盖率统计

```bash
python3 -m coverage run -m unittest discover -s tests
python3 -m coverage report -m
```

覆盖率配置聚焦于 `src` 包，目标是不低于 90% 的语句覆盖率。

## 运行 Pylint 静态检查

```bash
python3 -m pylint src tests scripts
```

`pyproject.toml` 中将 `max-line-length` 设为 100，并仅关闭
`too-few-public-methods` 这一项，因为求解器策略类本来就只暴露很少的公共接口。

## 运行性能分析脚本

```bash
python3 scripts/run_profile.py
```

该脚本会将结果写入 `reports/profile_report.txt`，并比较：

- `BruteForceWindowMaxSolver`：时间复杂度为 `O(nk)` 的基线实现
- `MonotonicQueueWindowMaxSolver`：时间复杂度为 `O(n)` 的优化实现

## 一键生成全部报告

```bash
python3 scripts/generate_reports.py
```

该脚本会生成以下文件：

- `reports/unittest_report.txt`
- `reports/coverage_report.txt`
- `reports/pylint_report.txt`
- `reports/profile_report.txt`

## 编译 LaTeX 报告

```bash
xelatex report.tex
```

项目中还包含本地 `.venv/` 目录，它仅用于我在当前环境中生成和验证报告文件，
提交最终作业压缩包时可以不包含该目录。

## 算法设计

项目通过统一接口封装了两种可互换的求解策略：

- `BruteForceWindowMaxSolver`：对每个窗口重新调用 `max`，时间复杂度为
  `O(nk)`，除结果列表外的额外空间复杂度为 `O(1)`。
- `MonotonicQueueWindowMaxSolver`：维护一个单调递减的候选下标双端队列，
  每个元素最多入队和出队一次，因此时间复杂度为 `O(n)`，额外空间复杂度为 `O(k)`。

对外函数 `max_sliding_window(nums, k, solver=None)` 默认使用单调队列实现，
同时允许传入其他求解器对象，方便后续扩展。

## 设计原则

本项目体现了作业要求中的几个软件工程目标：

- SRP：输入校验、算法策略、性能分析和测试代码分别放在独立模块或脚本中。
- OCP：新增算法时，只需要再实现一个带有 `solve(nums, k)` 方法的求解器，
  不需要改动已有对外接口。
- 防御式编程：`validate_window_input` 会对非法类型和越界参数主动抛出
  `TypeError` 或 `ValueError`。

## 扩展方向

在不改动公共接口的前提下，后续还可以继续扩展：

- 基于堆的滑动窗口求解器
- 基于分块思想的求解器
- 滑动窗口最小值版本
- 同时返回最大值下标的变体
