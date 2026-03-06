---
globs: ["**/*.py", "tests/**/*.py"]
alwaysApply: false
description: "Testing policy: one-to-one function-test mapping and uv-based execution gate"
---

# Testing Rules

## Function-Test Mapping

- 新增函数：必须新增对应测试。
- 修改函数：必须更新对应测试，确保行为变更被覆盖。
- 禁止“只改实现不改测试”或“只补 happy path”。

## Execution Gate

- 所有测试执行必须通过 `uv`：
  - `uv run pytest`
- 提交前最低门槛：
  - 默认门禁 `uv run pytest` 通过（`pyproject.toml` 中默认排除 `e2e`）。
- 分层标记必须显式维护：
  - `unit`：确定性本地逻辑
  - `integration`：跨模块协作（可替身外部边界）
  - `e2e`：真实外部依赖烟雾测试
- 触及网络 / 下载 / 代理 / 外部依赖适配时，提交前额外执行：
  - `uv run pytest -m e2e -o addopts="--strict-markers"`

## Failure Policy

- 测试失败时必须先修复根因。
- 禁止通过删除、跳过、放宽断言来规避失败。
- 新增功能若缺少测试，视为未完成。
