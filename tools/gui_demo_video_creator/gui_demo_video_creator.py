#!/usr/bin/env python3
"""Create a real Task Manager GUI demo video with directed user actions."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import tempfile
import time
import wave
from array import array
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = PROJECT_ROOT / "Lessons" / "tutorial_site" / "media" / "tutorial-outcome.mp4"
DEFAULT_SOUND_PREVIEW_DIR = PROJECT_ROOT / "Lessons" / "tutorial_site" / "media" / "sound-previews"
TASK_MANAGER_DIR = PROJECT_ROOT / "task_manager"
ENCODE_PROFILES: dict[str, dict[str, str]] = {
    "draft": {
        "video_preset": "veryfast",
        "video_crf": "22",
        "audio_bitrate": "96k",
    },
    "release": {
        "video_preset": "medium",
        "video_crf": "18",
        "audio_bitrate": "128k",
    },
}


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
            "width": {"type": "integer", "default": 1366, "minimum": 900},
            "height": {"type": "integer", "default": 820, "minimum": 600},
            "fps": {"type": "integer", "default": 12, "minimum": 6},
            "encode-profile": {"type": "string", "default": "draft", "enum": ["draft", "release"]},
            "type-words-per-second": {"type": "number", "default": 3.0, "minimum": 0.5},
            "avg-chars-per-word": {"type": "number", "default": 5.0, "minimum": 1.0},
            "pre-click-delay-seconds": {"type": "number", "default": 1.0, "minimum": 0.0},
            "post-type-wait-seconds": {"type": "number", "default": 3.0, "minimum": 0.0},
            "between-goals-wait-seconds": {"type": "number", "default": 5.0, "minimum": 0.0},
            "ffmpeg-path": {"type": "string", "default": ""},
            "max-demo-seconds": {"type": "integer", "default": 240, "minimum": 30},
            "print-schema": {"type": "boolean", "default": False},
            "export-sound-previews": {"type": "boolean", "default": False},
            "sound-preview-dir": {
                "type": "string",
                "default": "Lessons/tutorial_site/media/sound-previews",
            },
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


def encode_profile_settings(profile_name: str) -> dict[str, str]:
    settings = ENCODE_PROFILES.get(profile_name)
    if not settings:
        valid = ", ".join(sorted(ENCODE_PROFILES.keys()))
        raise RuntimeError(f"Unknown encode profile '{profile_name}'. Expected one of: {valid}")
    return settings


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=tool_schema()["description"])
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--width", type=lambda v: min_int(v, 900, "width"), default=1366)
    parser.add_argument("--height", type=lambda v: min_int(v, 600, "height"), default=820)
    parser.add_argument("--fps", type=lambda v: min_int(v, 6, "fps"), default=12)
    parser.add_argument("--encode-profile", choices=sorted(ENCODE_PROFILES.keys()), default="draft")
    parser.add_argument("--type-words-per-second", type=positive_float, default=3.0)
    parser.add_argument("--avg-chars-per-word", type=positive_float, default=5.0)
    parser.add_argument("--pre-click-delay-seconds", type=float, default=1.0)
    parser.add_argument("--post-type-wait-seconds", type=float, default=3.0)
    parser.add_argument("--between-goals-wait-seconds", type=float, default=5.0)
    parser.add_argument("--ffmpeg-path", default="")
    parser.add_argument("--max-demo-seconds", type=lambda v: min_int(v, 30, "max-demo-seconds"), default=240)
    parser.add_argument("--print-schema", action="store_true")
    parser.add_argument("--export-sound-previews", action="store_true")
    parser.add_argument("--sound-preview-dir", default=str(DEFAULT_SOUND_PREVIEW_DIR))
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


def probe_video_duration_seconds(video_path: Path) -> float:
    try:
        import imageio_ffmpeg

        _frames, seconds = imageio_ffmpeg.count_frames_and_secs(str(video_path))
        return float(seconds)
    except Exception as exc:
        raise RuntimeError(f"Could not read video duration for: {video_path}") from exc


def resolve_ffprobe(ffmpeg_exe: str) -> str | None:
    ffmpeg_path = Path(ffmpeg_exe)
    ffprobe_name = "ffprobe.exe" if ffmpeg_path.name.lower().endswith(".exe") else "ffprobe"
    sibling = ffmpeg_path.with_name(ffprobe_name)
    if sibling.exists():
        return str(sibling)
    found = shutil.which("ffprobe")
    if found:
        return found
    return None


def probe_video_has_audio(video_path: Path, ffmpeg_exe: str) -> bool:
    ffprobe_exe = resolve_ffprobe(ffmpeg_exe)
    if ffprobe_exe:
        process = subprocess.run(
            [
                ffprobe_exe,
                "-v",
                "error",
                "-select_streams",
                "a",
                "-show_entries",
                "stream=index",
                "-of",
                "csv=p=0",
                str(video_path),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if process.returncode == 0:
            return bool((process.stdout or "").strip())

    fallback = subprocess.run(
        [ffmpeg_exe, "-i", str(video_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    diagnostic = ((fallback.stdout or "") + "\n" + (fallback.stderr or "")).lower()
    return " audio: " in diagnostic


def collect_video_file_stats(video_path: Path, ffmpeg_exe: str) -> dict[str, float | int | bool]:
    return {
        "video_length_seconds": probe_video_duration_seconds(video_path),
        "video_size_bytes": int(video_path.stat().st_size),
        "has_audio": bool(probe_video_has_audio(video_path, ffmpeg_exe)),
    }


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


def sidecar_paths(video_path: Path) -> tuple[Path, Path]:
    base = video_path.with_suffix("")
    return base.with_suffix(".directives.md"), base.with_suffix(".story.md")


def write_video_sidecars(
    video_path: Path,
    args: argparse.Namespace,
    goals: list[str],
    performance: dict[str, float | int | bool] | None = None,
) -> tuple[Path, Path]:
    directives_path, story_path = sidecar_paths(video_path)
    generated_at = now_iso()
    chars_per_second = args.type_words_per_second * args.avg_chars_per_word
    typing_interval_ms = max(int(round(1000 / chars_per_second)), 1)
    encode_settings = encode_profile_settings(str(args.encode_profile))

    directives_lines = [
        f"# Video Directives: {video_path.name}",
        "",
        f"- Generated (UTC): `{generated_at}`",
        "- Tool: `gui_demo_video_creator`",
        f"- Output video: `{video_path}`",
        "",
        "## Capture Directives",
        f"- Window size: `{args.width}x{args.height}`",
        f"- FPS: `{args.fps}`",
        f"- Encode profile: `{args.encode_profile}`",
        (
            f"- MP4 codec settings: `libx264 preset={encode_settings['video_preset']} "
            f"crf={encode_settings['video_crf']} pix_fmt=yuv420p`"
        ),
        f"- MP4 audio settings: `aac {encode_settings['audio_bitrate']} 48kHz`",
        "- UI source: `task_manager` PySide6 app",
        "",
        "## Interaction Directives",
        f"- Typing pace intent: `{args.type_words_per_second:.2f}` words/second",
        f"- Typing conversion: `{args.avg_chars_per_word:.2f}` chars/word",
        f"- Fixed typing cadence: `{chars_per_second:.2f}` chars/second (`{typing_interval_ms}` ms per char)",
        f"- Pre-click delay: `{max(float(args.pre_click_delay_seconds), 0.0):.2f}` seconds",
        f"- Wait after typing before submit: `{max(float(args.post_type_wait_seconds), 0.0):.2f}` seconds",
        f"- Wait between goals: `{max(float(args.between_goals_wait_seconds), 0.0):.2f}` seconds",
        "- Mouse cue style: non-occluding translucent/hollow markers with click pulse rings",
        "- Typing audio: pleasant keyboard keystroke sounds synchronized to goal-input characters",
        "- Logger audio: soft tick sound when progress rows are appended",
        "- Click audio: soft click sound when submit is clicked",
        "",
        "## Goal Script",
    ]
    for idx, goal in enumerate(goals, start=1):
        directives_lines.append(f"{idx}. {goal}")
    directives_lines.extend(
        [
            "",
            "## Iteration Knobs",
            "- Adjust timing knobs above to tune pacing and perceived responsiveness.",
            "- Edit the goal script text to steer scenario outcomes shown in output/logger.",
            "- Keep goals deterministic so result comparisons across iterations stay meaningful.",
        ]
    )
    directives_text = "\n".join(directives_lines) + "\n"
    directives_start = time.perf_counter()
    directives_path.write_text(directives_text, encoding="utf-8")
    directives_generation_seconds = time.perf_counter() - directives_start

    story_lines = [
        f"# Video Story: {video_path.name}",
        "",
        "## Narrative Intent",
        (
            "Demonstrate an end-to-end user journey in the task manager GUI: inspecting task state, "
            "performing updates, and verifying results with visible agent progress logs."
        ),
        "",
        "## Story Beats",
        "1. User checks current tasks and sees baseline state.",
        "2. User marks selected tasks done and verifies updated state.",
        "3. User adds more tasks and requests full aligned ASCII-table output.",
        "",
        "## How To Steer Next Iteration",
        "- Compare observed behavior against this story and the directives sidecar.",
        "- Modify goals or timing in directives to change the next render's flow.",
        "- Regenerate and review until narrative clarity and pacing match your target.",
    ]
    story_text = "\n".join(story_lines) + "\n"
    story_start = time.perf_counter()
    story_path.write_text(story_text, encoding="utf-8")
    story_generation_seconds = time.perf_counter() - story_start

    performance_lines = ["", "## Performance Status"]
    if performance:
        performance_lines.extend(
            [
                f"- Raw video generation (seconds): `{float(performance.get('raw_video_generation_seconds', 0.0)):.3f}`",
                f"- Post processing (seconds): `{float(performance.get('post_processing_seconds', 0.0)):.3f}`",
                f"- Transcode step (seconds): `{float(performance.get('transcode_seconds', 0.0)):.3f}`",
                f"- Overlay step (seconds): `{float(performance.get('overlay_seconds', 0.0)):.3f}`",
                f"- Video length (seconds): `{float(performance.get('video_length_seconds', 0.0)):.3f}`",
                f"- Video size on disk (bytes): `{int(performance.get('video_size_bytes', 0))}`",
                f"- Has audio stream: `{bool(performance.get('has_audio', False))}`",
            ]
        )
    performance_lines.extend(
        [
            f"- Directives generation (seconds): `{directives_generation_seconds:.6f}`",
            f"- Story generation (seconds): `{story_generation_seconds:.6f}`",
            f"- Sidecar generation total (seconds): `{(directives_generation_seconds + story_generation_seconds):.6f}`",
        ]
    )
    with directives_path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(performance_lines) + "\n")
    with story_path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(performance_lines) + "\n")
    return directives_path, story_path


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
        self.mouse_visible = True
        self.click_highlight_until = 0.0
        self.last_event_scan_time_seconds = 0.0
        self.keypress_times_seconds: list[float] = []
        self.log_event_times_seconds: list[float] = []
        self.click_times_seconds: list[float] = []
        self.last_goal_input_length = 0
        self.last_progress_row_count = 0
        self.pending_click_sound_count = 0

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
        self.mouse_visible = False
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
        self.pending_click_sound_count += 1
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
        current_time_seconds = self.frame_index / float(self.args.fps)
        self._capture_audio_event_times(current_time_seconds)
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
        self.mouse_visible = True

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

        if self.mouse_visible:
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

    def _capture_audio_event_times(self, current_time_seconds: float) -> None:
        start_time = max(self.last_event_scan_time_seconds, 0.0)
        end_time = max(current_time_seconds, start_time)
        span = max(end_time - start_time, 1e-6)

        current_goal_len = len(self.window.goal_input.text())
        if current_goal_len < self.last_goal_input_length:
            self.last_goal_input_length = current_goal_len
        new_chars = current_goal_len - self.last_goal_input_length
        if new_chars > 0:
            for index in range(new_chars):
                fraction = (index + 1) / float(new_chars + 1)
                self.keypress_times_seconds.append(start_time + span * fraction)
            self.last_goal_input_length = current_goal_len

        current_rows = self.window.progress_table.rowCount()
        if current_rows < self.last_progress_row_count:
            self.last_progress_row_count = current_rows
        new_rows = current_rows - self.last_progress_row_count
        if new_rows > 0:
            for index in range(new_rows):
                fraction = (index + 1) / float(new_rows + 1)
                self.log_event_times_seconds.append(start_time + span * fraction)
            self.last_progress_row_count = current_rows

        if self.pending_click_sound_count > 0:
            for index in range(self.pending_click_sound_count):
                fraction = (index + 1) / float(self.pending_click_sound_count + 1)
                self.click_times_seconds.append(start_time + span * fraction)
            self.pending_click_sound_count = 0

        self.last_event_scan_time_seconds = end_time


def synthesize_interaction_audio(
    audio_path: Path,
    *,
    duration_seconds: float,
    keypress_times_seconds: list[float],
    log_event_times_seconds: list[float],
    click_times_seconds: list[float],
    sample_rate: int = 48000,
) -> None:
    total_samples = max(int(math.ceil(max(duration_seconds, 0.0) * sample_rate)), 1)
    mix = array("f", [0.0]) * total_samples

    def add_burst(
        event_time: float,
        *,
        event_index: int,
        duration: float,
        amplitude: float,
        decay: float,
        freq_a: float,
        freq_b: float,
        tonal_mix: float,
        noise_mix: float,
        phase_seed: float,
    ) -> None:
        start_sample = int(max(event_time, 0.0) * sample_rate)
        if start_sample >= total_samples:
            return
        burst_samples = max(int(sample_rate * duration), 1)
        phase = phase_seed * float((event_index % 11) + 1)
        for n in range(burst_samples):
            sample_index = start_sample + n
            if sample_index >= total_samples:
                break
            t = n / float(sample_rate)
            envelope = math.exp(-decay * t)
            tonal = (
                tonal_mix * math.sin(2.0 * math.pi * freq_a * t + phase)
                + (1.0 - tonal_mix) * math.sin(2.0 * math.pi * freq_b * t + phase * 0.63)
            )
            noise_seed = math.sin((event_index + 3) * (n + 29) * 12.9898) * 43758.5453
            noise = (noise_seed - math.floor(noise_seed)) * 2.0 - 1.0
            sample_value = ((1.0 - noise_mix) * tonal + noise_mix * noise) * envelope * amplitude
            mix[sample_index] += sample_value

    for event_index, event_time in enumerate(keypress_times_seconds):
        add_burst(
            event_time,
            event_index=event_index,
            duration=0.050,
            amplitude=0.070,
            decay=57.0,
            freq_a=1580.0 + float((event_index % 5) * 62),
            freq_b=1040.0 + float((event_index % 4) * 47),
            tonal_mix=0.72,
            noise_mix=0.12,
            phase_seed=0.31,
        )

    for event_index, event_time in enumerate(log_event_times_seconds):
        add_burst(
            event_time,
            event_index=event_index,
            duration=0.045,
            amplitude=0.040,
            decay=72.0,
            freq_a=760.0 + float((event_index % 4) * 24),
            freq_b=1180.0 + float((event_index % 3) * 31),
            tonal_mix=0.66,
            noise_mix=0.08,
            phase_seed=0.22,
        )

    for event_index, event_time in enumerate(click_times_seconds):
        add_burst(
            event_time,
            event_index=event_index,
            duration=0.085,
            amplitude=0.090,
            decay=46.0,
            freq_a=640.0 + float((event_index % 2) * 28),
            freq_b=1760.0 + float((event_index % 3) * 54),
            tonal_mix=0.58,
            noise_mix=0.18,
            phase_seed=0.41,
        )

    peak = max((abs(value) for value in mix), default=0.0)
    gain = 0.82 / peak if peak > 0.82 else 1.0
    pcm_samples = array("h")
    for value in mix:
        clamped = max(-1.0, min(1.0, value * gain))
        pcm_samples.append(int(round(clamped * 32767.0)))

    audio_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(audio_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm_samples.tobytes())


def export_sound_previews(preview_dir: Path) -> list[Path]:
    preview_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []

    typing_preview = preview_dir / "gui-typing.wav"
    typing_times = [0.10 + (index * 0.09) for index in range(18)]
    synthesize_interaction_audio(
        typing_preview,
        duration_seconds=2.4,
        keypress_times_seconds=typing_times,
        log_event_times_seconds=[],
        click_times_seconds=[],
    )
    generated.append(typing_preview)

    logger_preview = preview_dir / "gui-logger.wav"
    logger_times = [0.25 + (index * 0.24) for index in range(8)]
    synthesize_interaction_audio(
        logger_preview,
        duration_seconds=2.6,
        keypress_times_seconds=[],
        log_event_times_seconds=logger_times,
        click_times_seconds=[],
    )
    generated.append(logger_preview)

    click_preview = preview_dir / "gui-click.wav"
    click_times = [0.45, 1.25, 1.95]
    synthesize_interaction_audio(
        click_preview,
        duration_seconds=2.4,
        keypress_times_seconds=[],
        log_event_times_seconds=[],
        click_times_seconds=click_times,
    )
    generated.append(click_preview)

    return generated


def encode_video(
    ffmpeg_exe: str,
    frames_dir: Path,
    fps: int,
    output_path: Path,
    encode_settings: dict[str, str],
    audio_track_path: Path | None = None,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pattern = str(frames_dir / "frame_%06d.png")
    ffmpeg_args = [
        "-y",
        "-framerate",
        str(fps),
        "-i",
        pattern,
    ]
    if audio_track_path is not None and audio_track_path.exists():
        ffmpeg_args.extend(["-i", str(audio_track_path)])
    ffmpeg_args.extend(
        [
            "-c:v",
            "libx264",
            "-preset",
            encode_settings["video_preset"],
            "-crf",
            encode_settings["video_crf"],
            "-pix_fmt",
            "yuv420p",
        ]
    )
    if audio_track_path is not None and audio_track_path.exists():
        ffmpeg_args.extend(
            [
                "-c:a",
                "aac",
                "-b:a",
                encode_settings["audio_bitrate"],
                "-ar",
                "48000",
                "-shortest",
            ]
        )
    ffmpeg_args.extend(["-movflags", "+faststart", str(output_path)])
    run_ffmpeg(ffmpeg_exe, ffmpeg_args)


def run_demo(args: argparse.Namespace) -> list[Path]:
    sys.path.insert(0, str(TASK_MANAGER_DIR))
    if not TASK_MANAGER_DIR.exists():
        raise RuntimeError(f"task_manager directory is missing: {TASK_MANAGER_DIR}")

    from PySide6.QtWidgets import QApplication

    import storage
    import ui

    output_path = Path(args.output).resolve()
    raw_video_generation_seconds = 0.0
    transcode_seconds = 0.0
    post_processing_seconds = 0.0
    ffmpeg_exe = ""

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
        raw_start = time.perf_counter()
        app.exec()
        raw_video_generation_seconds = time.perf_counter() - raw_start

        frame_count = len(list(frames_dir.glob("frame_*.png")))
        if frame_count < 2:
            raise RuntimeError("Frame capture failed; not enough frames were generated.")

        video_duration_seconds = frame_count / float(args.fps)
        interaction_audio_path = temp_dir / "interaction_audio.wav"
        synthesize_interaction_audio(
            interaction_audio_path,
            duration_seconds=video_duration_seconds,
            keypress_times_seconds=director.keypress_times_seconds,
            log_event_times_seconds=director.log_event_times_seconds,
            click_times_seconds=director.click_times_seconds,
        )

        ffmpeg_exe = resolve_ffmpeg(args.ffmpeg_path)
        encode_settings = encode_profile_settings(str(args.encode_profile))
        post_start = time.perf_counter()
        transcode_start = time.perf_counter()
        encode_video(
            ffmpeg_exe=ffmpeg_exe,
            frames_dir=frames_dir,
            fps=args.fps,
            output_path=output_path,
            encode_settings=encode_settings,
            audio_track_path=interaction_audio_path,
        )
        transcode_seconds = time.perf_counter() - transcode_start
        post_processing_seconds = time.perf_counter() - post_start

    performance: dict[str, float | int | bool] = {
        "raw_video_generation_seconds": raw_video_generation_seconds,
        "post_processing_seconds": post_processing_seconds,
        "transcode_seconds": transcode_seconds,
        "overlay_seconds": 0.0,
    }
    performance.update(collect_video_file_stats(output_path, ffmpeg_exe))

    generated_paths: list[Path] = [output_path]
    directives_path, story_path = write_video_sidecars(output_path, args, DemoDirector.GOALS, performance=performance)
    generated_paths.extend([directives_path, story_path])

    return generated_paths


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.print_schema:
        print(json.dumps(tool_schema(), indent=2))
        return 0
    if args.export_sound_previews:
        generated_paths = export_sound_previews(Path(args.sound_preview_dir).resolve())
        print("Generated GUI sound previews:")
        for path in generated_paths:
            print(f" - {path} ({path.stat().st_size:,} bytes)")
        return 0

    generated_paths = run_demo(args)
    print("Generated GUI demo video:")
    for path in generated_paths:
        print(f" - {path} ({path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
