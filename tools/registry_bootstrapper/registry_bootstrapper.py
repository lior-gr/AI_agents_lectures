#!/usr/bin/env python3
"""Create baseline SKILLS.md and TOOLS.md registry files."""

from __future__ import annotations

import argparse
from pathlib import Path


SKILLS_TEMPLATE = """# Skills Registry

This file lists all currently available skill scripts with name and description.

## Available skills

| Name | Description | File |
|---|---|---|
"""

TOOLS_TEMPLATE = """# Tools Registry

This file lists executable tools and their LLM-usable argument schemas.

## Tool registration format

For each tool add:
- tool name
- script path
- purpose
- invocation examples
- input schema (JSON)
- output artifacts
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create SKILLS.md and TOOLS.md templates.")
    parser.add_argument("--project-root", default=".", help="Project root where registry files are created.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing registry files.")
    return parser.parse_args()


def write_template_file(path: Path, template: str, label: str, force: bool) -> None:
    exists = path.exists()
    if exists and not force:
        print(f"{label} already exists: {path}")
        return

    path.write_text(template, encoding="utf-8")
    if exists:
        print(f"{label} overwritten: {path}")
    else:
        print(f"{label} created: {path}")


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    project_root.mkdir(parents=True, exist_ok=True)

    skills_path = project_root / "SKILLS.md"
    tools_path = project_root / "TOOLS.md"

    write_template_file(skills_path, SKILLS_TEMPLATE, "SKILLS.md", args.force)
    write_template_file(tools_path, TOOLS_TEMPLATE, "TOOLS.md", args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
