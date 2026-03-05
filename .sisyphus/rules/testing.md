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
  - `uv run pytest` 全量通过。

## Failure Policy

- 测试失败时必须先修复根因。
- 禁止通过删除、跳过、放宽断言来规避失败。
- 新增功能若缺少测试，视为未完成。
