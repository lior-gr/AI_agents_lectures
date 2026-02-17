#!/usr/bin/env python3
"""Record browser-based tutorial videos and concept slideshows."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Iterable
from urllib.parse import urljoin


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SITE_DIR = PROJECT_ROOT / "Lessons" / "tutorial_site"
DEFAULT_MEDIA_DIR = DEFAULT_SITE_DIR / "media"


def tool_schema() -> dict:
    return {
        "tool": "browser_video_creator",
        "entrypoints": {
            "windows": "tools/browser_video_creator/run.ps1",
            "unix": "tools/browser_video_creator/run.sh",
            "python": "tools/browser_video_creator/browser_video_creator.py",
        },
        "description": (
            "Generate real videos from browser-rendered HTML pages, with support for "
            "tutorial-site walkthroughs and concept-to-slideshow recording."
        ),
        "arguments": {
            "mode": {
                "type": "string",
                "required": False,
                "default": "site-videos",
                "enum": ["site-videos", "html-tour", "concept-slideshow"],
                "description": "Select the recording workflow.",
            },
            "site-dir": {
                "type": "string",
                "required": False,
                "default": "Lessons/tutorial_site",
                "description": "Directory served by local HTTP server for site recordings.",
            },
            "media-dir": {
                "type": "string",
                "required": False,
                "default": "Lessons/tutorial_site/media",
                "description": "Destination directory for generated media files.",
            },
            "output-mode": {
                "type": "string",
                "required": False,
                "default": "both",
                "enum": ["both", "outcome", "process"],
                "description": "Used in site-videos mode to choose output set.",
            },
            "site-pages": {
                "type": "string",
                "required": False,
                "default": (
                    "index.html,lesson-0-foundations.html,lesson-1-baseline.html,"
                    "lesson-2-agent-loop.html,lesson-3-mcp-decoupling.html,"
                    "lesson-4-skills.html,lesson-5-ui-boundary.html,"
                    "appendix-a-multiple-skills.html,appendix-b-bounded-routing.html"
                ),
                "description": "Comma-separated page list for site walkthrough recordings.",
            },
            "tour-pages": {
                "type": "string",
                "required": False,
                "default": "index.html,lesson-0-foundations.html,lesson-1-baseline.html",
                "description": "Comma-separated page list used by html-tour mode.",
            },
            "tour-output": {
                "type": "string",
                "required": False,
                "default": "html-tour.mp4",
                "description": "Output filename used by html-tour mode (written under media-dir).",
            },
            "concept": {
                "type": "string",
                "required": False,
                "default": "",
                "description": "Concept text for concept-slideshow mode.",
            },
            "concept-file": {
                "type": "string",
                "required": False,
                "default": "",
                "description": "Path to concept text file (used when --concept is empty).",
            },
            "slideshow-output": {
                "type": "string",
                "required": False,
                "default": "concept-slideshow.mp4",
                "description": "Output filename for concept-slideshow mode (written under media-dir).",
            },
            "slideshow-title": {
                "type": "string",
                "required": False,
                "default": "Concept Slideshow",
                "description": "Title used on concept slideshow cards.",
            },
            "slide-duration": {
                "type": "number",
                "required": False,
                "default": 3.0,
                "minimum": 0.5,
                "description": "Seconds each slide stays visible in concept-slideshow mode.",
            },
            "points-per-slide": {
                "type": "integer",
                "required": False,
                "default": 4,
                "minimum": 1,
                "description": "Maximum bullet points per generated slide.",
            },
            "width": {
                "type": "integer",
                "required": False,
                "default": 1280,
                "minimum": 640,
                "description": "Recording width.",
            },
            "height": {
                "type": "integer",
                "required": False,
                "default": 720,
                "minimum": 360,
                "description": "Recording height.",
            },
            "fps": {
                "type": "integer",
                "required": False,
                "default": 30,
                "minimum": 12,
                "description": "Target frames-per-second for MP4 outputs.",
            },
            "browser": {
                "type": "string",
                "required": False,
                "default": "auto",
                "enum": ["auto", "chrome", "edge"],
                "description": "Preferred installed browser channel.",
            },
            "browser-path": {
                "type": "string",
                "required": False,
                "default": "",
                "description": "Optional explicit browser executable path.",
            },
            "show-browser": {
                "type": "boolean",
                "required": False,
                "default": False,
                "description": "Show browser window while recording (headless is default).",
            },
            "show-mouse-overlay": {
                "type": "boolean",
                "required": False,
                "default": True,
                "description": "Render an in-page mouse cursor overlay in recorded videos.",
            },
            "pre-click-delay-seconds": {
                "type": "number",
                "required": False,
                "default": 1.0,
                "minimum": 0.0,
                "description": "Delay before executing click actions, after highlighting the click target.",
            },
            "ffmpeg-path": {
                "type": "string",
                "required": False,
                "default": "",
                "description": "Optional explicit ffmpeg executable.",
            },
            "generate-fallback-copies": {
                "type": "boolean",
                "required": False,
                "default": False,
                "description": "Copy primary outputs to fallback file names expected by the site.",
            },
            "print-schema": {
                "type": "boolean",
                "required": False,
                "default": False,
                "description": "Print schema JSON and exit.",
            },
        },
    }


def positive_float(value: str) -> float:
    result = float(value)
    if result <= 0:
        raise argparse.ArgumentTypeError("must be greater than 0")
    return result


def min_int(value: str, minimum: int, name: str) -> int:
    result = int(value)
    if result < minimum:
        raise argparse.ArgumentTypeError(f"{name} must be at least {minimum}")
    return result


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=tool_schema()["description"])
    parser.add_argument("--mode", choices=["site-videos", "html-tour", "concept-slideshow"], default="site-videos")
    parser.add_argument("--site-dir", default=str(DEFAULT_SITE_DIR))
    parser.add_argument("--media-dir", default=str(DEFAULT_MEDIA_DIR))
    parser.add_argument("--output-mode", choices=["both", "outcome", "process"], default="both")
    parser.add_argument(
        "--site-pages",
        default=(
            "index.html,lesson-0-foundations.html,lesson-1-baseline.html,"
            "lesson-2-agent-loop.html,lesson-3-mcp-decoupling.html,lesson-4-skills.html,"
            "lesson-5-ui-boundary.html,appendix-a-multiple-skills.html,"
            "appendix-b-bounded-routing.html"
        ),
    )
    parser.add_argument("--tour-pages", default="index.html,lesson-0-foundations.html,lesson-1-baseline.html")
    parser.add_argument("--tour-output", default="html-tour.mp4")
    parser.add_argument("--concept", default="")
    parser.add_argument("--concept-file", default="")
    parser.add_argument("--slideshow-output", default="concept-slideshow.mp4")
    parser.add_argument("--slideshow-title", default="Concept Slideshow")
    parser.add_argument("--slide-duration", type=positive_float, default=3.0)
    parser.add_argument("--points-per-slide", type=lambda v: min_int(v, 1, "points-per-slide"), default=4)
    parser.add_argument("--width", type=lambda v: min_int(v, 640, "width"), default=1280)
    parser.add_argument("--height", type=lambda v: min_int(v, 360, "height"), default=720)
    parser.add_argument("--fps", type=lambda v: min_int(v, 12, "fps"), default=30)
    parser.add_argument("--browser", choices=["auto", "chrome", "edge"], default="auto")
    parser.add_argument("--browser-path", default="")
    parser.add_argument("--show-browser", action="store_true")
    parser.add_argument("--show-mouse-overlay", action="store_true", default=True)
    parser.add_argument("--hide-mouse-overlay", dest="show_mouse_overlay", action="store_false")
    parser.add_argument("--pre-click-delay-seconds", type=float, default=1.0)
    parser.add_argument("--ffmpeg-path", default="")
    parser.add_argument("--generate-fallback-copies", action="store_true")
    parser.add_argument("--print-schema", action="store_true")
    return parser.parse_args(argv)


def parse_pages(raw_value: str) -> list[str]:
    pages = [item.strip() for item in raw_value.split(",")]
    cleaned = [item for item in pages if item]
    if not cleaned:
        raise RuntimeError("Page list is empty.")
    return cleaned


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
    except Exception as exc:  # pragma: no cover - only hit when dependency missing/corrupt.
        raise RuntimeError(
            "Could not resolve ffmpeg. Install ffmpeg or pass --ffmpeg-path."
        ) from exc


def run_ffmpeg(ffmpeg_exe: str, args: Iterable[str]) -> None:
    cmd = [ffmpeg_exe, *args]
    process = subprocess.run(cmd, check=False)
    if process.returncode != 0:
        raise RuntimeError(f"ffmpeg failed with exit code {process.returncode}")


def transcode_webm_to_mp4(ffmpeg_exe: str, source_webm: Path, target_mp4: Path, fps: int) -> None:
    target_mp4.parent.mkdir(parents=True, exist_ok=True)
    run_ffmpeg(
        ffmpeg_exe,
        [
            "-y",
            "-i",
            str(source_webm),
            "-r",
            str(fps),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-an",
            str(target_mp4),
        ],
    )


def probe_video_duration_seconds(video_path: Path) -> float:
    try:
        import imageio_ffmpeg

        _frames, seconds = imageio_ffmpeg.count_frames_and_secs(str(video_path))
        return float(seconds)
    except Exception as exc:  # pragma: no cover - dependency/runtime specific.
        raise RuntimeError(f"Could not read video duration for: {video_path}") from exc


def build_cursor_overlay_filter(cursor_events: list[dict[str, float | str]], duration_seconds: float) -> str:
    if duration_seconds <= 0.0:
        return ""

    points = [event for event in cursor_events if "x" in event and "y" in event and "t" in event]
    if not points:
        return ""

    filters: list[str] = []
    for index, event in enumerate(points):
        start = max(float(event["t"]), 0.0)
        next_time = duration_seconds
        if index + 1 < len(points):
            next_time = max(float(points[index + 1]["t"]), start + 0.03)
        end = min(next_time, duration_seconds)
        if end <= start:
            continue

        x = int(round(float(event["x"])))
        y = int(round(float(event["y"])))
        enable = f"between(t\\,{start:.3f}\\,{end:.3f})"
        filters.append(
            "drawbox="
            f"x={x - 11}:y={y - 11}:w=22:h=22:color=black@0.58:t=2:enable={enable}"
        )
        filters.append(
            "drawbox="
            f"x={x - 8}:y={y - 8}:w=16:h=16:color=yellow@0.72:t=2:enable={enable}"
        )

    for event in points:
        if str(event.get("kind", "")) != "click":
            continue
        click_start = max(float(event["t"]), 0.0)
        click_end = min(click_start + 0.55, duration_seconds)
        if click_end <= click_start:
            continue

        x = int(round(float(event["x"])))
        y = int(round(float(event["y"])))
        enable = f"between(t\\,{click_start:.3f}\\,{click_end:.3f})"
        filters.append(
            "drawbox="
            f"x={x - 30}:y={y - 30}:w=60:h=60:color=red@0.38:t=3:enable={enable}"
        )

    return ",".join(filters)


def annotate_cursor_on_mp4(
    ffmpeg_exe: str,
    video_path: Path,
    cursor_events: list[dict[str, float | str]],
    fps: int,
) -> None:
    if not cursor_events:
        return

    duration_seconds = probe_video_duration_seconds(video_path)
    filter_value = build_cursor_overlay_filter(cursor_events, duration_seconds=duration_seconds)
    if not filter_value:
        return

    temp_output = video_path.with_name(f"{video_path.stem}.cursor.tmp.mp4")
    run_ffmpeg(
        ffmpeg_exe,
        [
            "-y",
            "-i",
            str(video_path),
            "-vf",
            filter_value,
            "-r",
            str(fps),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "21",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-an",
            str(temp_output),
        ],
    )
    shutil.move(str(temp_output), str(video_path))


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


class QuietHTTPServer(ThreadingHTTPServer):
    def handle_error(self, request, client_address) -> None:  # noqa: ANN001
        return


@contextmanager
def local_http_server(root_dir: Path):
    root_dir = root_dir.resolve()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    handler = partial(QuietHandler, directory=str(root_dir))
    server = QuietHTTPServer(("127.0.0.1", port), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}/"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2.0)


def default_browser_paths() -> dict[str, list[Path]]:
    return {
        "chrome": [
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            Path("/usr/bin/google-chrome"),
            Path("/usr/bin/google-chrome-stable"),
            Path("/snap/bin/chromium"),
        ],
        "edge": [
            Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
            Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
            Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
            Path("/usr/bin/microsoft-edge"),
            Path("/usr/bin/microsoft-edge-stable"),
        ],
    }


def resolve_browser_executable(browser_name: str) -> str | None:
    paths = default_browser_paths().get(browser_name, [])
    for path in paths:
        if path.exists():
            return str(path.resolve())
    command_candidates = {
        "chrome": ["chrome", "google-chrome", "chromium"],
        "edge": ["msedge", "microsoft-edge"],
    }.get(browser_name, [])
    for command in command_candidates:
        resolved = shutil.which(command)
        if resolved:
            return resolved
    return None


def launch_browser(playwright, browser: str, browser_path: str, headless: bool):
    launch_args = {
        "headless": headless,
        "args": ["--disable-dev-shm-usage"],
    }
    failures: list[str] = []

    if browser_path:
        try:
            return playwright.chromium.launch(executable_path=browser_path, **launch_args)
        except Exception as exc:  # pragma: no cover - environment dependent.
            failures.append(f"explicit-path({browser_path}): {exc}")

    preferences: list[str]
    if browser == "auto":
        preferences = ["chrome", "edge"]
    else:
        preferences = [browser]

    for name in preferences:
        channel = "chrome" if name == "chrome" else "msedge"
        try:
            return playwright.chromium.launch(channel=channel, **launch_args)
        except Exception as exc:  # pragma: no cover - environment dependent.
            failures.append(f"channel({channel}): {exc}")

        executable = resolve_browser_executable(name)
        if executable:
            try:
                return playwright.chromium.launch(executable_path=executable, **launch_args)
            except Exception as exc:  # pragma: no cover - environment dependent.
                failures.append(f"executable({executable}): {exc}")

    try:
        return playwright.chromium.launch(**launch_args)
    except Exception as exc:  # pragma: no cover - environment dependent.
        failures.append(f"bundled-chromium: {exc}")
        joined = "; ".join(failures)
        raise RuntimeError(
            "Could not launch browser for recording. "
            f"Attempts: {joined}. Provide --browser-path if needed."
        ) from exc


def smooth_scroll(page, pixels: int, duration_seconds: float, steps: int) -> None:
    if steps <= 0:
        return
    step_pixels = pixels / steps
    delay = max(duration_seconds / steps, 0.01)
    for _ in range(steps):
        page.evaluate("(value) => window.scrollBy(0, value)", step_pixels)
        page.wait_for_timeout(int(delay * 1000))


def ensure_mouse_overlay(page) -> None:
    page.evaluate(
        """() => {
            const id = "__demo_mouse_overlay__";
            if (window.__demoMouseMove && document.getElementById(id)) {
                return;
            }
            const cursor = document.createElement("div");
            cursor.id = id;
            cursor.style.position = "fixed";
            cursor.style.left = "0";
            cursor.style.top = "0";
            cursor.style.width = "22px";
            cursor.style.height = "22px";
            cursor.style.border = "2px solid rgba(0,0,0,0.62)";
            cursor.style.borderRadius = "50%";
            cursor.style.background = "transparent";
            cursor.style.boxSizing = "border-box";
            cursor.style.pointerEvents = "none";
            cursor.style.zIndex = "2147483647";
            cursor.style.boxShadow = "0 0 0 1px rgba(255,230,0,0.65)";
            cursor.style.transform = "translate(48px, 48px)";
            cursor.style.transition = "transform 160ms linear";
            document.body.appendChild(cursor);

            const ring = document.createElement("div");
            ring.style.position = "fixed";
            ring.style.left = "0";
            ring.style.top = "0";
            ring.style.width = "58px";
            ring.style.height = "58px";
            ring.style.border = "3px solid rgba(255,60,60,0.40)";
            ring.style.borderRadius = "50%";
            ring.style.pointerEvents = "none";
            ring.style.zIndex = "2147483647";
            ring.style.opacity = "0";
            ring.style.transform = "translate(31px, 31px) scale(0.74)";
            ring.style.transition = "opacity 120ms linear, transform 320ms ease-out";
            document.body.appendChild(ring);

            window.__demoMouseMove = (x, y) => {
                cursor.style.transform = `translate(${x}px, ${y}px)`;
                ring.style.transform = `translate(${x - 17}px, ${y - 17}px) scale(0.74)`;
            };

            window.__demoMouseClick = () => {
                ring.style.opacity = "1";
                ring.style.transform = ring.style.transform.replace("scale(0.74)", "scale(1.16)");
                setTimeout(() => {
                    ring.style.opacity = "0";
                    ring.style.transform = ring.style.transform.replace("scale(1.16)", "scale(0.74)");
                }, 520);
            };
        }"""
    )


def move_mouse_to_selector(page, selector: str, timeout_ms: int) -> tuple[float, float] | None:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    try:
        box = page.locator(selector).first.bounding_box(timeout=timeout_ms)
    except PlaywrightTimeoutError:
        return None
    if box is None:
        return None
    center_x = float(box["x"]) + float(box["width"]) / 2.0
    center_y = float(box["y"]) + float(box["height"]) / 2.0
    page.evaluate("([x, y]) => window.__demoMouseMove?.(x, y)", [center_x, center_y])
    return center_x, center_y


def run_actions(
    page,
    base_url: str,
    actions: list[dict],
    *,
    show_mouse_overlay: bool,
    pre_click_delay_seconds: float,
    cursor_events: list[dict[str, float | str]] | None = None,
    time_origin: float | None = None,
) -> None:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    def track_cursor(x: float, y: float, kind: str = "move") -> None:
        if cursor_events is None:
            return
        if time_origin is None:
            timestamp = 0.0
        else:
            timestamp = max(time.monotonic() - time_origin, 0.0)
        cursor_events.append({"t": timestamp, "x": float(x), "y": float(y), "kind": kind})

    for action in actions:
        action_type = action["type"]
        if action_type == "goto":
            target = action["path"]
            page.goto(urljoin(base_url, target), wait_until="networkidle")
            if show_mouse_overlay:
                ensure_mouse_overlay(page)
                page.evaluate("() => window.__demoMouseMove?.(56, 56)")
                track_cursor(56.0, 56.0, kind="move")
            wait_ms = int(action.get("wait_seconds", 0) * 1000)
            if wait_ms > 0:
                page.wait_for_timeout(wait_ms)
            continue

        if action_type == "wait":
            page.wait_for_timeout(int(action["seconds"] * 1000))
            continue

        if action_type == "scroll":
            smooth_scroll(
                page,
                pixels=int(action["pixels"]),
                duration_seconds=float(action["duration_seconds"]),
                steps=int(action["steps"]),
            )
            continue

        if action_type == "click":
            selector = action["selector"]
            optional = bool(action.get("optional", False))
            timeout_ms = int(action.get("timeout_ms", 2000))
            has_target = True
            if show_mouse_overlay:
                ensure_mouse_overlay(page)
                target_pos = move_mouse_to_selector(page, selector=selector, timeout_ms=timeout_ms)
                has_target = target_pos is not None
                if target_pos is not None:
                    track_cursor(target_pos[0], target_pos[1], kind="move")
                    page.evaluate("() => window.__demoMouseClick?.()")
                    track_cursor(target_pos[0], target_pos[1], kind="click")
            if not has_target and optional:
                continue
            delay_ms = int(max(pre_click_delay_seconds, 0.0) * 1000)
            if delay_ms > 0:
                page.wait_for_timeout(delay_ms)
            try:
                page.click(selector, timeout=timeout_ms)
            except PlaywrightTimeoutError:
                if not optional:
                    raise
            wait_ms = int(action.get("wait_seconds", 0) * 1000)
            if wait_ms > 0:
                page.wait_for_timeout(wait_ms)
            continue

        raise RuntimeError(f"Unsupported action type: {action_type}")


def maybe_install_playwright_runtime(error: Exception) -> bool:
    error_text = str(error).lower()
    runtime_missing = "playwright install" in error_text or "ffmpeg-win64.exe" in error_text
    if not runtime_missing:
        return False
    print("Playwright runtime is missing; installing chromium runtime bundle...", file=sys.stderr)
    process = subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=False)
    return process.returncode == 0


def record_actions_to_webm(
    base_url: str,
    actions: list[dict],
    width: int,
    height: int,
    browser: str,
    browser_path: str,
    headless: bool,
    show_mouse_overlay: bool,
    pre_click_delay_seconds: float,
) -> tuple[Path, list[dict[str, float | str]]]:
    def _record_once() -> tuple[Path, list[dict[str, float | str]]]:
        with tempfile.TemporaryDirectory(prefix="browser-video-") as tmpdir:
            output_dir = Path(tmpdir)
            from playwright.sync_api import sync_playwright

            with sync_playwright() as playwright:
                browser_instance = launch_browser(playwright, browser=browser, browser_path=browser_path, headless=headless)
                context = browser_instance.new_context(
                    viewport={"width": width, "height": height},
                    record_video_dir=str(output_dir),
                    record_video_size={"width": width, "height": height},
                )
                page = context.new_page()
                cursor_events: list[dict[str, float | str]] = []
                action_start = time.monotonic()
                run_actions(
                    page,
                    base_url=base_url,
                    actions=actions,
                    show_mouse_overlay=show_mouse_overlay,
                    pre_click_delay_seconds=pre_click_delay_seconds,
                    cursor_events=cursor_events,
                    time_origin=action_start,
                )
                page.wait_for_timeout(300)
                video_handle = page.video
                context.close()
                browser_instance.close()

                if video_handle is None:
                    raise RuntimeError("Playwright did not produce a video handle.")

                recorded = Path(video_handle.path())
                final_webm = output_dir / "recording.webm"
                shutil.copy2(recorded, final_webm)
                temp_copy = Path(tempfile.gettempdir()) / f"browser-video-{int(time.time() * 1000)}.webm"
                shutil.copy2(final_webm, temp_copy)
                return temp_copy, cursor_events

    try:
        return _record_once()
    except Exception as exc:
        if not maybe_install_playwright_runtime(exc):
            raise
    return _record_once()


def build_outcome_actions(pages: list[str]) -> list[dict]:
    actions: list[dict] = []
    for index, page in enumerate(pages):
        actions.append({"type": "goto", "path": page, "wait_seconds": 0.8})
        if index == 0:
            actions.append(
                {
                    "type": "click",
                    "selector": "button[data-showcase-target='process']",
                    "optional": True,
                    "wait_seconds": 0.6,
                }
            )
            actions.append(
                {
                    "type": "click",
                    "selector": "button[data-showcase-target='outcome']",
                    "optional": True,
                    "wait_seconds": 0.4,
                }
            )
        actions.append({"type": "scroll", "pixels": 820, "duration_seconds": 2.7, "steps": 36})
        actions.append({"type": "scroll", "pixels": -540, "duration_seconds": 1.5, "steps": 24})
    actions.append({"type": "wait", "seconds": 1.0})
    return actions


def build_process_actions(pages: list[str]) -> list[dict]:
    actions: list[dict] = []
    actions.append({"type": "goto", "path": "index.html", "wait_seconds": 0.7})
    actions.append(
        {
            "type": "click",
            "selector": "button[data-showcase-target='process']",
            "optional": True,
            "wait_seconds": 0.5,
        }
    )
    for page in pages:
        actions.append({"type": "goto", "path": page, "wait_seconds": 0.4})
        actions.append({"type": "scroll", "pixels": 500, "duration_seconds": 1.0, "steps": 18})
    actions.append({"type": "wait", "seconds": 0.6})
    return actions


def build_tour_actions(pages: list[str]) -> list[dict]:
    actions: list[dict] = []
    for page in pages:
        actions.append({"type": "goto", "path": page, "wait_seconds": 0.7})
        actions.append({"type": "scroll", "pixels": 780, "duration_seconds": 2.1, "steps": 30})
    actions.append({"type": "wait", "seconds": 0.9})
    return actions


def sanitize_point(text_value: str) -> str:
    text_value = text_value.strip()
    text_value = re.sub(r"^[\-\*\d\.\)\s]+", "", text_value)
    return re.sub(r"\s+", " ", text_value).strip()


def split_concept_points(concept: str) -> list[str]:
    lines = [sanitize_point(line) for line in concept.splitlines()]
    lines = [line for line in lines if line]
    if len(lines) > 1:
        return lines

    compact = " ".join(lines) if lines else concept.strip()
    sentence_parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", compact) if part.strip()]
    if sentence_parts:
        return sentence_parts
    if compact:
        return [compact]
    return []


def build_slides(concept: str, title: str, points_per_slide: int) -> list[dict]:
    points = split_concept_points(concept)
    if not points:
        points = ["Define your concept using --concept or --concept-file."]

    slides: list[dict] = []
    for index in range(0, len(points), points_per_slide):
        chunk = points[index : index + points_per_slide]
        part_number = (index // points_per_slide) + 1
        headline = title if len(points) <= points_per_slide else f"{title} - Part {part_number}"
        slides.append({"title": headline, "bullets": chunk})
    return slides


def write_slideshow_html(html_path: Path, slides: list[dict], slide_duration: float) -> None:
    payload = json.dumps(slides, ensure_ascii=True)
    template = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Concept Slideshow</title>
  <style>
    :root {{
      color-scheme: light;
      --bg-a: #0b1b2b;
      --bg-b: #204a6f;
      --card-bg: rgba(246, 250, 255, 0.95);
      --ink: #0a2540;
      --muted: #315879;
      --accent: #0e7490;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      font-family: "Segoe UI", Tahoma, sans-serif;
      background:
        radial-gradient(circle at 15% 20%, rgba(255, 255, 255, 0.2), transparent 40%),
        linear-gradient(130deg, var(--bg-a), var(--bg-b));
      color: var(--ink);
    }}
    .deck {{
      width: min(980px, 90vw);
      min-height: min(590px, 82vh);
      background: var(--card-bg);
      border-radius: 26px;
      box-shadow: 0 25px 80px rgba(0, 0, 0, 0.32);
      padding: 52px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      animation: rise 0.5s ease;
    }}
    @keyframes rise {{
      from {{ transform: translateY(20px); opacity: 0; }}
      to {{ transform: translateY(0); opacity: 1; }}
    }}
    h1 {{
      margin: 0 0 12px;
      font-size: clamp(1.8rem, 2.8vw, 2.6rem);
      color: var(--ink);
      line-height: 1.2;
    }}
    ul {{
      margin: 0;
      padding-left: 22px;
      display: grid;
      gap: 14px;
      color: var(--muted);
      font-size: clamp(1rem, 1.6vw, 1.3rem);
      line-height: 1.35;
    }}
    .meta {{
      margin-top: 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.96rem;
      color: var(--accent);
      letter-spacing: 0.03em;
      text-transform: uppercase;
    }}
  </style>
</head>
<body>
  <main class="deck">
    <section>
      <h1 id="slide-title"></h1>
      <ul id="slide-list"></ul>
    </section>
    <div class="meta">
      <span>Concept to slideshow</span>
      <span id="slide-index"></span>
    </div>
  </main>

  <script>
    const slides = {payload};
    const slideMs = {int(slide_duration * 1000)};
    const titleNode = document.getElementById("slide-title");
    const listNode = document.getElementById("slide-list");
    const indexNode = document.getElementById("slide-index");
    let index = 0;

    function renderSlide() {{
      const slide = slides[index];
      titleNode.textContent = slide.title;
      listNode.innerHTML = "";
      for (const point of slide.bullets) {{
        const li = document.createElement("li");
        li.textContent = point;
        listNode.appendChild(li);
      }}
      indexNode.textContent = `slide ${{index + 1}} / ${{slides.length}}`;
    }}

    renderSlide();
    setInterval(() => {{
      index = (index + 1) % slides.length;
      renderSlide();
    }}, slideMs);
  </script>
</body>
</html>
"""
    html_path.write_text(template, encoding="utf-8")


