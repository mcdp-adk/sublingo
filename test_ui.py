import sys
import os
from PySide6.QtWidgets import QApplication
from sublingo.gui.pages.tasks import TasksPage
from sublingo.gui.models.task import TaskManager


def main():
    app = QApplication(sys.argv)

    # Create dummy TaskManager
    task_mgr = TaskManager()

    # Create TasksPage
    page = TasksPage(task_mgr)
    page.resize(800, 600)
    page.show()

    # Add some dummy tasks
    class DummyTask:
        def __init__(self, id, title, status, pct, stages, stage_statuses):
            self.id = id
            self.video_title = title
            self.task_type = "workflow"
            self.status_summary = status
            self.progress_percent = pct
            self.stages = stages
            self.stage_statuses = stage_statuses
            self.progress_message = "Downloading..."
            self.status = "RUNNING"
            self.channel = "Test Channel"
            self.duration = "10:00"
            self.upload_date = "2023-01-01"
            self.video_id = "test_id"

    task1 = DummyTask(
        "1",
        "Test Video 1",
        "Running",
        50,
        ["download", "translate", "mux"],
        {"download": "done", "translate": "active", "mux": "pending"},
    )
    task2 = DummyTask(
        "2",
        "Test Video 2",
        "Failed",
        0,
        ["download", "translate", "mux"],
        {"download": "error", "translate": "pending", "mux": "pending"},
    )
    task2.status = "FAILED"

    # Mock get_task
    task_mgr.get_task = lambda tid: task1 if tid == "1" else task2
    task_mgr.task_order = ["1", "2"]

    page._refresh_list()

    # Select first task
    page.task_list.setCurrentRow(0)

    # Ensure directory exists
    os.makedirs(".sisyphus/evidence", exist_ok=True)

    # Take screenshot
    pixmap = page.grab()
    pixmap.save(".sisyphus/evidence/task-19-tasks.png")

    print("Screenshot saved to .sisyphus/evidence/task-19-tasks.png")

    # Save evidence text
    with open(".sisyphus/evidence/task-19-evidence.txt", "w") as f:
        f.write("Tasks page implemented and screenshot taken.\n")


if __name__ == "__main__":
    main()
