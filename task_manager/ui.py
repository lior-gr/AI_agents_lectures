"""PySide6 UI for submitting goals and viewing live agent progress.

Separation of concerns:
- UI layer renders widgets, collects input, and displays backend output/events.
- Business logic remains in backend functions injected from `main.py`.
- Agent/OpenAI/MCP/storage logic is not implemented in this file.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class QtWindowRunner:
    """Compatibility wrapper that preserves `main.py` launch contract."""

    def __init__(self, app: QApplication, window: QWidget) -> None:
        self._app = app
        self._window = window

    def mainloop(self) -> int:
        """Run Qt event loop and return process exit code."""
        self._window.show()
        return self._app.exec()


class GoalWorker(QObject):
    """Background worker that runs backend goal execution off the UI thread."""

    progress_event = Signal(dict)
    completed = Signal(str)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, submit_goal: Callable[..., str], goal: str) -> None:
        super().__init__()
        self._submit_goal = submit_goal
        self._goal = goal

    @Slot()
    def run(self) -> None:
        """Execute backend callback and stream events."""
        try:
            def on_event(event: dict) -> None:
                self.progress_event.emit(event)

            result = self._submit_goal(self._goal, on_event=on_event)
            self.completed.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()


def _make_table_item(text: str) -> QTableWidgetItem:
    return QTableWidgetItem(text)


class UiController(QObject):
    """Main-thread controller for safe UI updates from worker signals."""

    def __init__(
        self,
        submit_goal: Callable[..., str],
        goal_input: QLineEdit,
        submit_button: QPushButton,
        output_box: QTextEdit,
        progress_table: QTableWidget,
    ) -> None:
        super().__init__()
        self._submit_goal = submit_goal
        self._goal_input = goal_input
        self._submit_button = submit_button
        self._output_box = output_box
        self._progress_table = progress_table
        self._sequence = 0
        self._thread: QThread | None = None
        self._worker: GoalWorker | None = None

    def _set_busy(self, is_busy: bool) -> None:
        self._submit_button.setEnabled(not is_busy)
        self._goal_input.setEnabled(not is_busy)

    def _start_worker(self, goal: str) -> None:
        """Start backend call in a worker thread so UI remains responsive."""
        thread = QThread(self)
        worker = GoalWorker(self._submit_goal, goal)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.progress_event.connect(self.on_progress_event)
        worker.completed.connect(self.on_worker_completed)
        worker.failed.connect(self.on_worker_failed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self.on_worker_finished)

        self._thread = thread
        self._worker = worker
        thread.start()

    @Slot(dict)
    def on_progress_event(self, event: dict) -> None:
        """Append one backend instrumentation event in chronological order."""
        self._sequence += 1
        sequence = str(self._sequence)
        timestamp = str(event.get("timestamp", ""))
        event_type = str(event.get("type", ""))
        name = str(event.get("name", ""))
        details = str(event.get("details", ""))
        step = event.get("step")
        if step is not None:
            details = f"step={step} | {details}" if details else f"step={step}"

        row = self._progress_table.rowCount()
        self._progress_table.insertRow(row)
        self._progress_table.setItem(row, 0, _make_table_item(sequence))
        self._progress_table.setItem(row, 1, _make_table_item(timestamp))
        self._progress_table.setItem(row, 2, _make_table_item(event_type))
        self._progress_table.setItem(row, 3, _make_table_item(name))
        self._progress_table.setItem(row, 4, _make_table_item(details))
        self._progress_table.scrollToBottom()

    @Slot(str)
    def on_worker_completed(self, result: str) -> None:
        self._output_box.setPlainText(result)

    @Slot(str)
    def on_worker_failed(self, error_text: str) -> None:
        self._output_box.setPlainText(f"UI worker failed: {error_text}")

    @Slot()
    def on_worker_finished(self) -> None:
        self._set_busy(False)
        self._thread = None
        self._worker = None

    @Slot()
    def on_submit(self) -> None:
        """Submit click handler: invoke backend and render streamed progress."""
        if self._thread is not None and self._thread.isRunning():
            return

        goal = self._goal_input.text().strip()
        self._output_box.clear()
        self._progress_table.setRowCount(0)
        self._sequence = 0

        if not goal:
            self._output_box.setPlainText("Please enter a non-empty goal.")
            return

        self._set_busy(True)
        self._start_worker(goal)


def create_window(submit_goal: Callable[..., str]) -> QtWindowRunner:
    """Create and configure the PySide6 UI window.

    Backend interface stays identical at integration boundary:
    - UI calls injected `submit_goal(...)`
    - UI does not import/execute agent logic directly
    """
    app = QApplication.instance() or QApplication([])

    window = QWidget()
    window.setWindowTitle("Task Manager UI")
    window.resize(1100, 560)

    root_layout = QVBoxLayout()
    window.setLayout(root_layout)

    splitter = QSplitter()
    root_layout.addWidget(splitter)

    # Left panel: input + final output text.
    left_panel = QWidget()
    left_layout = QVBoxLayout()
    left_panel.setLayout(left_layout)
    splitter.addWidget(left_panel)

    input_label = QLabel("Goal")
    left_layout.addWidget(input_label)

    input_row = QHBoxLayout()
    goal_input = QLineEdit()
    submit_button = QPushButton("Submit")
    input_row.addWidget(goal_input)
    input_row.addWidget(submit_button)
    left_layout.addLayout(input_row)

    output_label = QLabel("Output")
    left_layout.addWidget(output_label)

    output_box = QTextEdit()
    output_box.setReadOnly(True)
    left_layout.addWidget(output_box)

    # Right panel: live ordered progress events (skills/tools/steps/timestamps).
    right_panel = QWidget()
    right_layout = QVBoxLayout()
    right_panel.setLayout(right_layout)
    splitter.addWidget(right_panel)

    progress_label = QLabel("Agent Progress")
    right_layout.addWidget(progress_label)

    progress_table = QTableWidget(0, 5)
    progress_table.setHorizontalHeaderLabels(["#", "Time", "Type", "Name", "Details"])
    progress_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
    progress_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
    progress_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
    progress_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
    progress_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
    progress_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    progress_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    progress_table.setSelectionMode(QAbstractItemView.SingleSelection)
    right_layout.addWidget(progress_table)

    splitter.setSizes([700, 400])

    # Monospace font is required for aligned text (e.g., ASCII tables).
    fixed_font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
    output_box.setFont(fixed_font)
    progress_table.setFont(fixed_font)

    controller = UiController(
        submit_goal=submit_goal,
        goal_input=goal_input,
        submit_button=submit_button,
        output_box=output_box,
        progress_table=progress_table,
    )

    submit_button.clicked.connect(controller.on_submit)
    goal_input.returnPressed.connect(controller.on_submit)

    # Keep controller alive for the full window lifetime.
    window._controller = controller  # type: ignore[attr-defined]

    return QtWindowRunner(app, window)
