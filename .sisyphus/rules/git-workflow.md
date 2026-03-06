---
globs: ["**/*"]
alwaysApply: true
description: "Git workflow policy: safe commit practices and branch protections"
---

# Git Workflow Rules

## Commit Safety

- 未经明确请求，禁止执行 `git commit`、`git push`、`git rebase`。
- 提交前必须确认测试通过：`uv run pytest`。
- 禁止将敏感信息纳入提交，例如密钥、凭据、`.env`。

## Pre-Commit Checklist

执行 `git commit` 前必须：

1. 执行 `git status` 查看所有变更文件
2. 确认所有相关文件已 `git add` 到 staging area
3. 执行 `git diff --staged` 审查变更内容

## Version Bump Checklist

若本次改动包含 `pyproject.toml` 的 `version` 字段变更，提交前必须额外执行：

1. 执行 `uv sync`，同步 `uv.lock` 与环境元数据
2. 执行 `uv run pytest`，确认版本变更未破坏现有行为
3. 再次执行 `git status`，确认不存在因后续命令触发的遗漏改动

## Branch & Push Policy

- 禁止对 `main` / `master` 执行 `--force` 推送。
- 非明确要求下，禁止使用破坏性命令，例如 `reset --hard`、`checkout --` 覆盖改动。
- 涉及历史改写，例如 rebase 或 amend，需确保不会破坏已共享历史。

## Commit Quality

- 提交应尽量原子化：一个提交只解决一个明确问题。
- 提交信息要简洁、可读、可追溯，优先说明“为什么改”。
- 若改动跨多个关注点，应拆分为多个提交，避免混合提交。
