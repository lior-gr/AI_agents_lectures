#!/usr/bin/env python3
"""Create a real Task Manager GUI demo video with directed user actions."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = PROJECT_ROOT / "Lessons" / "tutorial_site" / "media" / "tutorial-outcome.mp4"
DEFAULT_FALLBACK = PROJECT_ROOT / "Lessons" / "tutorial_site" / "media" / "tutorial-outcome-fallback.mp4"
TASK_MANAGER_DIR = PROJECT_ROOT / "task_manager"


def tool_schema() -> dict[str, Any]:
    return {
        "tool": "gui_demo_video_creator",
        "entrypoints": {
            "windows": "tools/gui_demo_video_creator/run.ps1",
            "unix": "tools/gui_demo_video_creator/run.sh",
            "python": "tools/gui_demo_video_creator/gui_demo_video_creator.py",
        },
        "description": (
            "Launch the real task_manager PySide6 GUI, simulate directed user goals, "
            "capture the live window with visible mouse/click cues, and render tutorial outcome MP4."
        ),
        "arguments": {
            "output": {"type": "string", "default": str(DEFAULT_OUTPUT)},
            "fallback-output": {"type": "string", "default": str(DEFAULT_FALLBACK)},
            "generate-fallback-copy": {"type": "boolean", "default": True},
            "width": {"type": "integer", "default": 1366, "minimum": 900},
            "height": {"type": "integer", "default": 820, "minimum": 600},
            "fps": {"type": "integer", "default": 12, "minimum": 6},
            "type-words-per-second": {"type": "number", "default": 3.0, "minimum": 0.5},
            "avg-chars-per-word": {"type": "number", "default": 5.0, "minimum": 1.0},
            "pre-click-delay-seconds": {"type": "number", "default": 1.0, "minimum": 0.0},
            "post-type-wait-seconds": {"type": "number", "default": 3.0, "minimum": 0.0},
            "between-goals-wait-seconds": {"type": "number", "default": 5.0, "minimum": 0.0},
            "ffmpeg-path": {"type": "string", "default": ""},
            "max-demo-seconds": {"type": "integer", "default": 240, "minimum": 30},
            "print-schema": {"type": "boolean", "default": False},
        },
    }


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than 0")
    return parsed


def min_int(value: str, minimum: int, label: str) -> int:
    parsed = int(value)
    if parsed < minimum:
        raise argparse.ArgumentTypeError(f"{label} must be at least {minimum}")
    return parsed


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=tool_schema()["description"])
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--fallback-output", default=str(DEFAULT_FALLBACK))
    parser.add_argument("--generate-fallback-copy", action="store_true", default=True)
    parser.add_argument("--no-generate-fallback-copy", dest="generate_fallback_copy", action="store_false")
    parser.add_argument("--width", type=lambda v: min_int(v, 900, "width"), default=1366)
    parser.add_argument("--height", type=lambda v: min_int(v, 600, "height"), default=820)
    parser.add_argument("--fps", type=lambda v: min_int(v, 6, "fps"), default=12)
    parser.add_argument("--type-words-per-second", type=positive_float, default=3.0)
    parser.add_argument("--avg-chars-per-word", type=positive_float, default=5.0)
    parser.add_argument("--pre-click-delay-seconds", type=float, default=1.0)
    parser.add_argument("--post-type-wait-seconds", type=float, default=3.0)
    parser.add_argument("--between-goals-wait-seconds", type=float, default=5.0)
    parser.add_argument("--ffmpeg-path", default="")
    parser.add_argument("--max-demo-seconds", type=lambda v: min_int(v, 30, "max-demo-seconds"), default=240)
    parser.add_argument("--print-schema", action="store_true")
    return parser.parse_args(argv)


def resolve_ffmpeg(preferred_path: str) -> str:
    if preferred_path:
        candidate = Path(preferred_path)
        if candidate.exists():
            return str(candidate.resolve())
        resolved = shutil.which(preferred_path)
        if resolved:
            return resolved
        raise RuntimeError(f"ffmpeg path was provided but not found: {preferred_path}")

    resolved = shutil.which("ffmpeg")
    if resolved:
        return resolved

    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:
        raise RuntimeError("Could not resolve ffmpeg executable.") from exc


def run_ffmpeg(ffmpeg_exe: str, args: list[str]) -> None:
    process = subprocess.run([ffmpeg_exe, *args], check=False)
    if process.returncode != 0:
        raise RuntimeError(f"ffmpeg failed with exit code {process.returncode}")


def seed_demo_tasks(storage_module: Any) -> None:
    demo_tasks = [
        {"id": 1, "text": "Review sprint goals", "completed": False},
        {"id": 2, "text": "Send roadmap update", "completed": False},
        {"id": 3, "text": "Refactor task parser", "completed": False},
        {"id": 4, "text": "Validate MCP bridge", "completed": False},
        {"id": 5, "text": "Prepare team demo", "completed": False},
    ]
    storage_module.save_tasks(demo_tasks)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def format_ascii_table(tasks: list[dict[str, Any]]) -> str:
    headers = ["ID", "Task", "Done"]
    rows = [[str(task["id"]), str(task["text"]), "yes" if task.get("completed") else "no"] for task in tasks]
    widths = [len(headers[0]), len(headers[1]), len(headers[2])]
    for row in rows:
        for idx, value in enumerate(row):
            widths[idx] = max(widths[idx], len(value))

    def border() -> str:
        return "+" + "+".join("-" * (w + 2) for w in widths) + "+"

    def render_row(values: list[str]) -> str:
        return "| " + " | ".join(value.ljust(widths[idx]) for idx, value in enumerate(values)) + " |"

    lines = [border(), render_row(headers), border()]
    for row in rows:
        lines.append(render_row(row))
    lines.append(border())
    return "\n".join(lines)


class DemoTaskAgent:
    """Deterministic demo runner that emits progress events like the real agent."""

    def __init__(self, storage_module: Any, pause_seconds: float = 0.65) -> None:
        self.storage = storage_module
        self.pause_seconds = pause_seconds

    def _emit(
        self,
        callback,
        event_type: str,
        name: str,
        details: str,
        step: int | None = None,
        max_steps: int | None = None,
    ) -> None:
        if callback is None:
            return
        event: dict[str, Any] = {
            "time": now_iso(),
            "type": event_type,
            "name": name,
            "details": details,
        }
        if step is not None:
            event["step"] = step
        if max_steps is not None:
            event["max_steps"] = max_steps
        callback(event)

    def _sleep(self) -> None:
        time.sleep(self.pause_seconds)

    def _list_tasks_with_events(self, callback, step: int, max_steps: int) -> list[dict[str, Any]]:
        self._emit(callback, "tool", "tool_called", "Calling tool=list_tasks with args={}", step, max_steps)
        self._sleep()
        tasks = self.storage.list_tasks()
        self._emit(
            callback,
            "tool",
            "tool_result",
            f"Result from tool=list_tasks: count={len(tasks)}",
            step,
            max_steps,
        )
        self._sleep()
        return tasks

    def run_goal(self, goal: str, progress_callback=None) -> str:
        goal_clean = " ".join(goal.strip().split())
        goal_lc = goal_clean.lower()
        max_steps = 4

        self._emit(progress_callback, "lifecycle", "agent_start", f"Starting run for goal: {goal_clean}")
        self._emit(
            progress_callback,
            "step",
            "step_start",
            "Planning actions and selecting deterministic tools.",
            step=1,
            max_steps=max_steps,
        )
        self._sleep()

        if "mark" in goal_lc and "done" in goal_lc:
            self._emit(
                progress_callback,
                "step",
                "plan",
                "Plan: complete tasks 2 and 4, then list tasks to verify state.",
                step=1,
                max_steps=max_steps,
            )
            self._sleep()
            for task_id in (2, 4):
                self._emit(
                    progress_callback,
                    "tool",
                    "tool_called",
                    f"Calling tool=complete_task with args={{'task_id': {task_id}}}",
                    step=2,
                    max_steps=max_steps,
                )
                self._sleep()
                success, message = self.storage.complete_task(task_id)
                result = {"status": "ok" if success else "error", "message": message}
                self._emit(
                    progress_callback,
                    "tool",
                    "tool_result",
                    f"Result from tool=complete_task: {json.dumps(result, ensure_ascii=True)}",
                    step=2,
                    max_steps=max_steps,
                )
                self._sleep()
            tasks = self._list_tasks_with_events(progress_callback, step=3, max_steps=max_steps)
        elif "add" in goal_lc:
            self._emit(
                progress_callback,
                "step",
                "plan",
                "Plan: add three tasks, then list all tasks as aligned ASCII table.",
                step=1,
                max_steps=max_steps,
            )
            self._sleep()
            additions = [
                "Prepare demo slides",
                "Email team summary",
                "Plan follow-up call",
            ]
            for text in additions:
                self._emit(
                    progress_callback,
                    "tool",
                    "tool_called",
                    f"Calling tool=add_task with args={{'text': '{text}'}}",
                    step=2,
                    max_steps=max_steps,
                )
                self._sleep()
                task = self.storage.add_task(text)
                self._emit(
                    progress_callback,
                    "tool",
                    "tool_result",
                    f"Result from tool=add_task: id={task['id']}",
                    step=2,
                    max_steps=max_steps,
                )
                self._sleep()
            tasks = self._list_tasks_with_events(progress_callback, step=3, max_steps=max_steps)
        else:
            self._emit(
                progress_callback,
                "step",
                "plan",
                "Plan: list current tasks and return aligned ASCII table output.",
                step=1,
                max_steps=max_steps,
            )
            self._sleep()
            tasks = self._list_tasks_with_events(progress_callback, step=2, max_steps=max_steps)

        ascii_table = format_ascii_table(tasks)
        self._emit(
            progress_callback,
            "stop",
            "stop",
            "Stop reason=deterministic_demo_completed",
            step=max_steps,
            max_steps=max_steps,
        )
        return "All tasks (ASCII table):\n" + ascii_table


class DemoDirector:
    """Automate typing/submission timing and capture UI frames."""

    GOALS = [
        "Show current tasks state.",
        "Mark tasks 2 and 4 as done, and show current state.",
        (
            "Add tasks Prepare demo slides, Email team summary, and Plan follow-up call. "
            "Then show all tasks in an ASCII table with aligned vertical separators."
        ),
    ]

    def __init__(self, app, window, frames_dir: Path, args: argparse.Namespace) -> None:
        from PySide6.QtCore import QTimer

        self.app = app
        self.window = window
        self.frames_dir = frames_dir
        self.args = args
        self.current_goal_idx = 0
        self.current_goal_text = ""
        self.char_cursor = 0
        self.frame_index = 0
        self.finished = False
        self.chars_per_second = self.args.type_words_per_second * self.args.avg_chars_per_word
        self.typing_interval_ms = max(int(round(1000 / self.chars_per_second)), 1)
        self.pre_click_delay_seconds = max(float(self.args.pre_click_delay_seconds), 0.0)
        self.mouse_x = 24.0
        self.mouse_y = 24.0
        self.click_highlight_until = 0.0

        self.capture_timer = QTimer()
        self.capture_timer.timeout.connect(self._capture_frame)

        self.typing_timer = QTimer()
        self.typing_timer.timeout.connect(self._type_next_char)

        self.completion_timer = QTimer()
        self.completion_timer.timeout.connect(self._poll_completion)

        self.fail_safe_timer = QTimer()
        self.fail_safe_timer.setSingleShot(True)
        self.fail_safe_timer.timeout.connect(self._force_finish)

    def start(self) -> None:
        frame_interval_ms = max(int(round(1000 / self.args.fps)), 1)
        self.capture_timer.start(frame_interval_ms)
        self.fail_safe_timer.start(int(self.args.max_demo_seconds * 1000))
        self._set_mouse_to_input_typing_point()
        self._capture_frame()
        self._single_shot(1000, self._begin_goal)

    def _single_shot(self, ms: int, callback) -> None:
        from PySide6.QtCore import QTimer

        QTimer.singleShot(ms, callback)

    def _begin_goal(self) -> None:
        if self.finished:
            return
        if self.current_goal_idx >= len(self.GOALS):
            self._single_shot(1500, self.finish)
            return

        goal = self.GOALS[self.current_goal_idx]
        self.current_goal_text = goal
        self.char_cursor = 0
        self._set_mouse_to_input_typing_point()
        self.window.goal_input.clear()
        self.typing_timer.start(self.typing_interval_ms)

    def _type_next_char(self) -> None:
        if self.char_cursor < len(self.current_goal_text):
            typed = self.current_goal_text[: self.char_cursor + 1]
            self.window.goal_input.setText(typed)
            self.window.goal_input.setCursorPosition(len(typed))
            self.char_cursor += 1
            return

        self.typing_timer.stop()
        delay_ms = int(round(self.args.post_type_wait_seconds * 1000))
        self._single_shot(delay_ms, self._submit_goal)

    def _submit_goal(self) -> None:
        if self.finished:
            return
        self._set_mouse_to_widget_center(self.window.submit_btn)
        self.click_highlight_until = time.monotonic() + self.pre_click_delay_seconds + 0.35
        self._single_shot(int(round(self.pre_click_delay_seconds * 1000)), self._execute_submit_click)

    def _execute_submit_click(self) -> None:
        if self.finished:
            return
        self.window.submit_btn.click()
        self.completion_timer.start(200)

    def _poll_completion(self) -> None:
        if self.finished:
            return
        status = self.window.status_label.text().strip().lower()
        done = self.window.submit_btn.isEnabled() and status in {"completed", "failed"}
        if not done:
            return

        self.completion_timer.stop()
        self.current_goal_idx += 1

        if self.current_goal_idx >= len(self.GOALS):
            self._single_shot(1500, self.finish)
            return

        wait_ms = int(round(self.args.between_goals_wait_seconds * 1000))
        self._single_shot(wait_ms, self._begin_goal)

    def _capture_frame(self) -> None:
        pixmap = self.window.grab()
        self._draw_mouse_overlay(pixmap)
        frame_path = self.frames_dir / f"frame_{self.frame_index:06d}.png"
        pixmap.save(str(frame_path), "PNG")
        self.frame_index += 1

    def _set_mouse_to_input_typing_point(self) -> None:
        from PySide6.QtCore import QPoint

        line_edit = self.window.goal_input
        # Keep marker near the lower-left edge to avoid covering typed text.
        anchor = line_edit.mapTo(self.window, QPoint(18, max(8, line_edit.height() - 7)))
        self.mouse_x = float(anchor.x())
        self.mouse_y = float(anchor.y())

    def _set_mouse_to_widget_center(self, widget) -> None:
        center = widget.mapTo(self.window, widget.rect().center())
        self.mouse_x = float(center.x())
        self.mouse_y = float(center.y())

    def _draw_mouse_overlay(self, pixmap) -> None:
        from PySide6.QtCore import QPointF, Qt
        from PySide6.QtGui import QColor, QPainter, QPen

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)

        if time.monotonic() <= self.click_highlight_until:
            painter.setPen(QPen(QColor(255, 76, 76, 110), 3))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(self.mouse_x, self.mouse_y), 28, 28)
            painter.setPen(QPen(QColor(255, 76, 76, 80), 2))
            painter.drawEllipse(QPointF(self.mouse_x, self.mouse_y), 38, 38)

        # Non-occluding pointer marker: hollow rings only.
        painter.setPen(QPen(QColor(0, 0, 0, 150), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPointF(self.mouse_x, self.mouse_y), 10, 10)
        painter.setPen(QPen(QColor(255, 230, 0, 170), 2))
        painter.drawEllipse(QPointF(self.mouse_x, self.mouse_y), 7, 7)
        painter.end()

    def _force_finish(self) -> None:
        if self.finished:
            return
        self.finish()

    def finish(self) -> None:
        if self.finished:
            return
        self.finished = True
        self.typing_timer.stop()
        self.completion_timer.stop()
        self.capture_timer.stop()
        self._capture_frame()
        self.app.quit()


def encode_video(ffmpeg_exe: str, frames_dir: Path, fps: int, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pattern = str(frames_dir / "frame_%06d.png")
    run_ffmpeg(
        ffmpeg_exe,
        [
            "-y",
            "-framerate",
            str(fps),
            "-i",
            pattern,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output_path),
        ],
    )


def run_demo(args: argparse.Namespace) -> tuple[Path, Path | None]:
    sys.path.insert(0, str(TASK_MANAGER_DIR))
    if not TASK_MANAGER_DIR.exists():
        raise RuntimeError(f"task_manager directory is missing: {TASK_MANAGER_DIR}")

    from PySide6.QtWidgets import QApplication

    import storage
    import ui

    output_path = Path(args.output).resolve()
    fallback_path = Path(args.fallback_output).resolve()

    with tempfile.TemporaryDirectory(prefix="gui-demo-") as temp_dir_raw:
        temp_dir = Path(temp_dir_raw)
        frames_dir = temp_dir / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)

        storage.DB_PATH = temp_dir / "tasks_demo.json"
        seed_demo_tasks(storage)
        agent = DemoTaskAgent(storage_module=storage)

        app = QApplication.instance() or QApplication([])
        window = ui.TaskManagerWindow(agent.run_goal)
        window.resize(args.width, args.height)
        window.show()

        director = DemoDirector(app=app, window=window, frames_dir=frames_dir, args=args)
        director.start()
        app.exec()

        frame_count = len(list(frames_dir.glob("frame_*.png")))
        if frame_count < 2:
            raise RuntimeError("Frame capture failed; not enough frames were generated.")

        ffmpeg_exe = resolve_ffmpeg(args.ffmpeg_path)
        encode_video(ffmpeg_exe=ffmpeg_exe, frames_dir=frames_dir, fps=args.fps, output_path=output_path)

    copied_fallback: Path | None = None
    if args.generate_fallback_copy:
        fallback_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(output_path, fallback_path)
        copied_fallback = fallback_path

    return output_path, copied_fallback


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.print_schema:
        print(json.dumps(tool_schema(), indent=2))
        return 0

    output_path, fallback_path = run_demo(args)
    print("Generated GUI demo video:")
    print(f" - {output_path} ({output_path.stat().st_size:,} bytes)")
    if fallback_path is not None:
        print(f" - {fallback_path} ({fallback_path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
