"""Background thread workers that bridge task functions to the Qt signal system.

:class:`WorkerCallback` adapts the :class:`~sublingo.core.models.ProgressCallback`
protocol into Qt signals so that any long-running task can report progress and
log messages back to the GUI thread in a thread-safe manner.

:class:`TaskWorker` runs a **synchronous** callable, while
:class:`AsyncTaskWorker` runs an **async** callable via :func:`asyncio.run`.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Protocol

from PySide6.QtCore import QThread, Signal


# ---------------------------------------------------------------------------
# Internal protocol for signal duck-typing
# ---------------------------------------------------------------------------


class _QtSignalEmitter(Protocol):
    """Minimal protocol matching a bound Qt signal's ``emit`` method."""

    def emit(self, *args: Any) -> None: ...


# ---------------------------------------------------------------------------
# WorkerCallback -- bridges ProgressCallback protocol to Qt Signals
# ---------------------------------------------------------------------------


class WorkerCallback:
    """Bridges the :class:`~sublingo.core.models.ProgressCallback` protocol to Qt Signals.

    The *progress_signal* carries ``(current, total, message, meta)`` where
    *meta* is a :class:`dict` with optional keys such as ``speed``, ``eta``,
    ``stage``, ``stage_status``, ``batch``, and ``total_batches``.

    The *log_signal* carries ``(level, message, detail)`` where *detail* is a
    string that may contain verbose information like a traceback.
    """

    def __init__(
        self, progress_signal: _QtSignalEmitter, log_signal: _QtSignalEmitter
    ) -> None:
        self.progress_signal = progress_signal
        self.log_signal = log_signal

    def on_progress(
        self, current: int, total: int, message: str = "", **meta: Any
    ) -> None:
        """Emit progress data as a Qt signal.

        Args:
            current: Current progress value.
            total: Total progress value.
            message: Optional message describing current state.
            **meta: Additional metadata forwarded as a dict.
        """
        self.progress_signal.emit(current, total, message, meta)

    def on_log(self, level: str, message: str, detail: str = "") -> None:
        """Emit a log entry as a Qt signal.

        Args:
            level: Log level (debug, info, warning, error).
            message: Log message.
            detail: Optional detailed information.
        """
        self.log_signal.emit(level, message, detail)


# ---------------------------------------------------------------------------
# TaskWorker -- synchronous background thread
# ---------------------------------------------------------------------------


class TaskWorker(QThread):
    """Run a synchronous *task_fn* on a background :class:`QThread`.

    Signals
    -------
    progress(current, total, message, meta)
        Emitted by the task function via :class:`WorkerCallback`.
    log(level, message, detail)
        Emitted by the task function via :class:`WorkerCallback`.
    finished(result)
        Emitted when the task function returns.
    error(exception)
        Emitted when the task function raises an exception.
    """

    progress = Signal(int, int, str, dict)
    log = Signal(str, str, str)
    finished = Signal(object)
    error = Signal(Exception)

    def __init__(
        self,
        task_fn: Callable[..., Any],
        task_input: Any,
        parent: QThread | None = None,
    ) -> None:
        super().__init__(parent)
        self.task_fn = task_fn
        self.task_input = task_input

    def run(self) -> None:  # noqa: D401
        """Thread entry point -- executes the task function."""
        try:
            callback = WorkerCallback(self.progress, self.log)
            result = self.task_fn(self.task_input, progress=callback)
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(exc)


# ---------------------------------------------------------------------------
# AsyncTaskWorker -- async background thread
# ---------------------------------------------------------------------------


class AsyncTaskWorker(QThread):
    """Same as :class:`TaskWorker` but runs an **async** function via :func:`asyncio.run`.

    This is intended for coroutine-based tasks like ``translate()`` and
    ``run_workflow()``.
    """

    progress = Signal(int, int, str, dict)
    log = Signal(str, str, str)
    finished = Signal(object)
    error = Signal(Exception)

    def __init__(
        self,
        task_fn: Callable[..., Any],
        task_input: Any,
        parent: QThread | None = None,
    ) -> None:
        super().__init__(parent)
        self.task_fn = task_fn
        self.task_input = task_input

    def run(self) -> None:  # noqa: D401
        """Thread entry point -- executes the async task function."""
        try:
            callback = WorkerCallback(self.progress, self.log)
            result = asyncio.run(self.task_fn(self.task_input, progress=callback))
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(exc)
