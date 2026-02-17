#!/usr/bin/env python3
"""Create tutorial videos from real source clips for the tutorial site."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MEDIA_DIR = PROJECT_ROOT / "Lessons" / "tutorial_site" / "media"


def tool_schema() -> dict:
    return {
        "tool": "tutorial_video_creator",
        "entrypoints": {
            "windows": "tools/tutorial_video_creator/run.ps1",
            "unix": "tools/tutorial_video_creator/run.sh",
            "python": "tools/tutorial_video_creator/tutorial_video_creator.py",
        },
        "description": "Create tutorial preview videos for the agent + GUI wrapper walkthrough.",
        "arguments": {
            "media-dir": {
                "type": "string",
                "required": False,
                "default": "Lessons/tutorial_site/media",
                "description": "Target media directory for outputs.",
            },
            "outcome-input": {
                "type": "string",
                "required": False,
                "default": "raw-outcome.mp4",
                "aliases": ["outcome-source-path"],
                "description": "Source clip for final tutorial outcome.",
            },
            "process-input": {
                "type": "string",
                "required": False,
                "default": "raw-process.mp4",
                "aliases": ["process-source-path"],
                "description": "Source clip for accelerated learning process.",
            },
            "process-speed": {
                "type": "number",
                "required": False,
                "default": 6.0,
                "minimum": 0.1,
                "aliases": ["speed-multiplier"],
                "description": "Playback acceleration for process clip.",
            },
            "width": {
                "type": "integer",
                "required": False,
                "default": 1280,
                "minimum": 320,
                "aliases": ["resolution-width"],
                "description": "Output width; height auto-preserved by aspect ratio.",
            },
            "output-mode": {
                "type": "string",
                "required": False,
                "default": "both",
                "enum": ["both", "outcome", "process"],
                "description": "Select which output videos to generate.",
            },
            "ffmpeg-path": {
                "type": "string",
                "required": False,
                "default": "",
                "description": "Optional explicit ffmpeg path or executable name.",
            },
            "include-webm": {
                "type": "boolean",
                "required": False,
                "default": False,
                "description": "Also generate .webm versions.",
            },
            "create-demo-placeholders": {
                "type": "boolean",
                "required": False,
                "default": False,
                "description": "Generate synthetic source clips when source videos are missing.",
            },
            "print-schema": {
                "type": "boolean",
                "required": False,
                "default": False,
                "description": "Print this schema as JSON and exit.",
            },
        },
        "outputs": [
            "tutorial-outcome.mp4",
            "learning-process-fast.mp4",
            "tutorial-outcome.webm (optional)",
            "learning-process-fast.webm (optional)",
        ],
    }


def normalize_legacy_args(argv: list[str]) -> list[str]:
    """Accept old PowerShell-style argument names for compatibility."""
    mapping = {
        "-MediaDir": "--media-dir",
        "-OutcomeInput": "--outcome-input",
        "-OutcomeSourcePath": "--outcome-input",
        "-ProcessInput": "--process-input",
        "-ProcessSourcePath": "--process-input",
        "-ProcessSpeed": "--process-speed",
        "-SpeedMultiplier": "--process-speed",
        "-Width": "--width",
        "-ResolutionWidth": "--width",
        "-OutputMode": "--output-mode",
        "-FfmpegPath": "--ffmpeg-path",
        "-IncludeWebm": "--include-webm",
        "-CreateDemoPlaceholders": "--create-demo-placeholders",
        "-PrintSchema": "--print-schema",
    }

    normalized: list[str] = []
    bool_aliases = {
        "includewebm": "--include-webm",
        "createdemoplaceholders": "--create-demo-placeholders",
        "printschema": "--print-schema",
    }
    pattern = re.compile(r"^-([A-Za-z][A-Za-z0-9]*)\s*:\s*\$(true|false)$", re.IGNORECASE)

    for token in argv:
        if token in mapping:
            normalized.append(mapping[token])
            continue

        match = pattern.match(token)
        if match:
            key = match.group(1).lower()
            value = match.group(2).lower() == "true"
            if value and key in bool_aliases:
                normalized.append(bool_aliases[key])
            continue

        normalized.append(token)
    return normalized


def positive_float(value: str) -> float:
    result = float(value)
    if result <= 0:
        raise argparse.ArgumentTypeError("must be greater than 0")
    return result


def min_width(value: str) -> int:
    result = int(value)
    if result < 320:
        raise argparse.ArgumentTypeError("must be at least 320")
    return result


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=tool_schema()["description"])
    parser.add_argument("--media-dir", default=str(DEFAULT_MEDIA_DIR))
    parser.add_argument("--outcome-input", "--outcome-source-path", default="raw-outcome.mp4")
    parser.add_argument("--process-input", "--process-source-path", default="raw-process.mp4")
    parser.add_argument("--process-speed", "--speed-multiplier", type=positive_float, default=6.0)
    parser.add_argument("--width", "--resolution-width", type=min_width, default=1280)
    parser.add_argument("--output-mode", choices=["both", "outcome", "process"], default="both")
    parser.add_argument("--ffmpeg-path", default="")
    parser.add_argument("--include-webm", action="store_true")
    parser.add_argument("--create-demo-placeholders", action="store_true")
    parser.add_argument("--print-schema", action="store_true")
    return parser.parse_args(normalize_legacy_args(argv))


def resolve_ffmpeg(preferred_path: str) -> str:
    if preferred_path:
        candidate = Path(preferred_path)
        if candidate.exists():
            return str(candidate.resolve())
        resolved = shutil.which(preferred_path)
        if resolved:
            return resolved

    resolved = shutil.which("ffmpeg")
    if resolved:
        return resolved

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        winget_link = Path(local_app_data) / "Microsoft" / "WinGet" / "Links" / "ffmpeg.exe"
        if winget_link.exists():
            return str(winget_link)

        packages_root = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
        if packages_root.exists():
            candidates = [
                path
                for path in packages_root.rglob("ffmpeg.exe")
                if "Gyan.FFmpeg_" in str(path) and "\\bin\\" in str(path)
            ]
            if candidates:
                latest = max(candidates, key=lambda p: p.stat().st_mtime)
                return str(latest)

    raise RuntimeError(
        "Could not find ffmpeg. Install it (or run the wrapper), "
        "or pass --ffmpeg-path C:/path/to/ffmpeg.exe."
    )


def run_ffmpeg(ffmpeg_exe: str, args: Iterable[str]) -> None:
    cmd = [ffmpeg_exe, *args]
    process = subprocess.run(cmd, check=False)
    if process.returncode != 0:
        raise RuntimeError(f"ffmpeg failed with exit code {process.returncode}.")


def find_by_patterns(folder: Path, patterns: list[str]) -> str | None:
    files = [path for path in folder.iterdir() if path.is_file()]
    for pattern in patterns:
        matches = [path for path in files if fnmatch.fnmatch(path.name, pattern)]
        if matches:
            latest = max(matches, key=lambda p: p.stat().st_mtime)
            return str(latest.resolve())
    return None


def resolve_input_source(input_value: str, media_folder: Path, role: str) -> str | None:
    candidates: list[Path] = []
    requested = Path(input_value)
    if requested.is_absolute():
        candidates.append(requested)
    else:
        candidates.append(media_folder / input_value)
        candidates.append(Path.cwd() / input_value)

    for candidate in candidates:
        if candidate.exists():
            return str(candidate.resolve())

    if role == "outcome":
        patterns = ["*outcome*.mp4", "*outcome*.mov", "*summary*.mp4", "*overview*.mp4", "*intro*.mp4"]
    else:
        patterns = ["*process*.mp4", "*timelapse*.mp4", "*speed*.mp4", "*workflow*.mp4"]

    auto_detected = find_by_patterns(media_folder, patterns)
    if auto_detected:
        print(f"Auto-detected {role} source: {auto_detected}")
    return auto_detected


def new_demo_source(ffmpeg_exe: str, output_path: Path, role: str, width: int) -> str:
    height = round(width * 9 / 16)
    if height % 2 != 0:
        height += 1

    if role == "outcome":
        source_filter = f"testsrc2=size={width}x{height}:rate=30:duration=24"
        crf = "28"
    else:
        source_filter = f"testsrc=size={width}x{height}:rate=30:duration=54"
        crf = "30"

    print(f"Generating demo {role} source: {output_path}")
    run_ffmpeg(
        ffmpeg_exe,
        [
            "-y",
            "-f",
            "lavfi",
            "-i",
            source_filter,
            "-c:v",
            "libx264",
            "-crf",
            crf,
            "-preset",
            "veryfast",
            "-movflags",
            "+faststart",
            "-an",
            str(output_path),
        ],
    )
    return str(output_path)


def show_missing_input_help(
    media_folder: Path,
    outcome_requested: str,
    process_requested: str,
    missing_outcome: bool,
    missing_process: bool,
    mode: str,
) -> None:
    print()
    print(f"Missing source videos for mode '{mode}'.")
    if missing_outcome:
        print(f" - Could not find outcome source for: {outcome_requested}")
    if missing_process:
        print(f" - Could not find process source for: {process_requested}")

    print()
    print("Expected defaults in:")
    print(f" - {media_folder / 'raw-outcome.mp4'}")
    print(f" - {media_folder / 'raw-process.mp4'}")

    print()
    print("Try one of these:")
    print(" 1) Pass explicit paths:")
    print(
        "    tools/tutorial_video_creator/run.ps1 --output-mode both "
        "--outcome-input 'C:\\path\\outcome.mp4' --process-input 'C:\\path\\process.mp4'"
    )
    print(f" 2) Put clips in '{media_folder}' with names like '*outcome*.mp4' and '*process*.mp4'.")
    print(" 3) Generate demo placeholders now:")
    print("    tools/tutorial_video_creator/run.ps1 --output-mode both --create-demo-placeholders")


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.print_schema:
        print(json.dumps(tool_schema(), indent=2))
        return 0

    ffmpeg_exe = resolve_ffmpeg(args.ffmpeg_path)
    print(f"Using ffmpeg: {ffmpeg_exe}")

    media_dir = Path(args.media_dir)
    media_dir.mkdir(parents=True, exist_ok=True)
    media_dir = media_dir.resolve()

    need_outcome = args.output_mode in {"both", "outcome"}
    need_process = args.output_mode in {"both", "process"}

    outcome_source = resolve_input_source(args.outcome_input, media_dir, "outcome") if need_outcome else None
    process_source = resolve_input_source(args.process_input, media_dir, "process") if need_process else None

    if args.create_demo_placeholders:
        if need_outcome and not outcome_source:
            outcome_source = new_demo_source(ffmpeg_exe, media_dir / "__demo-outcome-source.mp4", "outcome", args.width)
        if need_process and not process_source:
            process_source = new_demo_source(ffmpeg_exe, media_dir / "__demo-process-source.mp4", "process", args.width)

    missing_outcome = need_outcome and not outcome_source
    missing_process = need_process and not process_source
    if missing_outcome or missing_process:
        show_missing_input_help(
            media_folder=media_dir,
            outcome_requested=args.outcome_input,
            process_requested=args.process_input,
            missing_outcome=missing_outcome,
            missing_process=missing_process,
            mode=args.output_mode,
        )
        return 1

    if need_outcome:
        print(f"Outcome source: {outcome_source}")
    if need_process:
        print(f"Process source: {process_source}")

    outcome_mp4 = media_dir / "tutorial-outcome.mp4"
    process_mp4 = media_dir / "learning-process-fast.mp4"
    outcome_webm = media_dir / "tutorial-outcome.webm"
    process_webm = media_dir / "learning-process-fast.webm"

    speed_pts = 1.0 / args.process_speed
    print("Generating video files...")

    if need_outcome and outcome_source:
        run_ffmpeg(
            ffmpeg_exe,
            [
                "-y",
                "-i",
                outcome_source,
                "-vf",
                f"scale={args.width}:-2,fps=30",
                "-c:v",
                "libx264",
                "-crf",
                "23",
                "-preset",
                "medium",
                "-movflags",
                "+faststart",
                "-an",
                str(outcome_mp4),
            ],
        )

    if need_process and process_source:
        run_ffmpeg(
            ffmpeg_exe,
            [
                "-y",
                "-i",
                process_source,
                "-vf",
                f"setpts={speed_pts:.12g}*PTS,scale={args.width}:-2,fps=30",
                "-c:v",
                "libx264",
                "-crf",
                "24",
                "-preset",
                "medium",
                "-movflags",
                "+faststart",
                "-an",
                str(process_mp4),
            ],
        )

    if args.include_webm:
        print("Generating WEBM files...")
        if need_outcome and outcome_mp4.exists():
            run_ffmpeg(
                ffmpeg_exe,
                [
                    "-y",
                    "-i",
                    str(outcome_mp4),
                    "-c:v",
                    "libvpx-vp9",
                    "-crf",
                    "34",
                    "-b:v",
                    "0",
                    "-an",
                    str(outcome_webm),
                ],
            )

        if need_process and process_mp4.exists():
            run_ffmpeg(
                ffmpeg_exe,
                [
                    "-y",
                    "-i",
                    str(process_mp4),
                    "-c:v",
                    "libvpx-vp9",
                    "-crf",
                    "34",
                    "-b:v",
                    "0",
                    "-an",
                    str(process_webm),
                ],
            )

    print("Done.")
    print("Expected site files:")
    if need_outcome:
        print(f" - {outcome_mp4}")
    if need_process:
        print(f" - {process_mp4}")
    if args.include_webm and need_outcome:
        print(f" - {outcome_webm}")
    if args.include_webm and need_process:
        print(f" - {process_webm}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
