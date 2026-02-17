# True Agent Video Demo

## Purpose

Produce and integrate real demo videos for the implemented agent system with a GUI wrapper.

## Product framing

- Agent core: decision loop, tools, MCP boundary, and skill/routing behavior.
- GUI wrapper: input/output and progress visibility around the agent core.

The demo must present the system as an agent with a GUI wrapper, not as a generic "feature" clip.

## Tooling concept

Video generation tooling is packaged as:
- Python implementation (`tools/tutorial_video_creator/tutorial_video_creator.py`)
- OS wrappers (`run.ps1`, `run.sh`) that prepare dependencies and invoke Python

## Trigger use-cases

Use this skill when requests include:
- replace placeholders with real demo
- show real tool video
- true agent video

## Required workflow

1. Confirm requested target behavior in one sentence.
2. Confirm success criteria: primary video playback is the goal.
3. Collect or record real source footage that shows actual agent execution.
4. Generate web media outputs via the tool wrapper:
   - Windows: `tools/tutorial_video_creator/run.ps1`
   - Linux/macOS: `tools/tutorial_video_creator/run.sh`
5. Integrate outputs into primary `<video>` sources in tutorial pages.
6. Verify file presence, page copy, and playback intent.

## Validation checklist

- Primary MP4 files exist with non-trivial size.
- Primary clip content demonstrates real agent behavior.
- GUI is shown as wrapper over agent execution.
- No placeholder wording remains in primary demo sections.

## Common failure modes to avoid

- Showing only UI visuals without real agent execution.