def resolve_concept(args: argparse.Namespace) -> str:
    if args.concept.strip():
        return args.concept.strip()
    if args.concept_file:
        concept_path = Path(args.concept_file)
        if not concept_path.is_absolute():
            concept_path = (PROJECT_ROOT / concept_path).resolve()
        if not concept_path.exists():
            raise RuntimeError(f"Concept file does not exist: {concept_path}")
        return concept_path.read_text(encoding="utf-8").strip()
    raise RuntimeError("concept-slideshow mode requires --concept or --concept-file.")


def create_video_from_actions(
    base_url: str,
    actions: list[dict],
    output_path: Path,
    args: argparse.Namespace,
) -> None:
    webm_path, cursor_events = record_actions_to_webm(
        base_url=base_url,
        actions=actions,
        width=args.width,
        height=args.height,
        browser=args.browser,
        browser_path=args.browser_path,
        headless=not args.show_browser,
        show_mouse_overlay=args.show_mouse_overlay,
        pre_click_delay_seconds=max(float(args.pre_click_delay_seconds), 0.0),
    )
    try:
        ffmpeg_exe = resolve_ffmpeg(args.ffmpeg_path)
        transcode_webm_to_mp4(ffmpeg_exe=ffmpeg_exe, source_webm=webm_path, target_mp4=output_path, fps=args.fps)
        if args.show_mouse_overlay:
            annotate_cursor_on_mp4(ffmpeg_exe=ffmpeg_exe, video_path=output_path, cursor_events=cursor_events, fps=args.fps)
    finally:
        if webm_path.exists():
            webm_path.unlink()


