#!/usr/bin/env python3
"""Enforce release video rendering policy before push."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ZERO_SHA = "0" * 40
PROJECT_ROOT = Path(__file__).resolve().parents[2]

PROCESS_ARTIFACTS = {
    "Lessons/tutorial_site/media/learning-process-fast.mp4",
    "Lessons/tutorial_site/media/learning-process-fast.directives.md",
    "Lessons/tutorial_site/media/learning-process-fast.story.md",
}
OUTCOME_ARTIFACTS = {
    "Lessons/tutorial_site/media/tutorial-outcome.mp4",
    "Lessons/tutorial_site/media/tutorial-outcome.directives.md",
    "Lessons/tutorial_site/media/tutorial-outcome.story.md",
}
VIDEO_BINARIES = {
    "Lessons/tutorial_site/media/learning-process-fast.mp4",
    "Lessons/tutorial_site/media/tutorial-outcome.mp4",
}
CODE_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx", ".css", ".html", ".sh", ".ps1"}


def run_git(*args: str, check: bool = True) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )
    if check and completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "git command failed")
    return completed.stdout


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--range",
        action="append",
        default=[],
        help="Git revision range to inspect (repeatable), e.g. origin/main..HEAD",
    )
    parser.add_argument(
        "--check-staged",
        action="store_true",
        help="Inspect staged changes (git diff --cached).",
    )
    parser.add_argument(
        "--pre-push",
        action="store_true",
        help="Read pre-push stdin lines and infer ranges from refs being pushed.",
    )
    return parser.parse_args(argv)


def normalize_path(raw: str) -> str:
    return raw.strip().replace("\\", "/")


def changed_files_in_range(range_spec: str) -> set[str]:
    output = run_git("diff", "--name-only", range_spec)
    return {normalize_path(line) for line in output.splitlines() if line.strip()}


def changed_files_staged() -> set[str]:
    output = run_git("diff", "--cached", "--name-only")
    return {normalize_path(line) for line in output.splitlines() if line.strip()}


def commit_parent(commit_sha: str) -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", f"{commit_sha}^"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


def parse_prepush_ranges(stdin_text: str) -> list[str]:
    ranges: list[str] = []
    for raw_line in stdin_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 4:
            raise RuntimeError(f"Invalid pre-push input line: {line}")
        local_ref, local_sha, remote_ref, remote_sha = parts
        _ = local_ref, remote_ref
        if local_sha == ZERO_SHA:
            continue
        if remote_sha == ZERO_SHA:
            parent = commit_parent(local_sha)
            ranges.append(f"{parent}..{local_sha}" if parent else local_sha)
            continue
        ranges.append(f"{remote_sha}..{local_sha}")
    return ranges


def changed_code_tokens_for_path(range_spec: str, path: str) -> list[str]:
    output = run_git("diff", "--no-color", "-U0", range_spec, "--", path)
    ext = Path(path).suffix.lower()
    tokens: list[str] = []
    for line in output.splitlines():
        if not line or line.startswith("+++ ") or line.startswith("--- "):
            continue
        if not (line.startswith("+") or line.startswith("-")):
            continue
        content = line[1:].strip()
        if not content:
            continue
        if is_comment_only(content, ext):
            continue
        tokens.append(content)
    return tokens


def is_comment_only(content: str, ext: str) -> bool:
    if ext in {".py", ".sh", ".ps1"}:
        return content.startswith("#")
    if ext in {".js", ".ts", ".tsx", ".jsx", ".css"}:
        return (
            content.startswith("//")
            or content.startswith("/*")
            or content.startswith("*")
            or content.startswith("*/")
        )
    if ext == ".html":
        return content.startswith("<!--") or content.endswith("-->")
    return False


def code_change_is_comment_or_whitespace_only(path: str, ranges: list[str]) -> bool:
    ext = Path(path).suffix.lower()
    if ext not in CODE_EXTENSIONS:
        return False
    for range_spec in ranges:
        if changed_code_tokens_for_path(range_spec, path):
            return False
    return True


def classify_impacts(changed_files: set[str], ranges: list[str]) -> tuple[set[str], list[str]]:
    required_targets: set[str] = set()
    reasons: list[str] = []

    for path in sorted(changed_files):
        if path in VIDEO_BINARIES:
            continue

        p = Path(path)
        lower = path.lower()

        if lower.startswith("lessons/tutorial_site/") and p.suffix.lower() in {".html", ".css", ".js"}:
            required_targets.add("process")
            reasons.append(f"{path} affects tutorial site visuals.")
            continue

        if re.fullmatch(r"Lessons/tutorial_site/media/learning-process-fast\.(story|directives)\.md", path):
            required_targets.add("process")
            reasons.append(f"{path} is a process scenario input.")
            continue

        if re.fullmatch(r"Lessons/tutorial_site/media/tutorial-outcome\.(story|directives)\.md", path):
            required_targets.add("outcome")
            reasons.append(f"{path} is an outcome scenario input.")
            continue

        if lower.startswith("tools/browser_video_creator/"):
            if code_change_is_comment_or_whitespace_only(path, ranges):
                continue
            required_targets.add("process")
            reasons.append(f"{path} changes browser renderer behavior.")
            continue

        if lower.startswith("tools/gui_demo_video_creator/"):
            if code_change_is_comment_or_whitespace_only(path, ranges):
                continue
            required_targets.add("outcome")
            reasons.append(f"{path} changes GUI demo renderer behavior.")
            continue

        if lower.startswith("tools/tutorial_video_creator/"):
            if code_change_is_comment_or_whitespace_only(path, ranges):
                continue
            required_targets.update({"process", "outcome"})
            reasons.append(f"{path} can affect both tutorial artifacts.")
            continue

        if lower.startswith("task_manager/"):
            if p.suffix.lower() == ".md":
                continue
            if code_change_is_comment_or_whitespace_only(path, ranges):
                continue
            required_targets.add("outcome")
            reasons.append(f"{path} affects runtime behavior shown in outcome video.")

    return required_targets, reasons


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def directives_path_for_target(target: str) -> Path:
    if target == "process":
        return PROJECT_ROOT / "Lessons/tutorial_site/media/learning-process-fast.directives.md"
    return PROJECT_ROOT / "Lessons/tutorial_site/media/tutorial-outcome.directives.md"


def required_artifacts_for_target(target: str) -> set[str]:
    return PROCESS_ARTIFACTS if target == "process" else OUTCOME_ARTIFACTS


def validate_release_sidecar(target: str) -> tuple[bool, str]:
    directives_path = directives_path_for_target(target)
    if not directives_path.exists():
        return False, f"Missing directives file: {directives_path.as_posix()}"
    content = read_text(directives_path)
    if "- Encode profile: `release`" not in content:
        return False, f"{directives_path.as_posix()} is not marked as release profile."
    return True, ""


def gather_changed_files(args: argparse.Namespace) -> tuple[set[str], list[str]]:
    ranges = [r.strip() for r in args.range if r.strip()]
    if args.pre_push:
        ranges.extend(parse_prepush_ranges(sys.stdin.read()))
    if args.check_staged:
        changed = changed_files_staged()
        return changed, ["--cached"]
    if not ranges:
        raise RuntimeError("No change source specified. Use --range, --pre-push, or --check-staged.")
    changed: set[str] = set()
    for range_spec in ranges:
        changed.update(changed_files_in_range(range_spec))
    return changed, ranges


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    changed_files, ranges = gather_changed_files(args)
    required_targets, reasons = classify_impacts(changed_files, ranges)

    if not required_targets:
        print("video-render-policy: no rendering-impacting changes detected.")
        return 0

    errors: list[str] = []
    for target in sorted(required_targets):
        required_artifacts = required_artifacts_for_target(target)
        missing = sorted(required_artifacts - changed_files)
        if missing:
            errors.append(
                f"Missing updated {target} artifacts in pushed changes:\n"
                + "\n".join(f"  - {path}" for path in missing)
            )
        ok, message = validate_release_sidecar(target)
        if not ok:
            errors.append(message)

    if errors:
        print("video-render-policy: release gate failed.")
        print("Detected impacting changes:")
        for reason in reasons:
            print(f"  - {reason}")
        for error in errors:
            print(error)
        print(
            "Required action: render impacted videos with release profile before push "
            "and include updated MP4 + sidecars in the commit."
        )
        return 1

    print("video-render-policy: release gate passed.")
    for target in sorted(required_targets):
        print(f"  - {target}: release artifacts present and sidecar marked release")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
