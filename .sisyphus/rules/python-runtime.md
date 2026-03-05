---
globs: ["**/*.py", "pyproject.toml", "uv.lock"]
alwaysApply: false
description: "Python runtime policy: uv-only workflow and no external binary dependencies"
---

# Python Runtime Rules（uv-only）

## Mandatory Runtime

- 所有 Python 命令必须通过 `uv` 执行，不允许直接调用 `python`、`pip`、`pytest`。
- 推荐命令模板：
  - 依赖安装与同步：`uv sync`
  - 运行测试：`uv run pytest`
  - 运行模块：`uv run python -m <module>`

## Forbidden

- 禁止依赖系统全局 Python 或项目外虚拟环境。
- 禁止引入外部运行时/外部二进制依赖作为开发前提，例如：
  - `yt-dlp`
  - `deno`
  - `ffmpeg`
- 禁止使用 `pip install` 直装项目依赖（应由 `uv` 统一管理）。

## Verification

- 涉及 Python 行为变更时，至少完成：
  - `uv sync`（如依赖有变化）
  - `uv run pytest`
