# sublingo — YouTube Video Download & Subtitle Processing GUI Tool

## TL;DR

> **Quick Summary**: Build a PySide6 desktop application for downloading YouTube videos with subtitles, AI-powered subtitle translation, font subsetting, and ffmpeg-based subtitle embedding/muxing, with full workflow orchestration and batch processing.
> 
> **Deliverables**:
> - 8 core modules: config, subtitle, downloader, translator, font, ffmpeg, transcript, workflow
> - PySide6 GUI: 3 pages (Home, Tasks, Settings) + Setup Wizard
> - i18n support (English primary, Chinese translation)
> - Full test suite (tests-after strategy)
> 
> **Estimated Effort**: XL
> **Parallel Execution**: YES - 5 waves
> **Critical Path**: Task 1 → Task 2 → Task 4 → Task 7 → Task 10 → Task 13 → Task 16 → Task 19 → Task 22 → F1-F4

---

## Context

### Original Request
Build a Python GUI tool for YouTube video downloading with full subtitle processing pipeline: download (with all manual subtitles), optional transcript generation, AI translation, font subsetting, subtitle softsub/hardsub via ffmpeg. Support both independent module operation and full workflow orchestration with batch processing.

### Interview Summary
**Key Discussions**:
- Module architecture: 8 independent modules with dataclass communication
- Naming convention: `_` for word separation, `.` for semantic levels, `-` for compound identifiers
- Each module output = input_stem + module-specific suffix (module independence principle)
- AI translation: OpenAI-compatible API, default gemini-2.5-flash-preview, glossary via full system prompt injection
- Cookie: internal file, user copies Netscape format, validated before all operations
- GUI: PySide6, 3 pages + Setup Wizard, task persistence, checkpoint recovery
- i18n: English primary (source strings), Chinese as Qt translation
- No emoji in GUI (LXGWWenKai font limitation)
- Debug mode toggle in Settings controlling log granularity
- Batch: multi-URL + playlist expansion, preview before confirm, multi-threaded with LLM rate limiting

**Research Findings**:
- yt-dlp progress_hooks: status, filename, downloaded_bytes, total_bytes, speed, eta, elapsed, fragment_index/count
- yt-dlp postprocessor_hooks: status (started/processing/finished), postprocessor name, info_dict
- yt-dlp logger: needs debug/warning/error methods
- Netflix subtitle guides: Chinese 16 chars/line 9 CPS, English 42 chars/line 20 CPS
- Font subsetting: fonttools Subsetter API
- ASS manipulation: pysubs2 library
- FFmpeg softsub: map new subtitle first, set disposition, -attach for font embedding
- MKV preferred container for subtitle support

### Metis Review
**Identified Gaps (addressed in plan)**:
- AGENTS.md external dependency rule conflict: resolved by updating rules in Task 1
- Error handling/recovery strategy: defined per-module with explicit failure paths
- Thread safety (yt-dlp hooks → Qt signals): WorkerCallback bridge pattern from legacy
- Async/Qt coexistence: asyncio.run() in QThread (proven pattern from legacy)
- Task persistence format: JSON files
- No-subtitle video handling: user prompt, option to skip or abort
- File-exists strategy: skip existing artifacts, support force=True override
- static-ffmpeg libass validation: verification step in Task 1
- Deno availability: verification step in Task 1
- Scope creep lockdown: explicit exclusion list defined

---

## Work Objectives

### Core Objective
Deliver a functional, well-tested PySide6 desktop application that enables YouTube video download with comprehensive subtitle processing through modular, independently-operable components orchestrated into a seamless workflow.

### Concrete Deliverables
- `src/sublingo/core/` — 8 core modules with full test coverage
- `src/sublingo/gui/` — PySide6 interface (3 pages + wizard + widgets)
- `src/sublingo/i18n/` — English + Chinese translations
- `fonts/` — 3 LXGWWenKai TTF files
- `glossaries/` — Example glossary CSV
- `pyproject.toml` — Complete project configuration
- `tests/` — Comprehensive test suite

### Definition of Done
- [ ] `uv run pytest` passes with 0 failures
- [ ] `uv run python -m sublingo` launches GUI without crash
- [ ] All 8 core modules independently testable without GUI
- [ ] Setup Wizard completes successfully on first run
- [ ] Single video full workflow (download → translate → font → softsub) produces correct MKV
- [ ] Batch processing with 2+ URLs works end-to-end

### Must Have
- Cookie-based yt-dlp authentication (no fallback)
- HTTP/HTTPS/SOCKS5 proxy support
- All manual subtitle download
- AI translation with glossary support
- Font subsetting for CJK characters
- Softsub (subtitle as track in MKV, new subtitle first track)
- Hardsub (burn-in subtitle to video)
- Full workflow orchestration via module composition
- Batch processing with preview
- Task persistence and checkpoint recovery
- Setup Wizard (Language → AI → Other)
- Debug mode toggle
- i18n (English primary + Chinese)

### Must NOT Have (Guardrails)
- No emoji in GUI (font limitation)
- No video format/resolution selection (always best quality)
- No audio extraction or format conversion
- No custom ASS style editor (fixed built-in template)
- No multi-target-language parallel translation
- No automatic terminology extraction
- No task queue priority/pause/resume
- No scheduled tasks
- No video preview/player
- No subtitle timeline editor
- No multi-window support
- No system tray / background running
- No auto-update mechanism
- No plugin/extension system
- No cloud sync
- No `pip install` or system `python` (uv only)
- Core modules must not import PySide6
- Single Python file must not exceed 400 lines
- Tests must not depend on real network requests (use mocks; integration tests marked separately)

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: NO (blank project, will be set up in Task 1)
- **Automated tests**: YES (Tests-after)
- **Framework**: pytest (via `uv run pytest`)
- **Strategy**: Each core module implementation immediately followed by its test suite

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Core modules**: Use Bash (`uv run pytest`) — run tests, verify pass count
- **GUI**: Use Playwright (playwright skill) — launch app, navigate, interact, screenshot
- **CLI verification**: Use Bash — run module functions directly, compare output
- **Architecture**: Use ast_grep_search — verify no PySide6 imports in core/

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation — start immediately):
+-- Task 1: Project scaffolding + rules update + tech validation [deep]
+-- Task 2: Core data models + constants + ProgressCallback [quick]
+-- Task 3: Copy fonts from legacy + create example glossary [quick]

Wave 2 (Core modules — independent, MAX PARALLEL):
+-- Task 4: config module + tests (depends: 2) [quick]
+-- Task 5: subtitle module + tests (depends: 2) [unspecified-high]
+-- Task 6: transcript module + tests (depends: 2, 5) [quick]

Wave 3 (Core modules — more complex, MAX PARALLEL):
+-- Task 7: downloader module + tests (depends: 2, 4) [deep]
+-- Task 8: font module + tests (depends: 2, 5) [unspecified-high]
+-- Task 9: ffmpeg module + tests (depends: 2) [deep]

Wave 4 (Translation + Workflow — depend on earlier modules):
+-- Task 10: translator module + tests (depends: 2, 4, 5) [deep]
+-- Task 11: workflow module + tests (depends: 4-10) [deep]
+-- Task 12: i18n infrastructure + translation files (depends: 1) [unspecified-high]

Wave 5 (GUI — depends on all core):
+-- Task 13: GUI scaffolding + main window + navigation (depends: 1, 4, 12) [visual-engineering]
+-- Task 14: Setup Wizard (depends: 4, 12, 13) [visual-engineering]
+-- Task 15: Settings page (depends: 4, 12, 13) [visual-engineering]
+-- Task 16: Home page — task creation (depends: 4, 7, 12, 13) [visual-engineering]
+-- Task 17: Task models + persistence + TaskManager (depends: 2, 4, 11) [unspecified-high]
+-- Task 18: Workers (TaskWorker + AsyncTaskWorker + WorkerCallback) (depends: 2, 17) [unspecified-high]
+-- Task 19: Tasks page — monitoring + stepper + details (depends: 12, 13, 17, 18) [visual-engineering]
+-- Task 20: Batch processing integration (depends: 7, 16, 17, 19) [deep]
+-- Task 21: GUI smoke tests (depends: 13-20) [unspecified-high]

Wave FINAL (After ALL tasks — independent review, 4 parallel):
+-- Task F1: Plan compliance audit (oracle)
+-- Task F2: Code quality review (unspecified-high)
+-- Task F3: Real manual QA (unspecified-high + playwright)
+-- Task F4: Scope fidelity check (deep)

Critical Path: T1 -> T2 -> T4 -> T7 -> T10 -> T11 -> T17 -> T18 -> T19 -> T21 -> FINAL
Parallel Speedup: ~65% faster than sequential
Max Concurrent: 5 (Wave 2-3)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| 1 | — | 3, 4-12, 13 | 1 |
| 2 | — | 4-11, 17, 18 | 1 |
| 3 | — | 8 | 1 |
| 4 | 2 | 7, 10, 11, 13-17 | 2 |
| 5 | 2 | 6, 8, 10, 11 | 2 |
| 6 | 2, 5 | 11 | 2 |
| 7 | 2, 4 | 11, 16, 20 | 3 |
| 8 | 2, 5 | 11 | 3 |
| 9 | 2 | 11 | 3 |
| 10 | 2, 4, 5 | 11 | 4 |
| 11 | 4-10 | 17, 20 | 4 |
| 12 | 1 | 13-16, 19 | 4 |
| 13 | 1, 4, 12 | 14-16, 19, 21 | 5 |
| 14 | 4, 12, 13 | 21 | 5 |
| 15 | 4, 12, 13 | 21 | 5 |
| 16 | 4, 7, 12, 13 | 20, 21 | 5 |
| 17 | 2, 4, 11 | 18, 19, 20 | 5 |
| 18 | 2, 17 | 19, 20 | 5 |
| 19 | 12, 13, 17, 18 | 20, 21 | 5 |
| 20 | 7, 16, 17, 19 | 21 | 5 |
| 21 | 13-20 | FINAL | 5 |

### Agent Dispatch Summary

- **Wave 1**: 3 tasks — T1 `deep`, T2 `quick`, T3 `quick`
- **Wave 2**: 3 tasks — T4 `quick`, T5 `unspecified-high`, T6 `quick`
- **Wave 3**: 3 tasks — T7 `deep`, T8 `unspecified-high`, T9 `deep`
- **Wave 4**: 3 tasks — T10 `deep`, T11 `deep`, T12 `unspecified-high`
- **Wave 5**: 9 tasks — T13-16,19 `visual-engineering`, T17-18 `unspecified-high`, T20 `deep`, T21 `unspecified-high`
- **FINAL**: 4 tasks — F1 `oracle`, F2 `unspecified-high`, F3 `unspecified-high`, F4 `deep`