def run_site_videos(args: argparse.Namespace) -> list[Path]:
    site_dir = Path(args.site_dir).resolve()
    media_dir = Path(args.media_dir).resolve()
    media_dir.mkdir(parents=True, exist_ok=True)
    if not site_dir.exists():
        raise RuntimeError(f"site directory does not exist: {site_dir}")

    pages = parse_pages(args.site_pages)
    outputs: list[Path] = []
    with local_http_server(site_dir) as base_url:
        if args.output_mode in ("both", "outcome"):
            outcome_output = media_dir / "tutorial-outcome.mp4"
            print(f"Recording tutorial outcome video to: {outcome_output}")
            create_video_from_actions(base_url, build_outcome_actions(pages), outcome_output, args)
            outputs.append(outcome_output)

        if args.output_mode in ("both", "process"):
            process_output = media_dir / "learning-process-fast.mp4"
            print(f"Recording learning process video to: {process_output}")
            create_video_from_actions(base_url, build_process_actions(pages), process_output, args)
            outputs.append(process_output)

    if args.generate_fallback_copies:
        for source, fallback_name in [
            (media_dir / "tutorial-outcome.mp4", "tutorial-outcome-fallback.mp4"),
            (media_dir / "learning-process-fast.mp4", "learning-process-fast-fallback.mp4"),
        ]:
            if source.exists():
                target = media_dir / fallback_name
                shutil.copy2(source, target)
                outputs.append(target)
                print(f"Created fallback copy: {target}")
    return outputs


