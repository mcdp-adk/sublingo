"""Tests for sublingo.gui.workers.task_worker module.

Covers WorkerCallback signal bridging, TaskWorker sync execution,
AsyncTaskWorker async execution, and error propagation.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QCoreApplication, QThread, Signal, SignalInstance

from sublingo.core.models import ProgressCallback
from sublingo.gui.workers.task_worker import (
    AsyncTaskWorker,
    TaskWorker,
    WorkerCallback,
)

# ---------------------------------------------------------------------------
# QCoreApplication singleton -- required for Qt event loop in tests
# ---------------------------------------------------------------------------

_app: QCoreApplication | None = None


def _ensure_qapp() -> QCoreApplication:
    """Return existing or create a new QCoreApplication instance."""
    global _app  # noqa: PLW0603
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
        _app = app
    return app


@pytest.fixture(scope="session", autouse=True)
def qapp() -> QCoreApplication:
    """Session-scoped QCoreApplication fixture."""
    return _ensure_qapp()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

WAIT_TIMEOUT_MS = 5000


def _wait_for_thread(worker: QThread) -> None:
    """Block until *worker* finishes, then process pending cross-thread signals."""
    finished = worker.wait(WAIT_TIMEOUT_MS)
    assert finished, "Worker thread did not finish within timeout"
    # Cross-thread signal delivery uses Qt::QueuedConnection, so we must
    # process pending events for the slots to actually execute.
    app = QCoreApplication.instance()
    if app is not None:
        app.processEvents()


# ---------------------------------------------------------------------------
# WorkerCallback tests
# ---------------------------------------------------------------------------


class TestWorkerCallback:
    """WorkerCallback correctly bridges protocol to signals."""

    def test_on_progress_emits_signal(self) -> None:
        mock_progress = MagicMock()
        mock_log = MagicMock()
        cb = WorkerCallback(mock_progress, mock_log)

        cb.on_progress(5, 100, "downloading", speed=1024, eta=30)

        mock_progress.emit.assert_called_once_with(
            5, 100, "downloading", {"speed": 1024, "eta": 30}
        )

    def test_on_progress_default_message(self) -> None:
        mock_progress = MagicMock()
        mock_log = MagicMock()
        cb = WorkerCallback(mock_progress, mock_log)

        cb.on_progress(0, 10)

        mock_progress.emit.assert_called_once_with(0, 10, "", {})

    def test_on_log_emits_signal(self) -> None:
        mock_progress = MagicMock()
        mock_log = MagicMock()
        cb = WorkerCallback(mock_progress, mock_log)

        cb.on_log("warning", "rate limited", "retry in 5s")

        mock_log.emit.assert_called_once_with("warning", "rate limited", "retry in 5s")

    def test_on_log_default_detail(self) -> None:
        mock_progress = MagicMock()
        mock_log = MagicMock()
        cb = WorkerCallback(mock_progress, mock_log)

        cb.on_log("info", "started")

        mock_log.emit.assert_called_once_with("info", "started", "")

    def test_satisfies_progress_callback_protocol(self) -> None:
        mock_progress = MagicMock()
        mock_log = MagicMock()
        cb = WorkerCallback(mock_progress, mock_log)

        assert isinstance(cb, ProgressCallback)


# ---------------------------------------------------------------------------
# TaskWorker tests
# ---------------------------------------------------------------------------

SENTINEL_RESULT = "sync_task_done"


def _sync_task(task_input: str, progress: Any = None) -> str:
    """Dummy sync task that uses the callback and returns a result."""
    if progress is not None:
        progress.on_progress(0, 1, "starting")
        progress.on_log("info", "running sync task")
        progress.on_progress(1, 1, "done")
    return f"{task_input}_{SENTINEL_RESULT}"


def _sync_task_error(task_input: str, progress: Any = None) -> str:
    """Dummy sync task that always raises."""
    raise ValueError(f"sync fail: {task_input}")


class TestTaskWorker:
    """TaskWorker runs sync function and emits finished."""

    def test_finished_signal_emitted(self) -> None:
        results: list[Any] = []
        worker = TaskWorker(_sync_task, "hello")
        worker.finished.connect(results.append)

        worker.start()
        _wait_for_thread(worker)

        assert len(results) == 1
        assert results[0] == "hello_sync_task_done"

    def test_progress_signal_emitted(self) -> None:
        progress_calls: list[tuple[int, int, str, dict[str, Any]]] = []
        worker = TaskWorker(_sync_task, "data")
        worker.progress.connect(
            lambda c, t, m, meta: progress_calls.append((c, t, m, meta))
        )

        worker.start()
        _wait_for_thread(worker)

        assert len(progress_calls) == 2
        assert progress_calls[0] == (0, 1, "starting", {})
        assert progress_calls[1] == (1, 1, "done", {})

    def test_log_signal_emitted(self) -> None:
        log_calls: list[tuple[str, str, str]] = []
        worker = TaskWorker(_sync_task, "data")
        worker.log.connect(lambda lvl, msg, det: log_calls.append((lvl, msg, det)))

        worker.start()
        _wait_for_thread(worker)

        assert len(log_calls) == 1
        assert log_calls[0] == ("info", "running sync task", "")

    def test_error_signal_on_exception(self) -> None:
        errors: list[Exception] = []
        results: list[Any] = []
        worker = TaskWorker(_sync_task_error, "oops")
        worker.error.connect(errors.append)
        worker.finished.connect(results.append)

        worker.start()
        _wait_for_thread(worker)

        assert len(errors) == 1
        assert isinstance(errors[0], ValueError)
        assert "sync fail: oops" in str(errors[0])
        assert len(results) == 0

    def test_stores_task_fn_and_input(self) -> None:
        worker = TaskWorker(_sync_task, "input_val")
        assert worker.task_fn is _sync_task
        assert worker.task_input == "input_val"


# ---------------------------------------------------------------------------
# AsyncTaskWorker tests
# ---------------------------------------------------------------------------

ASYNC_SENTINEL = "async_task_done"


async def _async_task(task_input: str, progress: Any = None) -> str:
    """Dummy async task that uses the callback and returns a result."""
    if progress is not None:
        progress.on_progress(0, 1, "async starting")
        progress.on_log("info", "running async task")
        progress.on_progress(1, 1, "async done")
    await asyncio.sleep(0)  # yield to event loop at least once
    return f"{task_input}_{ASYNC_SENTINEL}"


async def _async_task_error(task_input: str, progress: Any = None) -> str:
    """Dummy async task that always raises."""
    await asyncio.sleep(0)
    raise RuntimeError(f"async fail: {task_input}")


class TestAsyncTaskWorker:
    """AsyncTaskWorker runs async function and emits finished."""

    def test_finished_signal_emitted(self) -> None:
        results: list[Any] = []
        worker = AsyncTaskWorker(_async_task, "world")
        worker.finished.connect(results.append)

        worker.start()
        _wait_for_thread(worker)

        assert len(results) == 1
        assert results[0] == "world_async_task_done"

    def test_progress_signal_emitted(self) -> None:
        progress_calls: list[tuple[int, int, str, dict[str, Any]]] = []
        worker = AsyncTaskWorker(_async_task, "data")
        worker.progress.connect(
            lambda c, t, m, meta: progress_calls.append((c, t, m, meta))
        )

        worker.start()
        _wait_for_thread(worker)

        assert len(progress_calls) == 2
        assert progress_calls[0] == (0, 1, "async starting", {})
        assert progress_calls[1] == (1, 1, "async done", {})

    def test_log_signal_emitted(self) -> None:
        log_calls: list[tuple[str, str, str]] = []
        worker = AsyncTaskWorker(_async_task, "data")
        worker.log.connect(lambda lvl, msg, det: log_calls.append((lvl, msg, det)))

        worker.start()
        _wait_for_thread(worker)

        assert len(log_calls) == 1
        assert log_calls[0] == ("info", "running async task", "")

    def test_error_signal_on_exception(self) -> None:
        errors: list[Exception] = []
        results: list[Any] = []
        worker = AsyncTaskWorker(_async_task_error, "bad")
        worker.error.connect(errors.append)
        worker.finished.connect(results.append)

        worker.start()
        _wait_for_thread(worker)

        assert len(errors) == 1
        assert isinstance(errors[0], RuntimeError)
        assert "async fail: bad" in str(errors[0])
        assert len(results) == 0

    def test_stores_task_fn_and_input(self) -> None:
        worker = AsyncTaskWorker(_async_task, "input_val")
        assert worker.task_fn is _async_task
        assert worker.task_input == "input_val"
