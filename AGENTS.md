# Agent Working Agreement（sublingo）

本文件定义本仓库内 AI / 开发代理的最低执行标准。

## 0. Rule Source of Truth

- 本仓库规范以 `AGENTS.md` + `.sisyphus/rules/` 为唯一事实来源。
- 不使用 `CLAUDE.md` / `.claude/rules/` 作为规范入口，避免双轨冲突。
- 如出现规则冲突，以本文件为最高优先级。

## 1. Runtime & Dependency Policy

- 本项目是纯 `uv` Python 项目。
- 任何 Python 相关操作必须通过 `uv` 入口执行：
  - `uv sync`
  - `uv run pytest`
  - `uv run python -m <module>`
- 禁止调用项目外运行时或外部二进制依赖（包括但不限于 `yt-dlp`、`deno`、`ffmpeg`）。
- 禁止直接使用系统 `python` / `pip` / `pytest` 执行项目任务。

## 2. Code Quality Policy

- 避免 Magic Number / Magic String。
- 避免 Hardcoded 业务常量，优先常量命名与集中声明。
- 避免 God Object、Shotgun Surgery、Spaghetti Code 及类似反模式。
- 优先小函数、单一职责、可测试接口，保持模块边界清晰。

## 3. Testing Policy

- 函数级改动必须有一一对应测试：
  - 新增函数 → 新增测试
  - 修改函数 → 更新测试
- 提交前至少执行 `uv run pytest`，且必须通过。
- 禁止通过删除、跳过、弱化断言等方式规避失败测试。

## 4. Git Policy

- 未经明确请求，禁止执行 `git commit`、`git push`、`git rebase`。
- 提交前必须完成并通过 `uv run pytest`。
- 禁止提交敏感信息（如密钥、凭据、`.env`）。
- 禁止对 `main` / `master` 执行 `--force` 推送。
- 禁止在无明确要求时使用破坏性命令（如 `reset --hard`）。

## 5. Completion Standard

- 仅当“实现 + 对应测试 + `uv run pytest` 通过”同时满足时，任务才算完成。

## 6. Rule Files

- `/.sisyphus/rules/python-runtime.md`
- `/.sisyphus/rules/code-quality.md`
- `/.sisyphus/rules/testing.md`
- `/.sisyphus/rules/git-workflow.md`