def run_html_tour(args: argparse.Namespace) -> list[Path]:
    site_dir = Path(args.site_dir).resolve()
    media_dir = Path(args.media_dir).resolve()
    media_dir.mkdir(parents=True, exist_ok=True)
    if not site_dir.exists():
        raise RuntimeError(f"site directory does not exist: {site_dir}")

    output_path = media_dir / args.tour_output
    pages = parse_pages(args.tour_pages)
    with local_http_server(site_dir) as base_url:
        print(f"Recording html tour to: {output_path}")
        create_video_from_actions(base_url, build_tour_actions(pages), output_path, args)
    return [output_path]


def run_concept_slideshow(args: argparse.Namespace) -> list[Path]:
    concept = resolve_concept(args)
    slides = build_slides(concept=concept, title=args.slideshow_title, points_per_slide=args.points_per_slide)
    media_dir = Path(args.media_dir).resolve()
    media_dir.mkdir(parents=True, exist_ok=True)
    output_path = media_dir / args.slideshow_output

    with tempfile.TemporaryDirectory(prefix="concept-slideshow-") as tmpdir:
        temp_root = Path(tmpdir)
        html_path = temp_root / "slides.html"
        write_slideshow_html(html_path, slides=slides, slide_duration=args.slide_duration)

        total_seconds = len(slides) * args.slide_duration + 1.0
        actions = [{"type": "goto", "path": "slides.html", "wait_seconds": 0.7}, {"type": "wait", "seconds": total_seconds}]
        with local_http_server(temp_root) as base_url:
            print(f"Recording concept slideshow to: {output_path}")
            create_video_from_actions(base_url, actions, output_path, args)
    return [output_path]


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.print_schema:
        print(json.dumps(tool_schema(), indent=2))
        return 0

    if args.mode == "site-videos":
        outputs = run_site_videos(args)
    elif args.mode == "html-tour":
        outputs = run_html_tour(args)
    else:
        outputs = run_concept_slideshow(args)

    print()
    print("Generated files:")
    for output in outputs:
        if output.exists():
            print(f" - {output} ({output.stat().st_size:,} bytes)")
        else:
            print(f" - {output} (missing)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
