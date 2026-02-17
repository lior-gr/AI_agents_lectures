#!/usr/bin/env python3
"""Record browser-based tutorial videos and concept slideshows."""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import wave
from array import array
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Iterable
from urllib.parse import urljoin


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SITE_DIR = PROJECT_ROOT / "Lessons" / "tutorial_site"
DEFAULT_MEDIA_DIR = DEFAULT_SITE_DIR / "media"
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
            "encode-profile": {
                "type": "string",
                "required": False,
                "default": "draft",
                "enum": ["draft", "release"],
                "description": "Encoding quality/speed profile for MP4 output.",
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
    parser.add_argument("--encode-profile", choices=sorted(ENCODE_PROFILES.keys()), default="draft")
    parser.add_argument("--browser", choices=["auto", "chrome", "edge"], default="auto")
    parser.add_argument("--browser-path", default="")
    parser.add_argument("--show-browser", action="store_true")
    parser.add_argument("--show-mouse-overlay", action="store_true", default=True)
    parser.add_argument("--hide-mouse-overlay", dest="show_mouse_overlay", action="store_false")
    parser.add_argument("--pre-click-delay-seconds", type=float, default=1.0)
    parser.add_argument("--ffmpeg-path", default="")
    parser.add_argument("--print-schema", action="store_true")
    return parser.parse_args(argv)


def parse_pages(raw_value: str) -> list[str]:
    pages = [item.strip() for item in raw_value.split(",")]
    cleaned = [item for item in pages if item]
    if not cleaned:
        raise RuntimeError("Page list is empty.")
    return cleaned


def sidecar_paths(video_path: Path) -> tuple[Path, Path]:
    base = video_path.with_suffix("")
    return base.with_suffix(".directives.md"), base.with_suffix(".story.md")


def encode_profile_settings(profile_name: str) -> dict[str, str]:
    settings = ENCODE_PROFILES.get(profile_name)
    if not settings:
        valid = ", ".join(sorted(ENCODE_PROFILES.keys()))
        raise RuntimeError(f"Unknown encode profile '{profile_name}'. Expected one of: {valid}")
    return settings


def describe_action(action: dict) -> str:
    action_type = str(action.get("type", "")).strip().lower()
    if action_type == "goto":
        return f"Open `{action.get('path', '')}` and wait {float(action.get('wait_seconds', 0.0)):.1f}s."
    if action_type == "click":
        selector = str(action.get("selector", ""))
        wait_seconds = float(action.get("wait_seconds", 0.0))
        optional = bool(action.get("optional", False))
        optional_note = " (optional)" if optional else ""
        return f"Click `{selector}`{optional_note}, then wait {wait_seconds:.1f}s."
    if action_type == "scroll":
        pixels = int(action.get("pixels", 0))
        duration = float(action.get("duration_seconds", 0.0))
        steps = int(action.get("steps", 0))
        direction = "down" if pixels >= 0 else "up"
        return f"Scroll {direction} by {abs(pixels)}px over {duration:.1f}s in {steps} steps."
    if action_type == "wait":
        return f"Idle for {float(action.get('seconds', 0.0)):.1f}s."
    if action_type == "focus":
        selector = str(action.get("selector", ""))
        wait_seconds = float(action.get("wait_seconds", 0.0))
        optional = bool(action.get("optional", False))
        optional_note = " (optional)" if optional else ""
        return f"Focus on `{selector}`{optional_note} with spotlight, then hold for {wait_seconds:.1f}s."
    return json.dumps(action, ensure_ascii=True)


def write_video_sidecars(
    *,
    video_path: Path,
    workflow_name: str,
    story_summary: str,
    args: argparse.Namespace,
    actions: list[dict],
    performance: dict[str, float | int | bool] | None = None,
    story_notes: list[str] | None = None,
) -> tuple[Path, Path]:
    directives_path, story_path = sidecar_paths(video_path)
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    encode_settings = encode_profile_settings(str(args.encode_profile))

    directives_lines = [
        f"# Video Directives: {video_path.name}",
        "",
        f"- Generated (UTC): `{generated_at}`",
        f"- Tool: `browser_video_creator`",
        f"- Workflow: `{workflow_name}`",
        f"- Output video: `{video_path}`",
        "",
        "## Capture Directives",
        f"- Resolution: `{args.width}x{args.height}`",
        f"- FPS: `{args.fps}`",
        f"- Encode profile: `{args.encode_profile}`",
        (
            f"- MP4 codec settings: `libx264 preset={encode_settings['video_preset']} "
            f"crf={encode_settings['video_crf']} pix_fmt=yuv420p`"
        ),
        f"- MP4 audio settings: `aac {encode_settings['audio_bitrate']} 48kHz`",
        f"- Browser preference: `{args.browser}`",
        f"- Show browser window: `{bool(args.show_browser)}`",
        f"- Mouse overlay: `{bool(args.show_mouse_overlay)}`",
        f"- Pre-click delay (seconds): `{max(float(args.pre_click_delay_seconds), 0.0):.2f}`",
        "- Interaction audio: soft click and scroll sounds synchronized to actions",
        "",
        "## Interaction Script",
    ]
    for index, action in enumerate(actions, start=1):
        directives_lines.append(f"{index}. {describe_action(action)}")
    directives_lines.extend(
        [
            "",
            "## Iteration Knobs",
            "- To speed up or slow down pacing: adjust action waits/scroll durations in the tool workflow.",
            "- To change framing/clarity: tune `--width`, `--height`, and `--fps`.",
            "- To change interaction emphasis: tune `--pre-click-delay-seconds` and mouse overlay settings.",
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
        story_summary.strip(),
        "",
        "## Story Beats",
    ]
    for index, action in enumerate(actions, start=1):
        story_lines.append(f"{index}. {describe_action(action)}")
    if story_notes:
        story_lines.extend(["", "## Story Notes"])
        for note in story_notes:
            story_lines.append(f"- {note}")
    story_lines.extend(
        [
            "",
            "## How To Steer Next Iteration",
            "- Compare the current video output with these beats and directives.",
            "- Edit this story or directives file first, then update tool arguments/workflow actions to match.",
            "- Regenerate and repeat until visual pacing and clarity match the intended story.",
        ]
    )
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
                f"- Effects step (seconds): `{float(performance.get('overlay_seconds', 0.0)):.3f}`",
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


def transcode_webm_to_mp4(
    ffmpeg_exe: str,
    source_webm: Path,
    target_mp4: Path,
    fps: int,
    *,
    video_preset: str,
    video_crf: str,
) -> None:
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
            video_preset,
            "-crf",
            video_crf,
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-an",
            str(target_mp4),
        ],
    )