---

## TODOs

- [x] 1. Project Scaffolding + Rules Update + Tech Validation

  **What to do**:
  - Create `pyproject.toml` with all dependencies:
    - Runtime: `PySide6`, `yt-dlp[default]`, `httpx`, `pysubs2`, `fonttools`, `static-ffmpeg`
    - Dev: `pytest`, `pytest-asyncio`, `pytest-qt`
  - Create package structure:
    ```
    src/sublingo/
      __init__.py
      __main__.py           # Entry point: launch GUI
      core/
        __init__.py
        models.py            # (placeholder, built in Task 2)
        constants.py         # (placeholder, built in Task 2)
      gui/
        __init__.py
      i18n/
        .gitkeep
    tests/
      __init__.py
      conftest.py           # Shared fixtures
    fonts/
      .gitkeep
    glossaries/
      .gitkeep
    ```
  - Update `AGENTS.md` section 1 ("Runtime & Dependency Policy"):
    - Add exception for declared external binary dependencies: yt-dlp, ffmpeg, ffprobe, deno
    - Clarify these are managed via `uv` as Python package dependencies (`yt-dlp[default]`, `static-ffmpeg`)
    - Deno: document as system dependency required for yt-dlp EJS
  - Update `.sisyphus/rules/python-runtime.md` accordingly
  - Run `uv sync` to install all dependencies
  - **Tech validation** (CRITICAL before proceeding):
    - Verify `static-ffmpeg` provides ffmpeg with libass filter: `uv run python -c "import static_ffmpeg; static_ffmpeg.add_paths()" && ffmpeg -filters 2>&1 | grep ass`
    - Verify `static-ffmpeg` supports `-attach` for MKV font embedding
    - Verify `yt-dlp` Python API works: `uv run python -c "import yt_dlp; print(yt_dlp.version.__version__)"`
    - Verify Deno availability or document installation requirement
  - Run `uv run pytest` (should pass with 0 tests collected)

  **Must NOT do**:
  - Do not implement any business logic
  - Do not add dependencies not listed above
  - Do not create GUI code yet

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Involves project setup, dependency resolution, tech validation with potential troubleshooting
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: Not needed for scaffolding

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 2, 3)
  - **Parallel Group**: Wave 1 (with Tasks 2, 3)
  - **Blocks**: Tasks 3, 4-12, 13
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `/home/joe/sublingo-legacy/pyproject.toml` — Reference for dependency declarations, uv configuration, and package metadata structure
  - `/home/joe/sublingo-legacy/src/sublingo/__main__.py` — Entry point pattern (how to launch PySide6 app)

  **API/Type References**:
  - `/home/joe/sublingo/AGENTS.md:16-22` — Current rules that need updating (external binary prohibition)
  - `/home/joe/sublingo/.sisyphus/rules/python-runtime.md` — Runtime rules that need updating

  **External References**:
  - `static-ffmpeg` PyPI: https://pypi.org/project/static-ffmpeg/ — Check capabilities
  - yt-dlp installation: `pip install -U "yt-dlp[default]"` per official docs

  **WHY Each Reference Matters**:
  - Legacy pyproject.toml shows proven uv configuration for this exact tech stack
  - AGENTS.md must be updated FIRST or all subsequent tasks violate project rules

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Project structure is valid
    Tool: Bash
    Preconditions: Fresh clone
    Steps:
      1. Run `uv sync`
      2. Run `uv run python -c "import sublingo; print('OK')"`
      3. Run `uv run pytest --co` to collect tests (should find conftest.py)
    Expected Result: All 3 commands exit 0
    Failure Indicators: Import error, missing package, pytest error
    Evidence: .sisyphus/evidence/task-1-project-structure.txt

  Scenario: static-ffmpeg provides libass filter
    Tool: Bash
    Preconditions: uv sync completed
    Steps:
      1. Run `uv run python -c "import static_ffmpeg; static_ffmpeg.add_paths(); import subprocess; r=subprocess.run(['ffmpeg','-filters'],capture_output=True,text=True); print('libass' if 'ass' in r.stdout else 'NO_LIBASS')"`
    Expected Result: Output contains "libass"
    Failure Indicators: "NO_LIBASS" or ImportError
    Evidence: .sisyphus/evidence/task-1-ffmpeg-libass.txt

  Scenario: yt-dlp Python API works
    Tool: Bash
    Preconditions: uv sync completed
    Steps:
      1. Run `uv run python -c "import yt_dlp; print(yt_dlp.version.__version__)"`
    Expected Result: Version string printed (e.g. "2025.x.x")
    Failure Indicators: ImportError
    Evidence: .sisyphus/evidence/task-1-ytdlp-version.txt

  Scenario: AGENTS.md rules updated
    Tool: Bash (grep)
    Preconditions: Files edited
    Steps:
      1. Search AGENTS.md for "yt-dlp" — should appear in allowed dependencies
      2. Search AGENTS.md for old prohibition text — should be removed/modified
    Expected Result: yt-dlp, ffmpeg, deno mentioned as allowed dependencies
    Failure Indicators: Old prohibition text still present
    Evidence: .sisyphus/evidence/task-1-rules-updated.txt
  ```

  **Commit**: YES
  - Message: `chore(project): scaffold project structure and update dependency rules`
  - Files: `pyproject.toml`, `src/sublingo/**`, `tests/**`, `AGENTS.md`, `.sisyphus/rules/python-runtime.md`
  - Pre-commit: `uv run pytest`

- [x] 2. Core Data Models + Constants + ProgressCallback Protocol

  **What to do**:
  - Create `src/sublingo/core/models.py` with all dataclasses:
    - `VideoInfo`: url, video_id, title, duration, channel, upload_date, thumbnail_url, view_count, available_subtitles (dict[str, list[str]]), available_auto_captions (dict[str, list[str]])
    - `DownloadResult`: success, video_path (Path|None), subtitle_paths (list[Path]), video_title, error (str|None), warnings (list[str])
    - `TranslateResult`: success, output_path (Path|None), source_lang, target_lang, entry_count, failed_count, error (str|None), warnings (list[str])
    - `FontSubsetResult`: success, output_path (Path|None), original_size, subset_size, char_count, error (str|None), warnings (list[str])
    - `TranscriptResult`: success, transcript_path (Path|None), error (str|None), warnings (list[str])
    - `MuxResult` (softsub): success, output_path (Path|None), error (str|None), warnings (list[str])
    - `BurnResult` (hardsub): success, output_path (Path|None), error (str|None), warnings (list[str])
    - `StreamInfo`: index, codec_type, codec_name, language (str|None), title (str|None)
    - `ProjectStatus`: has_video, has_subtitle, has_translated, has_font, has_final, next_stage (str)
    - `WorkflowResult`: success, current_stage, download (DownloadResult|None), translate (TranslateResult|None), font (FontSubsetResult|None), mux (MuxResult|None), video_title, error (str|None), warnings (list[str])
    - `SubtitleEntry`: start_ms (int), end_ms (int), text (str)
    - `BilingualEntry`: start_ms (int), end_ms (int), original (str), translated (str)
  - Create `ProgressCallback` Protocol:
    - `on_progress(self, current: int, total: int, message: str = "", **meta: Any) -> None`
    - `on_log(self, level: str, message: str, detail: str = "") -> None`
    - Document meta keys: stage, stage_status, speed, eta, downloaded_bytes, total_bytes, batch, total_batches, postprocessor
  - Create `src/sublingo/core/constants.py` with all constants:
    - AI constants: timeouts, retries, temperatures, batch sizes, default model (gemini-2.5-flash-preview)
    - Subtitle constants: ASS resolution (1920x1080), font sizes (primary 58, secondary 38), margins, colors, timing
    - Downloader constants: YouTube URL patterns, video ID length, ANSI escape pattern
    - Config defaults: default font (LXGWWenKai-Medium.ttf), default API base URLs for each provider
    - FFmpeg constants: timeouts, error truncation
    - AI provider presets: dict mapping provider name -> (base_url, default_model)
  - Create `tests/test_models.py` with basic tests
  - Use `from __future__ import annotations` in every file

  **Must NOT do**:
  - Do not implement business logic in models
  - Do not import PySide6
  - Do not exceed 400 lines per file (split constants if needed)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Straightforward dataclass definitions and constant declarations
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 1, 3)
  - **Parallel Group**: Wave 1 (with Tasks 1, 3)
  - **Blocks**: Tasks 4-11, 17, 18
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `/home/joe/sublingo-legacy/src/sublingo/core/models.py` — Exact pattern for dataclass definitions and ProgressCallback protocol. Follow the same structure with `from __future__ import annotations`, `@dataclass` decorator, `Protocol` class
  - `/home/joe/sublingo-legacy/src/sublingo/core/constants.py` — Constant organization pattern: grouped by module with section dividers

  **API/Type References**:
  - Draft file `/home/joe/sublingo/.sisyphus/drafts/sublingo-gui-tool.md` sections "VideoInfo fields" and "AppConfig field order" — Exact field definitions agreed with user

  **External References**:
  - yt-dlp source (YoutubeDL.py) progress_hooks documentation — Exact meta field names for download progress

  **WHY Each Reference Matters**:
  - Legacy models.py is the proven pattern for Protocol-based callbacks and dataclass I/O structures
  - Constants.py grouping pattern prevents magic numbers scattered across codebase
  - Draft file contains user-confirmed field lists and naming conventions

  **Acceptance Criteria**:

  ```
  Scenario: All data models importable
    Tool: Bash
    Preconditions: uv sync completed
    Steps:
      1. Run `uv run python -c "from sublingo.core.models import VideoInfo, DownloadResult, TranslateResult, FontSubsetResult, TranscriptResult, MuxResult, BurnResult, StreamInfo, ProjectStatus, WorkflowResult, SubtitleEntry, BilingualEntry, ProgressCallback; print('OK')"`
    Expected Result: "OK" printed
    Failure Indicators: ImportError
    Evidence: .sisyphus/evidence/task-2-models-import.txt

  Scenario: Constants properly defined
    Tool: Bash
    Preconditions: uv sync completed
    Steps:
      1. Run `uv run python -c "from sublingo.core.constants import AI_PROVIDER_PRESETS, SUBTITLE_ASS_RESOLUTION_X, CONFIG_DEFAULT_FONT; print(AI_PROVIDER_PRESETS['gemini'][1]); print(SUBTITLE_ASS_RESOLUTION_X); print(CONFIG_DEFAULT_FONT)"`
    Expected Result: "gemini-2.5-flash-preview", "1920", "LXGWWenKai-Medium.ttf"
    Failure Indicators: KeyError or wrong values
    Evidence: .sisyphus/evidence/task-2-constants.txt

  Scenario: Model tests pass
    Tool: Bash
    Preconditions: Tests written
    Steps:
      1. Run `uv run pytest tests/test_models.py -v`
    Expected Result: All tests pass
    Failure Indicators: Any test failure
    Evidence: .sisyphus/evidence/task-2-tests.txt
  ```

  **Commit**: YES
  - Message: `feat(core): add data models, constants, and ProgressCallback protocol`
  - Files: `src/sublingo/core/models.py`, `src/sublingo/core/constants.py`, `tests/test_models.py`
  - Pre-commit: `uv run pytest`

- [x] 3. Copy Fonts + Create Example Glossary

  **What to do**:
  - Copy 3 font files from `/home/joe/sublingo-legacy/fonts/` to `fonts/`:
    - `LXGWWenKai-Regular.ttf` (GUI rendering, CJK support on non-CJK systems)
    - `LXGWWenKai-Medium.ttf` (default softsub font)
    - `LXGWWenKai-Light.ttf` (alternative option)
  - Create `glossaries/example.csv` with sample terminology entries:
    ```csv
    source,target
    machine learning,机器学习
    artificial intelligence,人工智能
    neural network,神经网络
    ```
  - Verify font files are valid TTF: `uv run python -c "from fonttools.ttLib import TTFont; TTFont('fonts/LXGWWenKai-Medium.ttf'); print('OK')"`

  **Must NOT do**:
  - Do not modify font files
  - Do not create complex glossary structures

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple file copy and CSV creation
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 1, 2)
  - **Parallel Group**: Wave 1 (with Tasks 1, 2)
  - **Blocks**: Task 8
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `/home/joe/sublingo-legacy/fonts/` — Source of the 3 TTF files to copy
  - `/home/joe/sublingo-legacy/glossaries/` — Reference for glossary format (if exists)

  **WHY Each Reference Matters**:
  - Font files are runtime assets that must be bit-for-bit identical to legacy
  - Glossary CSV format must match what translator module expects (source,target columns)

  **Acceptance Criteria**:

  ```
  Scenario: Font files are valid
    Tool: Bash
    Preconditions: Files copied
    Steps:
      1. Run `ls -la fonts/*.ttf` to verify 3 files exist
      2. Run `uv run python -c "from fontTools.ttLib import TTFont; [TTFont(f'fonts/{n}') for n in ('LXGWWenKai-Regular.ttf','LXGWWenKai-Medium.ttf','LXGWWenKai-Light.ttf')]; print('OK')"`
    Expected Result: 3 files listed, "OK" printed
    Failure Indicators: FileNotFoundError or TTFont parse error
    Evidence: .sisyphus/evidence/task-3-fonts.txt

  Scenario: Glossary CSV is valid
    Tool: Bash
    Preconditions: File created
    Steps:
      1. Run `uv run python -c "import csv; r=list(csv.DictReader(open('glossaries/example.csv'))); assert r[0]['source']=='machine learning'; assert r[0]['target']=='机器学习'; print(f'{len(r)} entries OK')"`
    Expected Result: "3 entries OK"
    Failure Indicators: KeyError or assertion error
    Evidence: .sisyphus/evidence/task-3-glossary.txt
  ```

  **Commit**: YES
  - Message: `chore(assets): add fonts and example glossary`
  - Files: `fonts/*.ttf`, `glossaries/example.csv`
  - Pre-commit: `uv run pytest`

- [x] 4. Config Module + Tests

  **What to do**:
  - Create `src/sublingo/core/config.py`:
    - `AppConfig` dataclass with fields (in order):
      - project_dir, output_dir
      - target_language ("zh-Hans"), generate_transcript (False)
      - font_file ("LXGWWenKai-Medium.ttf")
      - ai_provider ("gemini"), ai_base_url, ai_model ("gemini-2.5-flash-preview"), ai_api_key, ai_translate_batch_size (20), ai_proofread_batch_size (45), ai_segment_batch_size (45), ai_max_retries (3)
      - proxy ("" — empty string means no proxy)
      - language ("auto"), debug_mode (False)
    - `ConfigManager` class:
      - `__init__(self, project_root: Path)` — sets config_file path, cookie_file path
      - `load(self) -> AppConfig` — JSON load with backward compat, unknown field filtering
      - `save(self, config: AppConfig) -> None` — JSON dump with pretty format
      - `reset(self) -> None` — delete config.json, clear cache
      - `is_first_run` property — checks config.json existence
      - `cookie_file` property — returns project_root / "cookies.txt"
      - `resolve_project_dir(self) -> Path` — resolve relative to project_root
      - `resolve_output_dir(self) -> Path` — resolve relative to project_root
      - `get_default(self, key: str) -> Any` — get default value for a field
  - Create `src/sublingo/core/cookie.py`:
    - `validate_cookie_file(path: Path) -> tuple[bool, str]` — check Netscape format cookie file validity
    - `import_cookie_file(source: Path, dest: Path) -> None` — copy cookie file to project location
  - Create `tests/test_config.py` with tests:
    - Default values are correct (especially gemini-2.5-flash-preview)
    - JSON round-trip consistency
    - Missing fields use defaults
    - Reset deletes file
    - Unknown fields are filtered
  - Create `tests/test_cookie.py` with tests:
    - Valid cookie file passes validation
    - Invalid file fails with descriptive message
    - Import copies file correctly

  **Must NOT do**:
  - Do not import PySide6
  - Do not hardcode paths (use constants from constants.py)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple dataclass + JSON I/O, well-defined pattern from legacy
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 5, 6)
  - **Parallel Group**: Wave 2 (with Tasks 5, 6)
  - **Blocks**: Tasks 7, 10, 11, 13-17
  - **Blocked By**: Task 2

  **References**:

  **Pattern References**:
  - `/home/joe/sublingo-legacy/src/sublingo/core/config.py` — Exact ConfigManager pattern: lazy load, JSON round-trip, backward compat mapping, field filtering, resolve relative paths
  - `/home/joe/sublingo-legacy/src/sublingo/core/cookie.py` — Cookie validation logic
  - `/home/joe/sublingo-legacy/src/sublingo/core/constants.py:129-135` — Config default values pattern

  **WHY Each Reference Matters**:
  - Legacy config.py is a proven, tested implementation of exactly this pattern
  - Cookie validation must check Netscape format headers correctly

  **Acceptance Criteria**:

  ```
  Scenario: Config defaults are correct
    Tool: Bash
    Preconditions: Module implemented
    Steps:
      1. Run `uv run python -c "from sublingo.core.config import AppConfig; c=AppConfig(); print(c.ai_model, c.ai_provider, c.font_file, c.target_language)"`
    Expected Result: "gemini-2.5-flash-preview gemini LXGWWenKai-Medium.ttf zh-Hans"
    Evidence: .sisyphus/evidence/task-4-defaults.txt

  Scenario: Config tests pass
    Tool: Bash
    Steps:
      1. Run `uv run pytest tests/test_config.py tests/test_cookie.py -v`
    Expected Result: All tests pass
    Evidence: .sisyphus/evidence/task-4-tests.txt
  ```

  **Commit**: YES
  - Message: `feat(core): implement config module with ConfigManager`
  - Files: `src/sublingo/core/config.py`, `src/sublingo/core/cookie.py`, `tests/test_config.py`, `tests/test_cookie.py`
  - Pre-commit: `uv run pytest`

- [x] 5. Subtitle Module + Tests

  **What to do**:
  - Create `src/sublingo/core/subtitle.py`:
    - `parse_subtitle(path: Path) -> list[SubtitleEntry]` — Parse VTT or SRT file into SubtitleEntry list. Auto-detect format by extension. Handle BOM with utf-8-sig. Strip HTML tags from VTT.
    - `is_auto_generated(entries: list[SubtitleEntry]) -> bool` — Detect auto-generated subtitles by analyzing timestamp patterns: if most entries have per-word timestamps (very short durations, overlapping) treat as auto; if sentence-level timestamps, treat as manual.
    - `generate_bilingual_ass(entries: list[BilingualEntry], *, font_name: str, resolution: tuple[int, int] = (1920, 1080)) -> str` — Generate ASS content string with two styles: primary (translated, larger, bottom) and secondary (original, smaller, above primary). Use constants from constants.py for font sizes, colors, margins, outline.
    - `write_ass(content: str, path: Path) -> None` — Write ASS string to file with UTF-8 encoding.
  - Create `tests/test_subtitle.py`:
    - VTT parsing preserves timestamps and text
    - SRT parsing preserves timestamps and text
    - BOM handling (utf-8-sig files)
    - Auto-generated detection for word-level vs sentence-level timestamps
    - Bilingual ASS generation contains both styles
    - ASS output is valid (can be re-parsed by pysubs2)
  - Create test fixture files in `tests/fixtures/`:
    - `sample.en.vtt` — Manual subtitle sample
    - `sample.en.srt` — SRT version
    - `sample_auto.en.vtt` — Auto-generated subtitle sample (word-level timestamps)

  **Must NOT do**:
  - Do not import PySide6
  - Do not implement translation logic (that's translator module)
  - Do not use magic numbers for ASS styling (use constants)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Subtitle parsing has edge cases (BOM, HTML tags, various timestamp formats), needs careful implementation
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 4, 6)
  - **Parallel Group**: Wave 2 (with Tasks 4, 6)
  - **Blocks**: Tasks 6, 8, 10, 11
  - **Blocked By**: Task 2

  **References**:

  **Pattern References**:
  - `/home/joe/sublingo-legacy/src/sublingo/core/subtitle.py` — Complete subtitle parsing implementation: VTT/SRT/ASS parsing, BOM handling, HTML strip, ASS export. Study the `_strip_bom()`, `parse_vtt()`, `parse_srt()`, `export_ass()` functions
  - `/home/joe/sublingo-legacy/src/sublingo/core/constants.py:48-83` — ASS styling constants (resolution, font sizes, colors, margins)

  **External References**:
  - pysubs2 documentation: https://pysubs2.readthedocs.io/ — ASS format manipulation API
  - Netflix style guides (researched): Chinese 16 chars/line, English 42 chars/line — inform ASS line wrapping

  **WHY Each Reference Matters**:
  - Legacy subtitle.py has proven VTT/SRT parsing with edge case handling (BOM, HTML tags, empty lines)
  - Constants ensure consistent ASS styling across all generated subtitles
  - pysubs2 may be used for ASS validation in tests

  **Acceptance Criteria**:

  ```
  Scenario: Subtitle parsing tests pass
    Tool: Bash
    Steps:
      1. Run `uv run pytest tests/test_subtitle.py -v`
    Expected Result: All tests pass (VTT, SRT, BOM, auto-detect, ASS generation)
    Evidence: .sisyphus/evidence/task-5-tests.txt

  Scenario: Generated ASS is valid
    Tool: Bash
    Steps:
      1. Run `uv run python -c "from sublingo.core.subtitle import generate_bilingual_ass; from sublingo.core.models import BilingualEntry; entries=[BilingualEntry(0,2000,'Hello','你好')]; ass=generate_bilingual_ass(entries,font_name='LXGWWenKai-Medium'); import pysubs2; subs=pysubs2.SSAFile.from_string(ass); print(f'{len(subs)} events, {len(subs.styles)} styles')"`
    Expected Result: "1 events, 2 styles" (or similar valid count)
    Evidence: .sisyphus/evidence/task-5-ass-valid.txt
  ```

  **Commit**: YES
  - Message: `feat(core): implement subtitle parsing and ASS generation`
  - Files: `src/sublingo/core/subtitle.py`, `tests/test_subtitle.py`, `tests/fixtures/sample*.vtt`, `tests/fixtures/sample*.srt`
  - Pre-commit: `uv run pytest`

- [x] 6. Transcript Module + Tests

  **What to do**:
  - Create `src/sublingo/core/transcript.py`:
    - `generate_transcript(subtitle_path: Path, *, output_dir: Path | None = None) -> TranscriptResult` — Parse subtitle file, extract pure text (remove timestamps, deduplicate overlapping text from auto-subs), join with newlines, write to `{input_stem}.transcript.txt`.
    - Handle both VTT and SRT input via subtitle.parse_subtitle()
    - Output naming: `{input_stem}.transcript.txt`
  - Create `tests/test_transcript.py`:
    - VTT input produces correct transcript text
    - SRT input produces correct transcript text
    - Duplicate lines (common in auto-subs) are deduplicated
    - Output file naming follows convention
    - output_dir parameter works correctly

  **Must NOT do**:
  - Do not import PySide6
  - Do not implement whisper/speech-to-text (transcript is from existing subtitles only)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple text extraction from parsed subtitles
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 4, 5)
  - **Parallel Group**: Wave 2 (with Tasks 4, 5)
  - **Blocks**: Task 11
  - **Blocked By**: Tasks 2, 5 (uses subtitle.parse_subtitle)

  **References**:

  **Pattern References**:
  - `/home/joe/sublingo-legacy/src/sublingo/core/transcript.py` — Complete transcript generation logic: text extraction, deduplication, file writing

  **WHY Each Reference Matters**:
  - Legacy transcript.py has proven deduplication logic for auto-subtitle overlap

  **Acceptance Criteria**:

  ```
  Scenario: Transcript tests pass
    Tool: Bash
    Steps:
      1. Run `uv run pytest tests/test_transcript.py -v`
    Expected Result: All tests pass
    Evidence: .sisyphus/evidence/task-6-tests.txt
  ```

  **Commit**: YES
  - Message: `feat(core): implement transcript generation from subtitles`
  - Files: `src/sublingo/core/transcript.py`, `tests/test_transcript.py`
  - Pre-commit: `uv run pytest`

- [x] 7. Downloader Module + Tests

  **What to do**:
  - Create `src/sublingo/core/downloader.py`:
    - `extract_info(url: str, *, cookie_file: Path, proxy: str | None = None) -> VideoInfo` — Use yt_dlp.YoutubeDL with `extract_flat=False`, `download=False` to get video metadata. Map info_dict fields to VideoInfo dataclass. Support single video and playlist URLs. For playlists, return list via separate function.
    - `extract_playlist_info(url: str, *, cookie_file: Path, proxy: str | None = None) -> list[VideoInfo]` — Extract all video info from playlist URL.
    - `download(url: str, *, output_dir: Path, cookie_file: Path, proxy: str | None = None, progress: ProgressCallback | None = None) -> DownloadResult` — Download video + all manual subtitles.
    - YoutubeDL params (from yt-dlp docs, verified):
      - `cookiefile`: str(cookie_file)
      - `proxy`: proxy string if provided
      - `writesubtitles`: True
      - `subtitleslangs`: ["all", "-live_chat"]
      - `subtitlesformat`: "srt/vtt/best"
      - `restrictfilenames`: True
      - `outtmpl`: `{title}.%(ext)s` for video, with subtitle template matching `{title}.sub-%(lang)s.%(ext)s`
      - `compat_options`: {"no-live-chat"}
      - `progress_hooks`: [custom hook that calls ProgressCallback.on_progress with speed/eta/bytes meta]
      - `postprocessor_hooks`: [custom hook for post-processing status]
      - `logger`: custom logger that routes to ProgressCallback.on_log
      - `quiet`: True (we use our own logger)
      - `no_warnings`: False (capture warnings via logger)
    - Custom YtDlpLogger class with debug/warning/error methods routing to ProgressCallback.on_log
    - Custom progress hook function that maps yt-dlp dict to ProgressCallback.on_progress meta
    - Handle no-subtitle case: log warning, continue (subtitle_paths will be empty)
    - Handle subtitle file renaming: yt-dlp outputs as `{title}.{lang}.{ext}`, rename to `{title}.sub-{lang}.{ext}` for manual subtitles
  - Create `tests/test_downloader.py`:
    - Mock yt_dlp.YoutubeDL to test parameter construction
    - Verify cookie_file is passed correctly
    - Verify proxy is passed correctly
    - Verify progress hook maps yt-dlp dict to our ProgressCallback
    - Verify subtitle file renaming logic
    - Verify error handling for various yt-dlp exceptions

  **Must NOT do**:
  - Do not import PySide6
  - Do not provide any fallback when cookie is missing (raise clear error)
  - Do not download auto-subs by default (only manual subtitles; writeautomaticsub=False)
  - Do not hardcode yt-dlp parameters without docs reference

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: yt-dlp integration is complex with many parameters, hook mappings, and edge cases. Must match documented API exactly.
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 8, 9)
  - **Parallel Group**: Wave 3 (with Tasks 8, 9)
  - **Blocks**: Tasks 11, 16, 20
  - **Blocked By**: Tasks 2, 4

  **References**:

  **Pattern References**:
  - `/home/joe/sublingo-legacy/src/sublingo/core/downloader.py` — yt-dlp wrapper pattern: YoutubeDL params construction, progress hook mapping, logger class, project dir handling
  - `/mnt/c/Users/Joe/OneDrive/Program/Video-Tools-Suite/scripts/download.ps1` — Working yt-dlp parameter set: `--restrict-filenames`, `--compat-options no-live-chat`, `--extractor-args youtube:player_js_variant=tv`, subtitle selection logic

  **API/Type References**:
  - yt-dlp YoutubeDL.py source (fetched): `progress_hooks` dict structure — status, filename, downloaded_bytes, total_bytes, speed, eta, elapsed, fragment_index, fragment_count
  - yt-dlp YoutubeDL.py source: `postprocessor_hooks` — status (started/processing/finished), postprocessor name
  - yt-dlp YoutubeDL.py source: `logger` — needs debug(msg), warning(msg), error(msg) methods
  - yt-dlp YoutubeDL.py source: `cookiefile`, `proxy`, `writesubtitles`, `subtitleslangs`, `subtitlesformat`, `restrictfilenames`, `outtmpl`

  **External References**:
  - yt-dlp README subtitle options: `--write-subs`, `--sub-langs all,-live_chat`, `--sub-format srt/vtt/best`
  - yt-dlp README Python API: `YoutubeDL(params).extract_info(url, download=False)` and `YoutubeDL(params).download([url])`

  **WHY Each Reference Matters**:
  - Legacy downloader.py has the proven yt-dlp integration pattern
  - VTS download.ps1 has the working parameter set that successfully downloads from YouTube
  - yt-dlp source code documents exact hook dict structure (not approximated from docs)

  **Acceptance Criteria**:

  ```
  Scenario: Downloader tests pass
    Tool: Bash
    Steps:
      1. Run `uv run pytest tests/test_downloader.py -v`
    Expected Result: All tests pass (yt-dlp mocked)
    Evidence: .sisyphus/evidence/task-7-tests.txt

  Scenario: YoutubeDL params are correct
    Tool: Bash
    Steps:
      1. Run `uv run python -c "from sublingo.core.downloader import _build_ytdlp_params; params=_build_ytdlp_params(output_dir='/tmp', cookie_file='/tmp/cookies.txt', proxy='socks5://127.0.0.1:1080'); print(params.get('writesubtitles'), params.get('cookiefile'), params.get('proxy'))"`
    Expected Result: "True /tmp/cookies.txt socks5://127.0.0.1:1080"
    Evidence: .sisyphus/evidence/task-7-params.txt
  ```

  **Commit**: YES
  - Message: `feat(core): implement yt-dlp downloader module`
  - Files: `src/sublingo/core/downloader.py`, `tests/test_downloader.py`
  - Pre-commit: `uv run pytest`

- [x] 8. Font Module + Tests

  **What to do**:
  - Create `src/sublingo/core/font.py`:
    - `subset_font(subtitle_path: Path, font_path: Path, *, output_dir: Path | None = None) -> FontSubsetResult` — Extract all unique characters from subtitle file (parse ASS/SRT/VTT text), then use fonttools Subsetter to create a subset font containing only those characters. Output naming: `{input_subtitle_stem}.{fontname}.ttf`.
    - Internal helper `_extract_chars(subtitle_path: Path) -> set[str]` — Parse subtitle and extract unique characters, stripping ASS tags if present.
    - Use `fontTools.subset.Subsetter` with options: `layout_features=['*']` to preserve all OpenType features, `notdef_outline=True`.
  - Create `tests/test_font.py`:
    - Subset font is smaller than original
    - Subset font contains all characters from input subtitle
    - Output file naming follows convention: `{subtitle_stem}.{fontname}.ttf`
    - Empty subtitle produces minimal subset (just .notdef)
    - CJK characters are properly handled

  **Must NOT do**:
  - Do not import PySide6
  - Do not modify the original font file

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: fonttools API has specific usage patterns for subsetting
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 7, 9)
  - **Parallel Group**: Wave 3 (with Tasks 7, 9)
  - **Blocks**: Task 11
  - **Blocked By**: Tasks 2, 5 (uses subtitle parsing), 3 (needs font files)

  **References**:

  **Pattern References**:
  - `/home/joe/sublingo-legacy/src/sublingo/core/font.py` — Font subsetting implementation: character extraction, fonttools Subsetter usage, file size reporting

  **External References**:
  - fonttools subsetting: https://fonttools.readthedocs.io/en/latest/subset/index.html — Subsetter API
  - fonttools TTFont: `fontTools.ttLib.TTFont` for loading/saving

  **WHY Each Reference Matters**:
  - Legacy font.py has the proven fonttools subsetting pattern with CJK support

  **Acceptance Criteria**:

  ```
  Scenario: Font tests pass
    Tool: Bash
    Steps:
      1. Run `uv run pytest tests/test_font.py -v`
    Expected Result: All tests pass
    Evidence: .sisyphus/evidence/task-8-tests.txt

  Scenario: Subset font is smaller
    Tool: Bash
    Steps:
      1. Run `uv run python -c "from sublingo.core.font import subset_font; from pathlib import Path; r=subset_font(Path('tests/fixtures/sample.en.vtt'), Path('fonts/LXGWWenKai-Medium.ttf'), output_dir=Path('/tmp')); print(f'orig={r.original_size} subset={r.subset_size} chars={r.char_count} smaller={r.subset_size < r.original_size}')"`
    Expected Result: "smaller=True" with reasonable sizes
    Evidence: .sisyphus/evidence/task-8-subset-size.txt
  ```

  **Commit**: YES
  - Message: `feat(core): implement font subsetting module`
  - Files: `src/sublingo/core/font.py`, `tests/test_font.py`
  - Pre-commit: `uv run pytest`

- [x] 9. FFmpeg Module + Tests

  **What to do**:
  - Create `src/sublingo/core/ffmpeg.py`:
    - `probe_streams(video_path: Path) -> list[StreamInfo]` — Run ffprobe to get all streams (video/audio/subtitle). Parse JSON output into StreamInfo dataclass list.
    - `softsub(video_path: Path, subtitle_path: Path, *, font_path: Path | None = None, output_dir: Path | None = None, progress: ProgressCallback | None = None) -> MuxResult` — MKV muxing:
      - Map new subtitle as first subtitle track (s:0)
      - Map all existing streams (video, audio, existing subtitles after new one)
      - Set disposition: new subtitle default, existing subtitles non-default
      - If font_path provided, attach font with `-attach` and `mimetype=font/ttf`
      - Output: `{input_video_stem}.softsub.mkv`
      - Build ffmpeg command from probe results (need to know existing subtitle count)
    - `hardsub(video_path: Path, subtitle_path: Path, *, font_path: Path | None = None, output_dir: Path | None = None, progress: ProgressCallback | None = None) -> BurnResult` — Burn-in subtitles:
      - Use `-vf "ass={subtitle_path}"` for ASS subtitles
      - If font_path, add fontsdir or use ass style with embedded font reference
      - Re-encode video, copy audio
      - Output: `{input_video_stem}.hardsub.mp4`
    - Internal helper `_run_ffmpeg(args: list[str], *, progress: ProgressCallback | None = None, timeout: int) -> subprocess.CompletedProcess` — Run ffmpeg subprocess, parse progress output, route to callback.
    - Use `static_ffmpeg.add_paths()` at module level to ensure ffmpeg/ffprobe are on PATH.
  - Create `tests/test_ffmpeg.py`:
    - Mock subprocess to test command construction
    - Verify softsub command has correct -map order (new subtitle first)
    - Verify softsub sets disposition correctly
    - Verify hardsub uses -vf "ass=..." filter
    - Verify font attachment via -attach parameter
    - Verify probe_streams parses ffprobe JSON correctly

  **Must NOT do**:
  - Do not import PySide6
  - Do not call real ffmpeg in unit tests (mock subprocess)
  - Do not hardcode ffmpeg timeouts (use constants)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: ffmpeg command construction is complex (track mapping, disposition, font attachment), and incorrect commands silently produce wrong output
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 7, 8)
  - **Parallel Group**: Wave 3 (with Tasks 7, 8)
  - **Blocks**: Task 11
  - **Blocked By**: Task 2

  **References**:

  **Pattern References**:
  - `/home/joe/sublingo-legacy/src/sublingo/core/muxer.py` — FFmpeg muxing implementation: probe parsing, command construction, subtitle track mapping, font attachment
  - `/mnt/c/Users/Joe/OneDrive/Program/Video-Tools-Suite/scripts/mux.ps1` — Working ffmpeg softsub command: `-map 0:v -map 0:a -map 1:s -map 0:s?` ordering, `-disposition:s:0 default`, `-attach font.ttf -metadata:s:t:0 mimetype=font/ttf`, existing subtitle disposition reset

  **External References**:
  - ffmpeg subtitle docs: https://trac.ffmpeg.org/wiki/HowToBurnSubtitlesIntoVideo — ASS burn-in with `-vf "ass=subtitle.ass"`
  - ffmpeg MKV font attachment: `-attach font.ttf -metadata:s:t:0 mimetype=font/ttf`

  **WHY Each Reference Matters**:
  - VTS mux.ps1 has the EXACT working ffmpeg command for softsub with correct track ordering (this is critical and easy to get wrong)
  - Legacy muxer.py has the Python subprocess pattern for running ffmpeg

  **Acceptance Criteria**:

  ```
  Scenario: FFmpeg tests pass
    Tool: Bash
    Steps:
      1. Run `uv run pytest tests/test_ffmpeg.py -v`
    Expected Result: All tests pass (ffmpeg/ffprobe mocked)
    Evidence: .sisyphus/evidence/task-9-tests.txt

  Scenario: Softsub command is correct
    Tool: Bash
    Steps:
      1. Run `uv run python -c "from sublingo.core.ffmpeg import _build_softsub_cmd; cmd=_build_softsub_cmd(video_path='v.mp4', subtitle_path='s.ass', font_path='f.ttf', output_path='o.mkv', existing_sub_count=2); print(' '.join(cmd))"` (function may be internal, adapt import)
    Expected Result: Command contains `-map 1:s` before `-map 0:s`, `-disposition:s:0 default`, `-attach f.ttf`
    Evidence: .sisyphus/evidence/task-9-softsub-cmd.txt
  ```

  **Commit**: YES
  - Message: `feat(core): implement ffmpeg softsub and hardsub operations`
  - Files: `src/sublingo/core/ffmpeg.py`, `tests/test_ffmpeg.py`
  - Pre-commit: `uv run pytest`

- [x] 10. Translator Module + Tests

  **What to do**:
  - Create `src/sublingo/core/ai_client.py`:
    - `AiClient` class (async, httpx-based):
      - `__init__(self, *, base_url: str, api_key: str, model: str, proxy: str | None = None)` — Create httpx.AsyncClient with `trust_env=True` for proxy support
      - `async translate_batch(self, entries: list[SubtitleEntry], *, target_lang: str, glossary_text: str = "", temperature: float) -> list[str]` — Send batch to LLM, parse response, return translations
      - `async detect_language(self, sample_text: str) -> str` — Detect source language via LLM
      - `async proofread_batch(self, entries: list[BilingualEntry], *, context_entries: list[BilingualEntry], glossary_text: str = "", temperature: float) -> list[str]` — Proofread translations in context
      - `async test_connection(self) -> tuple[bool, str]` — Test API connectivity
      - `async close(self) -> None` — Close httpx client
    - Retry logic: exponential backoff for 429/5xx, max retries from config
    - Request format: OpenAI-compatible chat completions API (works with Gemini/DeepSeek/OpenRouter)
    - System prompt includes: translation instructions, Netflix style rules (Chinese: no commas/periods, single space, 16 chars/line), glossary terms
  - Create `src/sublingo/core/glossary.py`:
    - `load_glossary(path: Path) -> list[tuple[str, str]]` — Load CSV glossary (source,target columns)
    - `format_glossary_for_prompt(entries: list[tuple[str, str]]) -> str` — Format glossary as text for system prompt injection
  - Create `src/sublingo/core/translator.py`:
    - `async translate(subtitle_path: Path, *, target_lang: str, ai_config: AppConfig, glossary_path: Path | None = None, output_dir: Path | None = None, progress: ProgressCallback | None = None) -> TranslateResult` — Full translation pipeline:
      1. Parse input subtitle via subtitle.parse_subtitle()
      2. Detect if auto-generated via subtitle.is_auto_generated()
      3. If auto-generated, segment into sentence-level entries (via LLM segmentation)
      4. Detect source language via ai_client.detect_language()
      5. If source == target, return early with warning
      6. Load glossary if provided, format for prompt
      7. Split entries into batches (batch_size from config)
      8. Translate each batch with ai_client.translate_batch(), report progress (batch N/total)
      9. Proofread each batch with ai_client.proofread_batch()
      10. Generate bilingual ASS via subtitle.generate_bilingual_ass()
      11. Write to `{input_stem}.{target_lang}.ass`
    - Checkpoint support: after each batch, save progress to `{output_dir}/.checkpoint.json` so resume can skip completed batches
  - Create `tests/test_ai_client.py`:
    - Mock httpx to test request construction
    - Verify OpenAI-compatible request format
    - Verify glossary injection in system prompt
    - Verify retry logic on 429
    - Verify temperature settings per operation
  - Create `tests/test_glossary.py`:
    - CSV loading with source,target columns
    - Prompt formatting
  - Create `tests/test_translator.py`:
    - Mock ai_client to test full pipeline orchestration
    - Verify batch splitting
    - Verify checkpoint save/load
    - Verify progress reporting (batch N/M)
    - Verify output file naming
  - IMPORTANT: Keep `ai_client.py` under 400 lines. If needed, split segmentation logic into separate file.

  **Must NOT do**:
  - Do not import PySide6
  - Do not make real API calls in tests
  - Do not implement "smart" glossary matching (full injection only)
  - Do not exceed 400 lines per file

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Most complex module — AI integration, async HTTP, batch processing, checkpoint recovery, multiple sub-steps
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 11 partially, but 11 depends on 10)
  - **Parallel Group**: Wave 4
  - **Blocks**: Task 11
  - **Blocked By**: Tasks 2, 4, 5

  **References**:

  **Pattern References**:
  - `/home/joe/sublingo-legacy/src/sublingo/core/ai_client.py` — Complete AI client implementation: httpx async, OpenAI chat completions format, retry with exponential backoff, segmentation, translation, proofreading. Study request construction and response parsing carefully.
  - `/home/joe/sublingo-legacy/src/sublingo/core/translator.py` — Translation orchestration: pipeline steps, batch splitting, progress reporting
  - `/home/joe/sublingo-legacy/src/sublingo/core/glossary.py` — Glossary loading and formatting
  - `/home/joe/sublingo-legacy/src/sublingo/core/constants.py:8-44` — AI constants: timeouts, temperatures, batch sizes, retry config

  **External References**:
  - OpenAI chat completions API: https://platform.openai.com/docs/api-reference/chat/create — Request/response format
  - Netflix Chinese subtitle rules: no commas/periods, use single space, max 16 chars/line — must be in system prompt

  **WHY Each Reference Matters**:
  - Legacy ai_client.py is the most complex file and has all the proven patterns for LLM interaction
  - Legacy translator.py shows the orchestration pattern (detect → segment → translate → proofread)
  - Netflix rules must be embedded in translation system prompt for quality output

  **Acceptance Criteria**:

  ```
  Scenario: Translator tests pass
    Tool: Bash
    Steps:
      1. Run `uv run pytest tests/test_ai_client.py tests/test_glossary.py tests/test_translator.py -v`
    Expected Result: All tests pass (httpx mocked)
    Evidence: .sisyphus/evidence/task-10-tests.txt

  Scenario: File line counts under 400
    Tool: Bash
    Steps:
      1. Run `wc -l src/sublingo/core/ai_client.py src/sublingo/core/translator.py src/sublingo/core/glossary.py`
    Expected Result: All files under 400 lines
    Evidence: .sisyphus/evidence/task-10-line-count.txt
  ```

  **Commit**: YES
  - Message: `feat(core): implement AI-powered subtitle translator`
  - Files: `src/sublingo/core/ai_client.py`, `src/sublingo/core/translator.py`, `src/sublingo/core/glossary.py`, `tests/test_ai_client.py`, `tests/test_glossary.py`, `tests/test_translator.py`
  - Pre-commit: `uv run pytest`

- [x] 11. Workflow Module + Tests

  **What to do**:
  - Create `src/sublingo/core/workflow.py`:
    - `async run_workflow(url: str, *, config: AppConfig, cookie_file: Path, glossary_dir: Path | None = None, font_dir: Path | None = None, output_dir: Path, progress: ProgressCallback | None = None) -> WorkflowResult` — Full pipeline:
      1. **Download stage**: extract_info → download video + subtitles
      2. **Translate stage**: translate subtitle (if subtitles exist)
      3. **Font stage**: subset font (if translated ASS exists)
      4. **Mux stage**: softsub (if all prerequisites exist)
      5. **Transcript stage**: generate transcript (if config.generate_transcript and subtitle exists)
      - Report stage transitions via progress callback (stage=, stage_status="active"/"done")
      - Each stage checks for existing artifacts (checkpoint recovery)
    - `detect_project_status(project_dir: Path) -> ProjectStatus` — Scan directory for known artifacts to determine progress:
      - has_video: any video file exists
      - has_subtitle: any .vtt/.srt file exists
      - has_translated: any .ass file with target lang in name exists
      - has_font: any .subset.ttf or .{fontname}.ttf exists
      - has_final: any .softsub.mkv exists
      - next_stage: first incomplete stage
    - `async resume_workflow(project_dir: Path, *, config: AppConfig, cookie_file: Path, glossary_dir: Path | None = None, font_dir: Path | None = None, output_dir: Path, progress: ProgressCallback | None = None) -> WorkflowResult` — Resume from detected checkpoint
    - Project directory: `[video_id]{title}/` under output_dir (created by workflow, not downloader)
  - Create `tests/test_workflow.py`:
    - Mock all core modules (downloader, translator, font, ffmpeg, transcript)
    - Verify correct stage ordering
    - Verify stage skip when artifact exists (checkpoint recovery)
    - Verify progress callback reports stage transitions
    - Verify failure in one stage produces correct WorkflowResult
    - Verify resume starts from correct stage

  **Must NOT do**:
  - Do not import PySide6
  - Do not implement batch logic here (batch is GUI-level orchestration)
  - Do not duplicate module logic (workflow only calls other modules)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Orchestration logic with checkpoint recovery, stage management, and error handling across multiple modules
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on all core modules)
  - **Parallel Group**: Wave 4 (after Tasks 4-10 complete)
  - **Blocks**: Tasks 17, 20
  - **Blocked By**: Tasks 4, 5, 6, 7, 8, 9, 10

  **References**:

  **Pattern References**:
  - `/home/joe/sublingo-legacy/src/sublingo/core/workflow.py` — Workflow orchestration: stage sequencing, checkpoint detection via file artifacts, progress stage reporting, error handling with partial results
  - `/mnt/c/Users/Joe/OneDrive/Program/Video-Tools-Suite/scripts/workflow.ps1` — Working full pipeline: download → translate → font → mux ordering, project directory management

  **WHY Each Reference Matters**:
  - Legacy workflow.py has the proven stage-based orchestration with checkpoint recovery
  - VTS workflow.ps1 confirms the correct stage ordering in a working implementation

  **Acceptance Criteria**:

  ```
  Scenario: Workflow tests pass
    Tool: Bash
    Steps:
      1. Run `uv run pytest tests/test_workflow.py -v`
    Expected Result: All tests pass (all core modules mocked)
    Evidence: .sisyphus/evidence/task-11-tests.txt
  ```

  **Commit**: YES
  - Message: `feat(core): implement workflow orchestration with checkpoint recovery`
  - Files: `src/sublingo/core/workflow.py`, `tests/test_workflow.py`
  - Pre-commit: `uv run pytest`

- [x] 12. i18n Infrastructure + Translation Files

  **What to do**:
  - Create `src/sublingo/i18n/` translation infrastructure:
    - Source strings in English (all `self.tr("...")` and `QCoreApplication.translate()` use English)
    - Chinese translation via Qt `.ts` files
  - Create `src/sublingo/gui/i18n_utils.py` (renamed from legacy's misleading `app.py`):
    - `load_translator(app: QCoreApplication, language: str = "auto") -> QTranslator | None` — Load and install translator for given language. "auto" detects system locale.
    - `detect_system_language() -> str` — Detect system locale, return nearest supported language code
    - Language file mapping: `{"en": "sublingo_en.qm", "zh-Hans": "sublingo_zh_Hans.qm"}`
  - Create initial `.ts` translation files:
    - `src/sublingo/i18n/sublingo_en.ts` — English (identity translation since source is English)
    - `src/sublingo/i18n/sublingo_zh_Hans.ts` — Chinese Simplified translations
    - Compile to `.qm` files
  - Document translation workflow: how to add new translatable strings, how to update .ts files

  **Must NOT do**:
  - Do not create .ts files for languages other than en and zh-Hans
  - Do not use Chinese as source language (English is primary)
  - Do not name the utility file `app.py` (legacy naming confusion)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Qt i18n has specific toolchain requirements (lupdate/lrelease or manual .ts editing)
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 10, 11)
  - **Parallel Group**: Wave 4
  - **Blocks**: Tasks 13-16, 19
  - **Blocked By**: Task 1 (needs PySide6 installed)

  **References**:

  **Pattern References**:
  - `/home/joe/sublingo-legacy/src/sublingo/gui/app.py` — i18n utility pattern: load_translator(), detect_system_language(), language file mapping. Note: rename from `app.py` to `i18n_utils.py`
  - `/home/joe/sublingo-legacy/src/sublingo/i18n/` — Reference .ts/.qm files structure

  **WHY Each Reference Matters**:
  - Legacy app.py has the exact Qt translator loading pattern, but needs renaming to avoid confusion
  - Legacy .ts files show the XML structure for Qt translations

  **Acceptance Criteria**:

  ```
  Scenario: i18n module importable
    Tool: Bash
    Steps:
      1. Run `uv run python -c "from sublingo.gui.i18n_utils import load_translator, detect_system_language; print('OK')"`
    Expected Result: "OK"
    Evidence: .sisyphus/evidence/task-12-import.txt

  Scenario: Translation files exist
    Tool: Bash
    Steps:
      1. Run `ls src/sublingo/i18n/*.ts src/sublingo/i18n/*.qm`
    Expected Result: At least sublingo_zh_Hans.ts and sublingo_zh_Hans.qm listed
    Evidence: .sisyphus/evidence/task-12-files.txt
  ```

  **Commit**: YES
  - Message: `feat(i18n): set up Qt translation infrastructure with en+zh-Hans`
  - Files: `src/sublingo/gui/i18n_utils.py`, `src/sublingo/i18n/*.ts`, `src/sublingo/i18n/*.qm`
  - Pre-commit: `uv run pytest`

- [x] 13. GUI Scaffolding + Main Window + Navigation

  **What to do**:
  - Create `src/sublingo/__main__.py`: Entry point that launches QApplication, loads font (LXGWWenKai-Regular for CJK), checks first_run → Setup Wizard or Main Window
  - Create `src/sublingo/gui/main_window.py`: QMainWindow with sidebar navigation (3 buttons: Home, Tasks, Settings) + QStackedWidget content area. Apply LXGWWenKai-Regular as application font for CJK rendering support.
  - Create placeholder pages: `src/sublingo/gui/pages/home.py`, `src/sublingo/gui/pages/tasks.py`, `src/sublingo/gui/pages/settings.py` — each as QWidget with basic layout and translatable title
  - Sidebar: icon-less text buttons (no emoji), visually indicate active page
  - Window: set minimum size, window title "sublingo", default geometry

  **Must NOT do**:
  - Do not implement page content (just placeholders)
  - Do not use emoji anywhere
  - Do not put business logic in GUI files

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: UI layout, navigation patterns, Qt widget composition
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (foundation for all other GUI tasks)
  - **Parallel Group**: Wave 5 (first in wave)
  - **Blocks**: Tasks 14-16, 19, 21
  - **Blocked By**: Tasks 1, 4, 12

  **References**:
  - `/home/joe/sublingo-legacy/src/sublingo/gui/main_window.py` — Main window pattern: QStackedWidget navigation, sidebar, page switching
  - `/home/joe/sublingo-legacy/src/sublingo/__main__.py` — Entry point: QApplication creation, font loading, first-run check

  **Acceptance Criteria**:
  ```
  Scenario: App launches without crash
    Tool: Bash
    Steps:
      1. Run `timeout 10 uv run python -m sublingo --test-launch 2>&1 || true` (add --test-launch flag that quits after window shown)
    Expected Result: No Python traceback in output
    Evidence: .sisyphus/evidence/task-13-launch.txt
  ```

  **Commit**: YES
  - Message: `feat(gui): scaffold main window with sidebar navigation`

- [x] 14. Setup Wizard

  **What to do**:
  - Create `src/sublingo/gui/setup_wizard.py`: QWizard with 3 pages:
    - **Page 1 — Language**: GUI language dropdown (Auto/English/Chinese), target translation language dropdown. GUI language selection immediately switches interface language (call load_translator dynamically).
    - **Page 2 — AI Configuration**: Provider dropdown with presets (Gemini/OpenAI/DeepSeek/OpenRouter/Custom) that auto-fill base_url and model. Fields: base_url, model, api_key (password mode). "Test Connection" button (runs AiClient.test_connection in background thread, shows success/failure).
    - **Page 3 — Other Settings**: Cookie file import (FilePicker + Import button + Validate button with status label), output directory (FilePicker), proxy (text input, placeholder "socks5://127.0.0.1:1080").
  - On wizard completion: save all settings via ConfigManager.save()
  - Wizard appears when ConfigManager.is_first_run is True

  **Must NOT do**:
  - Do not use emoji
  - Do not add more than 3 pages
  - Do not auto-detect proxy or auto-fetch cookies

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Multi-page wizard with dynamic language switching and async connection test
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 15, 16)
  - **Parallel Group**: Wave 5
  - **Blocks**: Task 21
  - **Blocked By**: Tasks 4, 12, 13

  **References**:
  - `/home/joe/sublingo-legacy/src/sublingo/gui/setup_wizard.py` — Complete 544-line wizard implementation: page structure, dynamic language switch, connection test worker, cookie validation
  - `/home/joe/sublingo-legacy/src/sublingo/gui/pages/settings.py:53-63` — AI provider presets dictionary

  **Acceptance Criteria**:
  ```
  Scenario: Wizard completes and saves config
    Tool: Playwright (playwright skill)
    Steps:
      1. Launch app (first run, no config.json)
      2. Verify wizard appears
      3. Select language, click Next
      4. Fill AI fields, click Next
      5. Set output dir, click Finish
      6. Verify config.json created with correct values
    Expected Result: config.json exists with user-set values
    Evidence: .sisyphus/evidence/task-14-wizard-complete.png
  ```

  **Commit**: YES
  - Message: `feat(gui): implement Setup Wizard (language, AI, other settings)`

- [x] 15. Settings Page

  **What to do**:
  - Implement `src/sublingo/gui/pages/settings.py`: Full settings page with grouped sections in QScrollArea:
    - **GUI section**: language dropdown (with immediate switch)
    - **Translation section**: target language dropdown, font file dropdown (scan fonts/ dir), generate transcript checkbox
    - **Cookie section**: status label, import picker + Import button, Validate button
    - **Output section**: project dir picker, output dir picker
    - **AI section**: provider dropdown (with preset auto-fill), base_url, model, api_key (password), batch sizes (QSpinBox), max retries (QSpinBox), Test Connection button
    - **Proxy section**: proxy text input
    - **Maintenance section**: debug mode checkbox, "Reset All Settings" button (deletes config.json, shows restart prompt)
  - Each field has per-field reset button (reset to default value)
  - Auto-save: any field change triggers ConfigManager.save()
  - Load values from ConfigManager on init

  **Must NOT do**:
  - Do not use emoji
  - Do not exceed 400 lines (split into helper widgets if needed)
  - Do not add theme switching, shortcuts, or plugin settings

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Complex form layout with many widget types and auto-save logic
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 14, 16)
  - **Parallel Group**: Wave 5
  - **Blocks**: Task 21
  - **Blocked By**: Tasks 4, 12, 13

  **References**:
  - `/home/joe/sublingo-legacy/src/sublingo/gui/pages/settings.py` — Complete settings page: grouped sections, per-field reset, auto-save, provider presets, connection test worker, cookie validation, debug mode
  - `/home/joe/sublingo-legacy/src/sublingo/gui/widgets/file_picker.py` — File/directory picker widget
  - `/home/joe/sublingo-legacy/src/sublingo/gui/widgets/form_row.py` — Form row with label + widget + reset button

  **Acceptance Criteria**:
  ```
  Scenario: Settings save and reload
    Tool: Playwright (playwright skill)
    Steps:
      1. Launch app, navigate to Settings
      2. Change target language to "en"
      3. Close and relaunch
      4. Verify target language is "en"
    Expected Result: Setting persisted across restart
    Evidence: .sisyphus/evidence/task-15-settings-persist.png
  ```

  **Commit**: YES
  - Message: `feat(gui): implement Settings page with all config sections`

- [x] 16. Home Page -- Task Creation

  **What to do**:
  - Implement `src/sublingo/gui/pages/home.py`: Task creation interface:
    - **URL input**: QTextEdit for multi-line URL input (one URL per line, or playlist URL)
    - **Task type selector**: QComboBox — Full Workflow / Download Only / Translate Only / Softsub Only / Hardsub Only / Transcript Only / Font Subset Only
    - **Dynamic form**: QStackedWidget that shows different options based on task type:
      - Full Workflow: target language (from settings), generate transcript checkbox
      - Download Only: (no extra options, uses settings)
      - Translate Only: subtitle file picker, target language
      - Softsub/Hardsub Only: video file picker, subtitle file picker, font file picker (optional)
      - Transcript Only: subtitle file picker
      - Font Subset Only: subtitle file picker, font file picker
    - **Create Task button**: validates inputs, creates task via TaskManager, switches to Tasks page
    - All fields auto-populated from Settings defaults
  - For batch/playlist: after entering URL and clicking "Preview", show video list in a dialog for user confirmation before creating tasks

  **Must NOT do**:
  - Do not implement task execution logic (that's TaskManager)
  - Do not use emoji

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Dynamic form switching, input validation, preview dialog
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 14, 15)
  - **Parallel Group**: Wave 5
  - **Blocks**: Tasks 20, 21
  - **Blocked By**: Tasks 4, 7, 12, 13

  **References**:
  - `/home/joe/sublingo-legacy/src/sublingo/gui/pages/home.py` — Task creation: URL input, task type selector, dynamic form with QStackedWidget
  - `/mnt/c/Users/Joe/OneDrive/Program/Video-Tools-Suite/scripts/workflow.ps1` — Batch preview logic: extract info for all URLs, display list, confirm before proceeding

  **Acceptance Criteria**:
  ```
  Scenario: Task creation flow
    Tool: Playwright (playwright skill)
    Steps:
      1. Navigate to Home page
      2. Enter a URL
      3. Select "Full Workflow"
      4. Click "Create Task"
      5. Verify automatic switch to Tasks page
    Expected Result: Task appears in task list
    Evidence: .sisyphus/evidence/task-16-create-task.png
  ```

  **Commit**: YES
  - Message: `feat(gui): implement Home page for task creation`

- [x] 17. Task Models + Persistence + TaskManager

  **What to do**:
  - Create `src/sublingo/gui/models/task.py`:
    - `TaskType` enum: WORKFLOW, DOWNLOAD, TRANSLATE, SOFTSUB, HARDSUB, TRANSCRIPT, FONT_SUBSET
    - `TaskStatus` enum: QUEUED, RUNNING, COMPLETED, FAILED
    - `TASK_STAGES` dict: mapping TaskType to list of stage names
    - `TaskInfo` dataclass: id, task_type, params, status, created_at, stages, stage_statuses, current_stage, progress_percent, progress_message, meta, result, error, video_title
    - `TaskManager(QObject)`: centralized lifecycle manager:
      - Signals: task_created, task_started, task_progress, task_log, task_finished, task_failed
      - `create_task(task_type, params) -> str` — create and queue task
      - `_try_run_next()` — start next queued task (FIFO)
      - `_run_task(task_id)` — create worker, connect signals
      - `_on_progress/log/finished/error` — handlers mapping backend callbacks to task state
      - Stage mapping from backend stage names to display stage names
  - Create `src/sublingo/gui/models/task_persistence.py`:
    - `save_tasks(tasks: dict[str, TaskInfo], path: Path) -> None` — Serialize tasks to JSON
    - `load_tasks(path: Path) -> dict[str, TaskInfo]` — Deserialize tasks from JSON
    - Save on every state change, load on app startup
  - Create `tests/test_task_model.py`:
    - TaskInfo state transitions
    - TaskManager create/queue/run lifecycle
    - Persistence round-trip

  **Must NOT do**:
  - Do not use SQLite (JSON files only)
  - Do not implement task priority or pause/resume

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: State machine logic, signal wiring, persistence serialization
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 13-16)
  - **Parallel Group**: Wave 5
  - **Blocks**: Tasks 18, 19, 20
  - **Blocked By**: Tasks 2, 4, 11

  **References**:
  - `/home/joe/sublingo-legacy/src/sublingo/gui/models/task.py` — Complete TaskInfo, TaskType, TaskStatus, TaskManager implementation with signal-based lifecycle management and backend stage mapping

  **Acceptance Criteria**:
  ```
  Scenario: Task model tests pass
    Tool: Bash
    Steps:
      1. Run `uv run pytest tests/test_task_model.py -v`
    Expected Result: All tests pass
    Evidence: .sisyphus/evidence/task-17-tests.txt
  ```

  **Commit**: YES
  - Message: `feat(gui): implement task models, persistence, and TaskManager`

- [x] 18. Workers (TaskWorker + AsyncTaskWorker + WorkerCallback)

  **What to do**:
  - Create `src/sublingo/gui/workers/task_worker.py`:
    - `WorkerCallback` class: bridges ProgressCallback protocol to Qt Signals. Has `on_progress(current, total, message, **meta)` that emits `progress_signal(current, total, message, meta_dict)` and `on_log(level, message, detail)` that emits `log_signal(level, message, detail)`.
    - `TaskWorker(QThread)`: runs synchronous task function on background thread. Signals: progress, log, finished, error.
    - `AsyncTaskWorker(QThread)`: runs async task function via `asyncio.run()` on background thread. Same signals.
    - Both workers create WorkerCallback and pass to task function as `progress=callback`.
  - Create `tests/test_workers.py`:
    - WorkerCallback correctly bridges protocol to signals
    - TaskWorker runs sync function and emits finished
    - AsyncTaskWorker runs async function and emits finished
    - Error handling: exception → error signal

  **Must NOT do**:
  - Do not put business logic in workers
  - Do not use qasync (asyncio.run in QThread is sufficient, proven in legacy)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Qt thread + signal patterns, async bridging
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Task 17)
  - **Parallel Group**: Wave 5
  - **Blocks**: Tasks 19, 20
  - **Blocked By**: Tasks 2, 17

  **References**:
  - `/home/joe/sublingo-legacy/src/sublingo/gui/workers/task_worker.py` — Exact implementation: WorkerCallback, TaskWorker, AsyncTaskWorker pattern

  **Acceptance Criteria**:
  ```
  Scenario: Worker tests pass
    Tool: Bash
    Steps:
      1. Run `uv run pytest tests/test_workers.py -v`
    Expected Result: All tests pass
    Evidence: .sisyphus/evidence/task-18-tests.txt
  ```

  **Commit**: YES
  - Message: `feat(gui): implement TaskWorker, AsyncTaskWorker, WorkerCallback`

- [x] 19. Tasks Page -- Monitoring + Stepper + Details

  **What to do**:
  - Implement `src/sublingo/gui/pages/tasks.py`: Task monitoring interface:
    - **Task list** (left panel or top): QListWidget/QListView showing all tasks with: video title/URL, type label, status text, progress bar, thumbnail (if available)
    - **Task detail** (right panel or bottom, shown on task selection):
      - Video info card: thumbnail (large), title, channel, duration, upload date, video ID
      - Stepper widget: horizontal steps showing pipeline stages, each with status indicator (pending/active/done/error — use symbols like filled/empty circles, checkmarks, X marks — NO EMOJI)
      - Stage detail area: shows current stage's specific info (download speed/ETA, translation batch progress, font stats, etc.)
      - Log panel: collapsible, scrollable, color-coded by level (info=default, warning=yellow, error=red). Debug messages only shown when debug_mode is True.
    - **"Continue" button**: visible for failed tasks, calls resume_workflow
    - Connect to TaskManager signals for real-time updates
  - Create `src/sublingo/gui/widgets/stepper.py`: Reusable stepper widget showing multi-step progress
  - Create `src/sublingo/gui/widgets/log_viewer.py`: Log display widget with level filtering

  **Must NOT do**:
  - Do not use emoji for status indicators
  - Do not implement video player or preview
  - Do not exceed 400 lines per file

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Complex UI composition — list/detail split, stepper widget, real-time updates, log viewer
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (needs Task 17, 18 for task management)
  - **Parallel Group**: Wave 5 (after 17, 18)
  - **Blocks**: Tasks 20, 21
  - **Blocked By**: Tasks 12, 13, 17, 18

  **References**:
  - `/home/joe/sublingo-legacy/src/sublingo/gui/pages/task_list.py` — Task list UI pattern
  - `/home/joe/sublingo-legacy/src/sublingo/gui/widgets/stepper.py` — Stepper widget implementation
  - `/home/joe/sublingo-legacy/src/sublingo/gui/widgets/log_viewer.py` — Log viewer widget
  - `/home/joe/sublingo-legacy/src/sublingo/gui/widgets/progress.py` — Progress display widget

  **Acceptance Criteria**:
  ```
  Scenario: Tasks page shows created task
    Tool: Playwright (playwright skill)
    Steps:
      1. Create a task from Home page
      2. Verify Tasks page shows the task
      3. Verify stepper shows correct stages for task type
      4. Verify status text updates
    Expected Result: Task visible with stepper and status
    Evidence: .sisyphus/evidence/task-19-tasks-page.png
  ```

  **Commit**: YES
  - Message: `feat(gui): implement Tasks page with stepper and detail views`

- [x] 20. Batch Processing Integration

  **What to do**:
  - Add batch processing support to Home page and TaskManager:
    - When user enters multiple URLs or a playlist URL:
      1. Show "Preview" button (alongside "Create Task")
      2. On Preview click: run extract_info for each URL (or extract_playlist_info for playlist) in background worker
      3. Show preview dialog: QDialog with QTableWidget listing video titles, durations, subtitle availability
      4. User can check/uncheck videos to include
      5. On confirm: create one task per video, all queued in TaskManager
    - TaskManager batch handling: sequential execution (FIFO queue), but user sees all tasks in list
    - Rate limiting consideration: add configurable delay between tasks (`batch_delay_seconds` in config, default 0)
    - LLM rate limiting: translator module already handles retry with backoff; batch just runs tasks sequentially
  - Batch progress in Tasks page: show "Batch: 3/10 completed" summary at top when multiple tasks exist

  **Must NOT do**:
  - Do not implement parallel LLM translation (sequential only, rate limiting)
  - Do not implement task priority

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Async preview loading, playlist expansion, dialog UI, queue management integration
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (needs Home page + TaskManager + Tasks page)
  - **Parallel Group**: Wave 5 (late)
  - **Blocks**: Task 21
  - **Blocked By**: Tasks 7, 16, 17, 19

  **References**:
  - `/mnt/c/Users/Joe/OneDrive/Program/Video-Tools-Suite/scripts/workflow.ps1` — Batch processing: playlist expansion, video list preview, parallel download + sequential translate

  **Acceptance Criteria**:
  ```
  Scenario: Batch preview shows video list
    Tool: Playwright (playwright skill)
    Steps:
      1. Enter 2 URLs in Home page
      2. Click Preview
      3. Verify dialog shows 2 videos with titles
      4. Confirm, verify 2 tasks created
    Expected Result: Preview dialog displays correctly, 2 tasks in queue
    Evidence: .sisyphus/evidence/task-20-batch-preview.png
  ```

  **Commit**: YES
  - Message: `feat(gui): integrate batch processing with preview and rate limiting`

- [x] 21. GUI Smoke Tests

  **What to do**:
  - Create `tests/test_gui_smoke.py`:
    - Use `pytest-qt` with `qtbot` fixture
    - Test: app launches without crash (QApplication + MainWindow)
    - Test: 3 pages are accessible via navigation
    - Test: Setup Wizard pages can be traversed
    - Test: Settings page loads and displays all sections
    - Test: Home page task type selector changes form
    - All tests use mocked core modules (no network, no ffmpeg)
  - Create `tests/conftest.py` additions:
    - Session-scoped `qapp` fixture for PySide6
    - Mock fixtures for core modules

  **Must NOT do**:
  - Do not test actual video download or translation
  - Do not require network access

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Qt testing patterns with pytest-qt, mock setup
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (needs all GUI tasks complete)
  - **Parallel Group**: Wave 5 (final)
  - **Blocks**: FINAL wave
  - **Blocked By**: Tasks 13-20

  **References**:
  - `/home/joe/sublingo-legacy/tests/` — Test structure and Qt testing patterns with session-scoped qapp fixture

  **Acceptance Criteria**:
  ```
  Scenario: All GUI smoke tests pass
    Tool: Bash
    Steps:
      1. Run `uv run pytest tests/test_gui_smoke.py -v`
    Expected Result: All tests pass
    Evidence: .sisyphus/evidence/task-21-smoke-tests.txt
  ```

  **Commit**: YES
  - Message: `test(gui): add GUI smoke tests for all pages and wizard`

---

## Final Verification Wave

- [ ] F1. **Plan Compliance Audit** -- `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run command). For each "Must NOT Have": search codebase for forbidden patterns -- reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** -- `unspecified-high`
  Run `uv run pytest`. Review all changed files for: `as any`, empty catches, print() in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names (data/result/item/temp). Verify single-file 400-line limit. Verify no PySide6 import in core/.
  Output: `Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real Manual QA** -- `unspecified-high` (+ `playwright` skill)
  Start from clean state. Launch GUI via `uv run python -m sublingo`. Complete Setup Wizard. Navigate all 3 pages. Create a task (mock or real). Verify Settings save/load. Test debug mode toggle. Verify i18n switching. Save screenshots to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [ ] F4. **Scope Fidelity Check** -- `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 -- everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Detect cross-task contamination. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **T1**: `chore(project): scaffold project structure and update dependency rules`
- **T2**: `feat(core): add data models, constants, and ProgressCallback protocol`
- **T3**: `chore(assets): add fonts and example glossary`
- **T4**: `feat(core): implement config module with ConfigManager`
- **T5**: `feat(core): implement subtitle parsing and ASS generation`
- **T6**: `feat(core): implement transcript generation from subtitles`
- **T7**: `feat(core): implement yt-dlp downloader module`
- **T8**: `feat(core): implement font subsetting module`
- **T9**: `feat(core): implement ffmpeg softsub and hardsub operations`
- **T10**: `feat(core): implement AI-powered subtitle translator`
- **T11**: `feat(core): implement workflow orchestration with checkpoint recovery`
- **T12**: `feat(i18n): set up Qt translation infrastructure with en+zh-Hans`
- **T13**: `feat(gui): scaffold main window with sidebar navigation`
- **T14**: `feat(gui): implement Setup Wizard (language, AI, other settings)`
- **T15**: `feat(gui): implement Settings page with all config sections`
- **T16**: `feat(gui): implement Home page for task creation`
- **T17**: `feat(gui): implement task models, persistence, and TaskManager`
- **T18**: `feat(gui): implement TaskWorker, AsyncTaskWorker, WorkerCallback`
- **T19**: `feat(gui): implement Tasks page with stepper and detail views`
- **T20**: `feat(gui): integrate batch processing with preview and rate limiting`
- **T21**: `test(gui): add GUI smoke tests for all pages and wizard`

---

## Success Criteria

### Verification Commands
```bash
uv run pytest                           # Expected: all tests pass
uv run pytest --tb=short -q             # Expected: N passed, 0 failed
uv run python -m sublingo               # Expected: GUI launches without crash
ast_grep_search "import PySide6" in src/sublingo/core/  # Expected: 0 matches
```

### Final Checklist
- [ ] All "Must Have" items present and verified
- [ ] All "Must NOT Have" items absent (verified by search)
- [ ] All core module tests pass
- [ ] GUI launches and all pages accessible
- [ ] Setup Wizard completes on first run
- [ ] Settings save/load/reset work correctly
- [ ] Debug mode toggles log granularity
- [ ] i18n switches between English and Chinese
- [ ] Single file line count <= 400 for all files
