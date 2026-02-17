"""PySide6 UI boundary for the task manager.

This module handles user interaction and visualization only.
It calls shared backend functions for goal execution and does not own agent/MCP/storage logic.
"""

from __future__ import annotations

import traceback
from datetime import datetime
from typing import Any, Callable

try:
    from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QPlainTextEdit,
        QSplitter,
        QStackedWidget,
        QTableWidget,
        QTableWidgetItem,
        QTreeWidget,
        QTreeWidgetItem,
        QVBoxLayout,
        QWidget,
    )
except ImportError:  # pragma: no cover - exercised only when GUI dependencies missing.
    QObject = object  # type: ignore[assignment]
    Signal = None  # type: ignore[assignment]
    Slot = lambda *args, **kwargs: (lambda func: func)  # type: ignore[assignment]
    QApplication = None  # type: ignore[assignment]


_EVENT_COLORS = {
    "step": QColor("#e0f2fe") if QApplication else None,
    "tool": QColor("#ecfccb") if QApplication else None,
    "skill": QColor("#fce7f3") if QApplication else None,
    "skill_route": QColor("#e9d5ff") if QApplication else None,
    "validation": QColor("#fef9c3") if QApplication else None,
    "stop": QColor("#cffafe") if QApplication else None,
    "error": QColor("#fee2e2") if QApplication else None,
    "lifecycle": QColor("#ede9fe") if QApplication else None,
}