def synthesize_interaction_audio(
    audio_path: Path,
    *,
    duration_seconds: float,
    interaction_events: list[dict[str, float | str]],
    include_background_music: bool = False,
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
    ) -> None:
        start_sample = int(max(event_time, 0.0) * sample_rate)
        if start_sample >= total_samples:
            return
        burst_samples = max(int(sample_rate * duration), 1)
        phase = 0.31 * float((event_index % 9) + 1)
        for n in range(burst_samples):
            sample_index = start_sample + n
            if sample_index >= total_samples:
                break
            t = n / float(sample_rate)
            envelope = math.exp(-decay * t)
            tonal = (
                tonal_mix * math.sin(2.0 * math.pi * freq_a * t + phase)
                + (1.0 - tonal_mix) * math.sin(2.0 * math.pi * freq_b * t + phase * 0.67)
            )
            noise_seed = math.sin((event_index + 3) * (n + 29) * 12.9898) * 43758.5453
            noise = (noise_seed - math.floor(noise_seed)) * 2.0 - 1.0
            sample_value = ((1.0 - noise_mix) * tonal + noise_mix * noise) * envelope * amplitude
            mix[sample_index] += sample_value

    click_events = [event for event in interaction_events if str(event.get("kind", "")) == "click"]
    scroll_events = [event for event in interaction_events if str(event.get("kind", "")) == "scroll"]

    for index, event in enumerate(click_events):
        add_burst(
            float(event.get("t", 0.0)),
            event_index=index,
            duration=0.085,
            amplitude=0.075,
            decay=46.0,
            freq_a=680.0 + float((index % 2) * 34),
            freq_b=1620.0 + float((index % 3) * 58),
            tonal_mix=0.60,
            noise_mix=0.16,
        )

    scroll_tick_index = 0
    for event in scroll_events:
        start_time = max(float(event.get("t", 0.0)), 0.0)
        duration = max(float(event.get("duration", 0.0)), 0.0)
        if duration <= 0.0:
            continue
        step_count = max(int(event.get("step_count", 0)), 0)
        tick_times: list[float] = []
        if step_count > 1:
            max_ticks = 18
            stride = max(step_count // max_ticks, 1)
            for step_idx in range(0, step_count, stride):
                progress = step_idx / float(step_count - 1)
                tick_times.append(start_time + duration * progress)
        else:
            tick_gap = 0.135
            tick_count = max(int(duration / tick_gap), 1)
            for tick in range(tick_count):
                tick_times.append(start_time + min(tick * tick_gap, duration))
        for tick_time in tick_times:
            add_burst(
                tick_time,
                event_index=scroll_tick_index,
                duration=0.048,
                amplitude=0.028,
                decay=62.0,
                freq_a=900.0 + float((scroll_tick_index % 4) * 22),
                freq_b=1240.0 + float((scroll_tick_index % 3) * 31),
                tonal_mix=0.56,
                noise_mix=0.22,
            )
            scroll_tick_index += 1

    if include_background_music:
        # Procedural upbeat background bed (no external assets).
        tempo_bpm = 116.0
        beats_per_second = tempo_bpm / 60.0
        chords = [
            (261.63, 329.63, 392.00),  # C major
            (392.00, 493.88, 587.33),  # G major
            (440.00, 523.25, 659.25),  # A minor (light color)
            (349.23, 440.00, 523.25),  # F major
        ]
        arp_pattern = (0, 1, 2, 1)
        for i in range(total_samples):
            t = i / float(sample_rate)
            beats = t * beats_per_second
            bar_index = int(beats / 4.0) % len(chords)
            chord = chords[bar_index]

            beat_pos = beats - math.floor(beats)
            eighth = beats * 2.0
            eighth_pos = eighth - math.floor(eighth)
            sixteenth = beats * 4.0
            sixteenth_pos = sixteenth - math.floor(sixteenth)

            # Warm harmonic pad.
            shimmer = 0.88 + 0.12 * math.sin(2.0 * math.pi * 0.18 * t)
            pad = (
                math.sin(2.0 * math.pi * chord[0] * t)
                + 0.72 * math.sin(2.0 * math.pi * chord[1] * t + 0.32)
                + 0.58 * math.sin(2.0 * math.pi * chord[2] * t + 0.78)
            ) / 2.30

            # Rhythmic bass pulse.
            bass_env = 0.52 + 0.48 * math.exp(-7.5 * beat_pos)
            bass = math.sin(2.0 * math.pi * (chord[0] * 0.5) * t + 0.18) * bass_env

            # Bright arpeggio on eighth notes.
            arp_note = chord[arp_pattern[int(math.floor(eighth)) % len(arp_pattern)]]
            arp_env = math.exp(-12.5 * eighth_pos)
            arp = math.sin(2.0 * math.pi * (arp_note * 2.0) * t + 0.26) * arp_env

            # Soft shaker-like texture on sixteenth notes.
            noise_seed = math.sin((i + 19) * 12.9898) * 43758.5453
            noise = (noise_seed - math.floor(noise_seed)) * 2.0 - 1.0
            shaker = noise * math.exp(-24.0 * sixteenth_pos)

            mix[i] += (pad * 0.011 * shimmer) + (bass * 0.0085) + (arp * 0.0125) + (shaker * 0.0026)

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


def mux_audio_into_mp4(ffmpeg_exe: str, video_path: Path, audio_path: Path, *, audio_bitrate: str) -> None:
    if not audio_path.exists():
        return
    temp_output = video_path.with_name(f"{video_path.stem}.audio.tmp.mp4")
    run_ffmpeg(
        ffmpeg_exe,
        [
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            audio_bitrate,
            "-ar",
            "48000",
            "-shortest",
            "-movflags",
            "+faststart",
            str(temp_output),
        ],
    )
    shutil.move(str(temp_output), str(video_path))


def probe_video_duration_seconds(video_path: Path) -> float:
    try:
        import imageio_ffmpeg

        _frames, seconds = imageio_ffmpeg.count_frames_and_secs(str(video_path))
        return float(seconds)
    except Exception as exc:  # pragma: no cover - dependency/runtime specific.
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
    *,
    video_preset: str,
    video_crf: str,
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
            video_preset,
            "-crf",
            video_crf,
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


def ensure_focus_overlay(page) -> None:
    page.evaluate(
        """() => {
            const shadeId = "__demo_focus_shade__";
            const frameId = "__demo_focus_frame__";
            if (window.__demoFocusOn && document.getElementById(shadeId) && document.getElementById(frameId)) {
                return;
            }

            const styleId = "__demo_focus_style__";
            if (!document.getElementById(styleId)) {
                const style = document.createElement("style");
                style.id = styleId;
                style.textContent = `
                    .__demo_focus_target__ {
                        position: relative !important;
                        z-index: 2147483646 !important;
                        transition: box-shadow 220ms ease;
                        box-shadow:
                            0 0 0 2px rgba(104, 190, 255, 0.55),
                            0 16px 36px rgba(9, 31, 65, 0.26);
                    }
                `;
                document.head.appendChild(style);
            }

            const shade = document.createElement("div");
            shade.id = shadeId;
            shade.style.position = "fixed";
            shade.style.left = "0";
            shade.style.top = "0";
            shade.style.right = "0";
            shade.style.bottom = "0";
            shade.style.pointerEvents = "none";
            shade.style.background = "rgba(8, 20, 43, 0.18)";
            shade.style.opacity = "0";
            shade.style.transition = "opacity 180ms ease";
            shade.style.zIndex = "2147483644";
            document.body.appendChild(shade);

            const frame = document.createElement("div");
            frame.id = frameId;
            frame.style.position = "fixed";
            frame.style.left = "0";
            frame.style.top = "0";
            frame.style.width = "0";
            frame.style.height = "0";
            frame.style.pointerEvents = "none";
            frame.style.borderRadius = "14px";
            frame.style.border = "3px solid rgba(29, 155, 255, 0.82)";
            frame.style.boxShadow =
                "0 0 0 1px rgba(255,255,255,0.24), 0 14px 34px rgba(11, 37, 75, 0.28)";
            frame.style.opacity = "0";
            frame.style.transition =
                "left 220ms ease, top 220ms ease, width 220ms ease, height 220ms ease, opacity 160ms ease";
            frame.style.zIndex = "2147483645";
            document.body.appendChild(frame);

            window.__demoFocusTarget = null;
            window.__demoResolveTarget = (selector) => {
                const candidates = Array.from(document.querySelectorAll(selector));
                if (!candidates.length) {
                    return null;
                }
                const visible = candidates.find((node) => {
                    if (!(node instanceof Element)) {
                        return false;
                    }
                    const style = window.getComputedStyle(node);
                    if (style.display === "none" || style.visibility === "hidden" || Number(style.opacity || "1") === 0) {
                        return false;
                    }
                    const rect = node.getBoundingClientRect();
                    return rect.width >= 2 && rect.height >= 2;
                });
                return visible || candidates[0];
            };

            window.__demoFocusOn = (selector, options = {}) => {
                const target = window.__demoResolveTarget?.(selector);
                if (!target) {
                    return false;
                }
                if (window.__demoFocusTarget && window.__demoFocusTarget !== target) {
                    window.__demoFocusTarget.classList.remove("__demo_focus_target__");
                }

                const rect = target.getBoundingClientRect();
                const padding = Number.isFinite(options.padding) ? options.padding : 16;
                const zoom = Number.isFinite(options.zoom) ? options.zoom : 1.03;
                const dimOpacity = Number.isFinite(options.dim_opacity) ? options.dim_opacity : 0.18;
                const centerX = rect.left + rect.width / 2;
                const centerY = rect.top + rect.height / 2;
                const focusWidth = Math.max(10, rect.width * Math.max(zoom, 1.0));
                const focusHeight = Math.max(10, rect.height * Math.max(zoom, 1.0));
                const left = Math.max(centerX - (focusWidth / 2) - padding, 4);
                const top = Math.max(centerY - (focusHeight / 2) - padding, 4);
                const maxWidth = Math.max(window.innerWidth - left - 4, 12);
                const maxHeight = Math.max(window.innerHeight - top - 4, 12);
                const width = Math.min(focusWidth + padding * 2, maxWidth);
                const height = Math.min(focusHeight + padding * 2, maxHeight);

                shade.style.opacity = String(Math.max(0.0, Math.min(dimOpacity, 0.35)));
                frame.style.left = `${left}px`;
                frame.style.top = `${top}px`;
                frame.style.width = `${width}px`;
                frame.style.height = `${height}px`;
                frame.style.opacity = "1";

                target.classList.add("__demo_focus_target__");
                window.__demoFocusTarget = target;
                return true;
            };

            window.__demoFocusOff = () => {
                shade.style.opacity = "0";
                frame.style.opacity = "0";
                if (window.__demoFocusTarget) {
                    window.__demoFocusTarget.classList.remove("__demo_focus_target__");
                    window.__demoFocusTarget = null;
                }
            };
        }"""
    )


def ensure_mouse_overlay(page) -> None:
    ensure_focus_overlay(page)
    page.evaluate(
        """() => {
            const id = "__demo_mouse_overlay__";
            if (window.__demoMouseMove && document.getElementById(id)) {
                return;
            }
            document.documentElement.style.cursor = "none";
            document.body.style.cursor = "none";
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
            cursor.style.transition = "transform 200ms linear";
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


def move_mouse_to_selector(
    page, selector: str, timeout_ms: int, anchor: str = "center"
) -> tuple[float, float] | None:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    try:
        box = page.locator(selector).first.bounding_box(timeout=timeout_ms)
    except PlaywrightTimeoutError:
        return None
    if box is None:
        return None
    base_x = float(box["x"])
    base_y = float(box["y"])
    width = float(box["width"])
    height = float(box["height"])
    if anchor == "edge":
        offset_x = min(max(width * 0.20, 10.0), max(width - 10.0, 4.0))
        offset_y = min(max(height * 0.18, 10.0), max(height - 10.0, 4.0))
        center_x = base_x + offset_x
        center_y = base_y + offset_y
    else:
        center_x = base_x + width / 2.0
        center_y = base_y + height / 2.0
    page.evaluate("([x, y]) => window.__demoMouseMove?.(x, y)", [center_x, center_y])
    return center_x, center_y


def focus_selector(
    page,
    selector: str,
    timeout_ms: int,
    *,
    padding: float,
    zoom: float,
    dim_opacity: float,
    auto_scroll: bool,
) -> bool:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    locator = page.locator(selector).first
    try:
        locator.wait_for(state="visible", timeout=timeout_ms)
    except PlaywrightTimeoutError:
        return False

    if auto_scroll:
        try:
            locator.scroll_into_view_if_needed(timeout=timeout_ms)
        except PlaywrightTimeoutError:
            return False
        page.wait_for_timeout(120)
    try:
        box = locator.bounding_box(timeout=timeout_ms)
    except PlaywrightTimeoutError:
        return False
    if box is None:
        return False

    return bool(
        page.evaluate(
            """([sel, options]) => {
                return window.__demoFocusOn?.(sel, options) ?? false;
            }""",
            [
                selector,
                {
                    "padding": float(padding),
                    "zoom": float(zoom),
                    "dim_opacity": float(dim_opacity),
                },
            ],
        )
    )


def run_actions(
    page,
    base_url: str,
    actions: list[dict],
    *,
    show_mouse_overlay: bool,
    pre_click_delay_seconds: float,
    cursor_events: list[dict[str, float | str]] | None = None,
    interaction_events: list[dict[str, float | str]] | None = None,
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

    def track_interaction(kind: str, duration: float | None = None, step_count: int | None = None) -> None:
        if interaction_events is None:
            return
        if time_origin is None:
            timestamp = 0.0
        else:
            timestamp = max(time.monotonic() - time_origin, 0.0)
        event: dict[str, float | str] = {"t": timestamp, "kind": str(kind)}
        if duration is not None:
            event["duration"] = max(float(duration), 0.0)
        if step_count is not None:
            event["step_count"] = max(int(step_count), 0)
        interaction_events.append(event)

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
            scroll_duration_seconds = float(action["duration_seconds"])
            scroll_steps = int(action["steps"])
            track_interaction("scroll", duration=scroll_duration_seconds, step_count=scroll_steps)
            smooth_scroll(
                page,
                pixels=int(action["pixels"]),
                duration_seconds=scroll_duration_seconds,
                steps=scroll_steps,
            )
            continue

        if action_type == "focus":
            selector = action["selector"]
            optional = bool(action.get("optional", False))
            timeout_ms = int(action.get("timeout_ms", 2400))
            zoom = float(action.get("zoom", 1.03))
            padding = float(action.get("padding", 16.0))
            dim_opacity = float(action.get("dim_opacity", 0.18))
            auto_scroll = bool(action.get("auto_scroll", True))
            ensure_focus_overlay(page)
            has_target = focus_selector(
                page,
                selector=selector,
                timeout_ms=timeout_ms,
                padding=padding,
                zoom=zoom,
                dim_opacity=dim_opacity,
                auto_scroll=auto_scroll,
            )
            if not has_target and optional:
                page.evaluate("() => window.__demoFocusOff?.()")
                continue
            if not has_target:
                raise RuntimeError(f"Could not focus selector: {selector}")

            if show_mouse_overlay:
                ensure_mouse_overlay(page)
                target_pos = move_mouse_to_selector(page, selector=selector, timeout_ms=timeout_ms, anchor="edge")
                if target_pos is not None:
                    track_cursor(target_pos[0], target_pos[1], kind="move")

            wait_ms = int(float(action.get("wait_seconds", 0.8)) * 1000)
            if wait_ms > 0:
                page.wait_for_timeout(wait_ms)
            page.evaluate("() => window.__demoFocusOff?.()")
            settle_ms = int(float(action.get("post_wait_seconds", 0.16)) * 1000)
            if settle_ms > 0:
                page.wait_for_timeout(settle_ms)
            continue

        if action_type == "click":
            selector = action["selector"]
            optional = bool(action.get("optional", False))
            timeout_ms = int(action.get("timeout_ms", 2000))
            has_target = True
            target_pos: tuple[float, float] | None = None
            if show_mouse_overlay:
                ensure_mouse_overlay(page)
                target_pos = move_mouse_to_selector(page, selector=selector, timeout_ms=timeout_ms)
                has_target = target_pos is not None
                if target_pos is not None:
                    track_cursor(target_pos[0], target_pos[1], kind="move")
            if not has_target and optional:
                continue
            delay_ms = int(max(pre_click_delay_seconds, 0.0) * 1000)
            if delay_ms > 0:
                page.wait_for_timeout(delay_ms)
            try:
                if show_mouse_overlay and target_pos is not None:
                    page.evaluate("() => window.__demoMouseClick?.()")
                    track_cursor(target_pos[0], target_pos[1], kind="click")
                track_interaction("click")
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
) -> tuple[Path, list[dict[str, float | str]], list[dict[str, float | str]]]:
    def _record_once() -> tuple[Path, list[dict[str, float | str]], list[dict[str, float | str]]]:
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
                interaction_events: list[dict[str, float | str]] = []
                action_start = time.monotonic()
                run_actions(
                    page,
                    base_url=base_url,
                    actions=actions,
                    show_mouse_overlay=show_mouse_overlay,
                    pre_click_delay_seconds=pre_click_delay_seconds,
                    cursor_events=cursor_events,
                    interaction_events=interaction_events,
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
                return temp_copy, cursor_events, interaction_events

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
    lesson_pages = [page for page in pages if Path(page).name.lower() != "index.html"]
    if not lesson_pages:
        lesson_pages = pages

    actions.append({"type": "goto", "path": lesson_pages[0], "wait_seconds": 1.00})
    for index, page in enumerate(lesson_pages):
        actions.append(
            {
                "type": "focus",
                "selector": "#p1-outcomes",
                "optional": True,
                "wait_seconds": 1.35,
                "zoom": 1.015,
                "padding": 14.0,
                "dim_opacity": 0.16,
                "post_wait_seconds": 0.26,
                "auto_scroll": False,
            }
        )
        actions.append({"type": "scroll", "pixels": 430, "duration_seconds": 1.45, "steps": 20})
        actions.append(
            {
                "type": "focus",
                "selector": ".prompt-box",
                "optional": True,
                "wait_seconds": 1.80,
                "zoom": 1.03,
                "padding": 16.0,
                "dim_opacity": 0.18,
                "post_wait_seconds": 0.28,
                "auto_scroll": False,
            }
        )
        actions.append(
            {
                "type": "click",
                "selector": ".prompt-box .copy-btn",
                "optional": True,
                "wait_seconds": 0.52,
                "timeout_ms": 1800,
            }
        )
        actions.append({"type": "scroll", "pixels": 360, "duration_seconds": 1.25, "steps": 18})
        actions.append(
            {
                "type": "focus",
                "selector": ".task-box",
                "optional": True,
                "wait_seconds": 1.40,
                "zoom": 1.02,
                "padding": 16.0,
                "dim_opacity": 0.17,
                "post_wait_seconds": 0.26,
                "auto_scroll": False,
            }
        )
        actions.append({"type": "scroll", "pixels": 480, "duration_seconds": 1.55, "steps": 22})
        actions.append(
            {
                "type": "focus",
                "selector": ".checkpoint",
                "optional": True,
                "wait_seconds": 1.45,
                "zoom": 1.02,
                "padding": 16.0,
                "dim_opacity": 0.16,
                "post_wait_seconds": 0.32,
                "auto_scroll": False,
            }
        )
        actions.append({"type": "wait", "seconds": 0.60})
        if index < len(lesson_pages) - 1:
            next_page = lesson_pages[index + 1]
            actions.append(
                {
                    "type": "click",
                    "selector": f"aside.sidebar a[href='{next_page}']",
                    "optional": False,
                    "wait_seconds": 1.10,
                    "timeout_ms": 2600,
                }
            )
    actions.append({"type": "wait", "seconds": 1.25})
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
    *,
    include_background_music: bool = False,
) -> dict[str, float | int | bool]:
    capture_start = time.perf_counter()
    webm_path, _cursor_events, interaction_events = record_actions_to_webm(
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
    raw_video_generation_seconds = time.perf_counter() - capture_start
    transcode_seconds = 0.0
    overlay_seconds = 0.0
    post_processing_seconds = 0.0
    ffmpeg_exe = ""
    try:
        ffmpeg_exe = resolve_ffmpeg(args.ffmpeg_path)
        encode_settings = encode_profile_settings(str(args.encode_profile))
        post_start = time.perf_counter()
        transcode_start = time.perf_counter()
        transcode_webm_to_mp4(
            ffmpeg_exe=ffmpeg_exe,
            source_webm=webm_path,
            target_mp4=output_path,
            fps=args.fps,
            video_preset=encode_settings["video_preset"],
            video_crf=encode_settings["video_crf"],
        )
        transcode_seconds = time.perf_counter() - transcode_start
        effect_start = time.perf_counter()
        interaction_audio_path = Path(tempfile.gettempdir()) / f"browser-audio-{int(time.time() * 1000)}.wav"
        try:
            duration_seconds = probe_video_duration_seconds(output_path)
            synthesize_interaction_audio(
                interaction_audio_path,
                duration_seconds=duration_seconds,
                interaction_events=interaction_events,
                include_background_music=include_background_music,
            )
            mux_audio_into_mp4(
                ffmpeg_exe=ffmpeg_exe,
                video_path=output_path,
                audio_path=interaction_audio_path,
                audio_bitrate=encode_settings["audio_bitrate"],
            )
        finally:
            if interaction_audio_path.exists():
                interaction_audio_path.unlink()
        overlay_seconds = time.perf_counter() - effect_start
        post_processing_seconds = time.perf_counter() - post_start
    finally:
        if webm_path.exists():
            webm_path.unlink()
    performance: dict[str, float | int | bool] = {
        "raw_video_generation_seconds": raw_video_generation_seconds,
        "post_processing_seconds": post_processing_seconds,
        "transcode_seconds": transcode_seconds,
        "overlay_seconds": overlay_seconds,
    }
    performance.update(collect_video_file_stats(output_path, ffmpeg_exe))
    return performance


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
            outcome_actions = build_outcome_actions(pages)
            outcome_perf = create_video_from_actions(base_url, outcome_actions, outcome_output, args)
            outputs.append(outcome_output)
            outcome_directives, outcome_story = write_video_sidecars(
                video_path=outcome_output,
                workflow_name="site-videos/outcome",
                story_summary=(
                    "Show the tutorial site outcome path as a guided viewer journey across key lessons, "
                    "including showcase tab toggles and readable scroll reveals."
                ),
                args=args,
                actions=outcome_actions,
                performance=outcome_perf,
                story_notes=["Target viewer should understand what the finished tutorial site delivers."],
            )
            outputs.extend([outcome_directives, outcome_story])

        if args.output_mode in ("both", "process"):
            process_output = media_dir / "learning-process-fast.mp4"
            print(f"Recording learning process video to: {process_output}")
            process_actions = build_process_actions(pages)
            process_perf = create_video_from_actions(
                base_url,
                process_actions,
                process_output,
                args,
                include_background_music=True,
            )
            outputs.append(process_output)
            process_directives, process_story = write_video_sidecars(
                video_path=process_output,
                workflow_name="site-videos/process",
                story_summary=(
                    "Show the real lesson flow across the tutorial pages (excluding the landing preview): "
                    "highlight learning outcomes, Codex prompt blocks, student task checklists, and final "
                    "checkpoint question sections with smooth focus-in/focus-out shots."
                ),
                args=args,
                actions=process_actions,
                performance=process_perf,
                story_notes=[
                    "Target viewer should feel how Codex is used as a practical learning accelerator.",
                    "Prompt copy interactions are included to reinforce actionable usage, not passive reading.",
                    "Checkpoint sections are shown without revealing answers to preserve learner reflection.",
                    "Audio includes a subtle elevator-music bed plus click/scroll interaction cues.",
                ],
            )
            outputs.extend([process_directives, process_story])

    return outputs


def run_html_tour(args: argparse.Namespace) -> list[Path]:
    site_dir = Path(args.site_dir).resolve()
    media_dir = Path(args.media_dir).resolve()
    media_dir.mkdir(parents=True, exist_ok=True)
    if not site_dir.exists():
        raise RuntimeError(f"site directory does not exist: {site_dir}")

    output_path = media_dir / args.tour_output
    pages = parse_pages(args.tour_pages)
    actions = build_tour_actions(pages)
    with local_http_server(site_dir) as base_url:
        print(f"Recording html tour to: {output_path}")
        perf = create_video_from_actions(base_url, actions, output_path, args)
    directives_path, story_path = write_video_sidecars(
        video_path=output_path,
        workflow_name="html-tour",
        story_summary="Provide a concise guided tour through selected local HTML tutorial pages.",
        args=args,
        actions=actions,
        performance=perf,
        story_notes=["Use this as a reusable walkthrough template for any lesson subset."],
    )
    return [output_path, directives_path, story_path]


def run_concept_slideshow(args: argparse.Namespace) -> list[Path]:
    concept = resolve_concept(args)
    slides = build_slides(concept=concept, title=args.slideshow_title, points_per_slide=args.points_per_slide)
    media_dir = Path(args.media_dir).resolve()
    media_dir.mkdir(parents=True, exist_ok=True)
    output_path = media_dir / args.slideshow_output

    actions = []
    with tempfile.TemporaryDirectory(prefix="concept-slideshow-") as tmpdir:
        temp_root = Path(tmpdir)
        html_path = temp_root / "slides.html"
        write_slideshow_html(html_path, slides=slides, slide_duration=args.slide_duration)

        total_seconds = len(slides) * args.slide_duration + 1.0
        actions = [{"type": "goto", "path": "slides.html", "wait_seconds": 0.7}, {"type": "wait", "seconds": total_seconds}]
        with local_http_server(temp_root) as base_url:
            print(f"Recording concept slideshow to: {output_path}")
            perf = create_video_from_actions(base_url, actions, output_path, args)
    directives_path, story_path = write_video_sidecars(
        video_path=output_path,
        workflow_name="concept-slideshow",
        story_summary=(
            f"Translate a concept into a paced slide narrative: {len(slides)} slide(s) from source concept text."
        ),
        args=args,
        actions=actions,
        performance=perf,
        story_notes=[
            f"Slides generated: {len(slides)}",
            f"Slide duration: {args.slide_duration:.2f}s",
            "Refine concept wording and points-per-slide to steer the next iteration.",
        ],
    )
    return [output_path, directives_path, story_path]


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
