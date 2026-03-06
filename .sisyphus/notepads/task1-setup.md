## 2026-03-06 Task 1 学习与结论（追加）

- 规则先行：先更新 `AGENTS.md` 与 `.sisyphus/rules/python-runtime.md`，再做脚手架，才能保持后续任务合规。
- 依赖基线已确认：`PySide6`、`yt-dlp[default]`、`httpx`、`pysubs2`、`fonttools`、`static-ffmpeg`，开发依赖含 `pytest`、`pytest-asyncio`、`pytest-qt`。
- 技术验证结果：`static-ffmpeg` 可用，`ffmpeg -filters` 检测到 `ass/libass`，并且 `-attach` 选项存在。
- `yt-dlp` Python API 可正常导入并输出版本。
- 当前环境未安装 `deno`，已记录为系统前置依赖（用于 `yt-dlp` EJS）。
- 架构约束已验证：`core/` 下无 `PySide6` 导入。