if QApplication is not None:

    class AgentWorker(QObject):
        """Background worker that runs goal execution without blocking the UI thread."""

        progress = Signal(dict)
        finished = Signal(str)
        failed = Signal(str)

        def __init__(self, run_goal_fn: Callable[..., str], goal: str) -> None:
            super().__init__()
            self._run_goal_fn = run_goal_fn
            self._goal = goal

        @Slot()
        def run(self) -> None:
            try:
                result = self._run_goal_fn(self._goal, progress_callback=self._on_progress)
                self.finished.emit(result)
            except Exception as exc:  # pragma: no cover - depends on runtime backend behavior.
                detail = f"{exc}\n{traceback.format_exc(limit=3)}"
                self.failed.emit(detail)

        def _on_progress(self, event: dict[str, Any]) -> None:
            self.progress.emit(event)


    class TaskManagerWindow(QMainWindow):
        """Main Qt window with goal input, output, and progress instrumentation sidebar."""

        def __init__(self, run_goal_fn: Callable[..., str]) -> None:
            super().__init__()
            self._run_goal_fn = run_goal_fn
            self._events: list[dict[str, Any]] = []
            self._step_nodes: dict[str, QTreeWidgetItem] = {}
            self._run_node: QTreeWidgetItem | None = None
            self._thread: QThread | None = None
            self._worker: AgentWorker | None = None

            self.setWindowTitle("Task Manager Agent")
            self.resize(1180, 700)
            self._build_ui()

        def _build_ui(self) -> None:
            root = QWidget(self)
            self.setCentralWidget(root)
            root_layout = QHBoxLayout(root)

            splitter = QSplitter(Qt.Horizontal)
            root_layout.addWidget(splitter)

            # Left panel: input + output.
            left_panel = QWidget()
            left_layout = QVBoxLayout(left_panel)

            input_box = QGroupBox("Goal Input")
            input_layout = QHBoxLayout(input_box)
            self.goal_input = QLineEdit()
            self.goal_input.setPlaceholderText("Example: Plan my tasks for today")
            self.goal_input.returnPressed.connect(self._submit_goal)
            self.submit_btn = QPushButton("Submit")
            self.submit_btn.clicked.connect(self._submit_goal)
            input_layout.addWidget(self.goal_input)
            input_layout.addWidget(self.submit_btn)

            output_box = QGroupBox("Output")
            output_layout = QVBoxLayout(output_box)
            self.output_view = QPlainTextEdit()
            self.output_view.setReadOnly(True)
            self.status_label = QLabel("Ready")
            output_layout.addWidget(self.output_view)
            output_layout.addWidget(self.status_label)

            left_layout.addWidget(input_box)
            left_layout.addWidget(output_box)

            # Right panel: progress instrumentation.
            right_panel = QWidget()
            right_layout = QVBoxLayout(right_panel)

            progress_box = QGroupBox("Agent Progress")
            progress_layout = QVBoxLayout(progress_box)

            mode_row = QHBoxLayout()
            mode_row.addWidget(QLabel("View mode:"))
            self.mode_selector = QComboBox()
            self.mode_selector.addItems(["Table view", "Tree view"])
            self.mode_selector.currentIndexChanged.connect(self._switch_progress_view)
            mode_row.addWidget(self.mode_selector)
            mode_row.addStretch(1)

            tree_controls = QHBoxLayout()
            self.expand_btn = QPushButton("Expand all")
            self.collapse_btn = QPushButton("Collapse all")
            self.expand_btn.clicked.connect(self._expand_tree)
            self.collapse_btn.clicked.connect(self._collapse_tree)
            tree_controls.addWidget(self.expand_btn)
            tree_controls.addWidget(self.collapse_btn)
            tree_controls.addStretch(1)

            self.progress_stack = QStackedWidget()

            self.progress_table = QTableWidget(0, 4)
            self.progress_table.setHorizontalHeaderLabels(["Time", "Type", "Name", "Details"])
            self.progress_table.horizontalHeader().setStretchLastSection(True)
            self.progress_table.setAlternatingRowColors(True)
            self.progress_table.setEditTriggers(QTableWidget.NoEditTriggers)

            self.progress_tree = QTreeWidget()
            self.progress_tree.setHeaderLabels(["Event", "Details"])

            self.progress_stack.addWidget(self.progress_table)
            self.progress_stack.addWidget(self.progress_tree)

            progress_layout.addLayout(mode_row)
            progress_layout.addLayout(tree_controls)
            progress_layout.addWidget(self.progress_stack)

            right_layout.addWidget(progress_box)

            splitter.addWidget(left_panel)
            splitter.addWidget(right_panel)
            splitter.setStretchFactor(0, 2)
            splitter.setStretchFactor(1, 3)

            self._switch_progress_view(0)

        @Slot()
        def _submit_goal(self) -> None:
            goal = self.goal_input.text().strip()
            if not goal:
                QMessageBox.warning(self, "Missing goal", "Enter a goal before submitting.")
                return

            self._reset_progress_for_new_run(goal)
            self.status_label.setText("Running...")
            self.submit_btn.setEnabled(False)

            self._thread = QThread(self)
            self._worker = AgentWorker(self._run_goal_fn, goal)
            self._worker.moveToThread(self._thread)

            self._thread.started.connect(self._worker.run)
            self._worker.progress.connect(self._on_progress_event)
            self._worker.finished.connect(self._on_run_finished)
            self._worker.failed.connect(self._on_run_failed)

            self._worker.finished.connect(self._thread.quit)
            self._worker.failed.connect(self._thread.quit)
            self._thread.finished.connect(self._cleanup_thread)

            self._thread.start()

        def _reset_progress_for_new_run(self, goal: str) -> None:
            self._events.clear()
            self._step_nodes.clear()
            self.progress_table.setRowCount(0)
            self.progress_tree.clear()
            started_at = datetime.utcnow().strftime("%H:%M:%S")
            self._run_node = QTreeWidgetItem([f"run: {goal}", f"started {started_at} UTC"])
            self.progress_tree.addTopLevelItem(self._run_node)
            self.progress_tree.expandAll()

        @Slot(dict)
        def _on_progress_event(self, event: dict[str, Any]) -> None:
            self._events.append(event)
            self._append_table_event(event)
            self._append_tree_event(event)

        @Slot(str)
        def _on_run_finished(self, result: str) -> None:
            self.output_view.setPlainText(result)
            self.status_label.setText("Completed")
            self.submit_btn.setEnabled(True)

        @Slot(str)
        def _on_run_failed(self, error_text: str) -> None:
            self.output_view.setPlainText(error_text)
            self.status_label.setText("Failed")
            self.submit_btn.setEnabled(True)

        @Slot()
        def _cleanup_thread(self) -> None:
            if self._worker is not None:
                self._worker.deleteLater()
                self._worker = None
            if self._thread is not None:
                self._thread.deleteLater()
                self._thread = None

        def _append_table_event(self, event: dict[str, Any]) -> None:
            row = self.progress_table.rowCount()
            self.progress_table.insertRow(row)

            values = [
                str(event.get("time", "")),
                str(event.get("type", "")),
                str(event.get("name", "")),
                str(event.get("details", "")),
            ]

            color = _EVENT_COLORS.get(str(event.get("type", "")).lower())
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if color is not None:
                    item.setBackground(color)
                if column in (0, 1, 2):
                    item.setTextAlignment(Qt.AlignCenter)
                self.progress_table.setItem(row, column, item)

            self.progress_table.scrollToBottom()

        def _append_tree_event(self, event: dict[str, Any]) -> None:
            if self._run_node is None:
                self._run_node = QTreeWidgetItem(["run", ""])
                self.progress_tree.addTopLevelItem(self._run_node)

            step_value = event.get("step")
            parent = self._run_node
            if step_value is not None:
                key = str(step_value)
                if key not in self._step_nodes:
                    self._step_nodes[key] = QTreeWidgetItem([f"step {key}", ""])
                    self._run_node.addChild(self._step_nodes[key])
                parent = self._step_nodes[key]

            label = f"{event.get('time', '')} | {event.get('name', '')} ({event.get('type', '')})"
            detail = str(event.get("details", ""))
            parent.addChild(QTreeWidgetItem([label, detail]))

        @Slot(int)
        def _switch_progress_view(self, index: int) -> None:
            self.progress_stack.setCurrentIndex(index)
            tree_selected = index == 1
            self.expand_btn.setVisible(tree_selected)
            self.collapse_btn.setVisible(tree_selected)

        @Slot()
        def _expand_tree(self) -> None:
            self.progress_tree.expandAll()

        @Slot()
        def _collapse_tree(self) -> None:
            self.progress_tree.collapseAll()


def run_gui(run_goal_fn: Callable[..., str]) -> int:
    """Launch the Qt6 UI and delegate goal execution through shared backend function."""
    if QApplication is None:
        raise RuntimeError(
            "PySide6 is not installed. Install dependencies with 'pip install -r requirements.txt'."
        )

    app = QApplication.instance() or QApplication([])
    window = TaskManagerWindow(run_goal_fn)
    window.show()
    return app.exec()
