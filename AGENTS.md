# Agent Working Agreement - sublingo

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
- 原则上禁止调用项目外运行时或外部二进制依赖。
- 例外：允许使用在 `pyproject.toml` 中声明并由 `uv` 管理的二进制能力：
  - `yt-dlp[default]`，提供 `yt-dlp`
  - `static-ffmpeg`，提供 `ffmpeg`、`ffprobe`
- `deno` 作为 `yt-dlp` EJS 能力所需系统依赖，允许作为运行前置条件，但不通过 `pip`/系统 Python 单独安装项目 Python 依赖。
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
- 测试采用分层策略：
  - `unit`：纯本地、确定性逻辑
  - `integration`：多模块协作，外部边界可替身
  - `e2e`：真实外部依赖（网络 / 系统）烟雾测试
- 提交前至少执行默认门禁 `uv run pytest`，且必须通过。
- 涉及网络、下载、代理、外部依赖适配等改动时，提交前还应执行：
  - `uv run pytest -m e2e -o addopts="--strict-markers"`
- 禁止通过删除、跳过、弱化断言等方式规避失败测试。

## 4. Git Policy

- 未经明确请求，禁止执行 `git commit`、`git push`、`git rebase`。
- 提交前必须完成并通过 `uv run pytest`。
- 提交前必须执行 `git status` 确认所有变更文件已 staged，禁止遗漏任何变更。
- 若修改 `pyproject.toml` 中版本号，提交前必须执行 `uv sync`，确保锁文件与环境元数据已同步，避免后续运行产生额外改动。
- 禁止提交敏感信息，例如密钥、凭据、`.env`。
- 禁止对 `main` / `master` 执行 `--force` 推送。
- 禁止在无明确要求时使用破坏性命令，例如 `reset --hard`。

## 5. Completion Standard

- 仅当“实现 + 对应测试 + `uv run pytest` 通过”同时满足时，任务才算完成。

## 6. Rule Files

- `/.sisyphus/rules/python-runtime.md`
- `/.sisyphus/rules/code-quality.md`
- `/.sisyphus/rules/testing.md`
- `/.sisyphus/rules/git-workflow.md`
