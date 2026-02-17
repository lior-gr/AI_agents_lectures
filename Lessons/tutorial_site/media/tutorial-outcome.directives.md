# Video Directives: tutorial-outcome.mp4

- Generated (UTC): `2026-02-17T15:36:52+00:00`
- Tool: `gui_demo_video_creator`
- Output video: `C:\here\AI_agents_lectures\Lessons\tutorial_site\media\tutorial-outcome.mp4`

## Capture Directives
- Window size: `1366x820`
- FPS: `24`
- Encode profile: `release`
- MP4 codec settings: `libx264 preset=medium crf=18 pix_fmt=yuv420p`
- MP4 audio settings: `aac 128k 48kHz`
- UI source: `task_manager` PySide6 app

## Interaction Directives
- Typing pace intent: `3.00` words/second
- Typing conversion: `5.00` chars/word
- Fixed typing cadence: `15.00` chars/second (`67` ms per char)
- Pre-click delay: `1.00` seconds
- Wait after typing before submit: `3.00` seconds
- Wait between goals: `5.00` seconds
- Mouse cue style: non-occluding translucent/hollow markers with click pulse rings
- Typing audio: pleasant keyboard keystroke sounds synchronized to goal-input characters
- Logger audio: soft tick sound when progress rows are appended
- Click audio: soft click sound when submit is clicked

## Goal Script
1. Show current tasks state.
2. Mark tasks 2 and 4 as done, and show current state.
3. Add tasks Prepare demo slides, Email team summary, and Plan follow-up call. Then show all tasks in an ASCII table with aligned vertical separators.

## Iteration Knobs
- Adjust timing knobs above to tune pacing and perceived responsiveness.
- Edit the goal script text to steer scenario outcomes shown in output/logger.
- Keep goals deterministic so result comparisons across iterations stay meaningful.

## Performance Status
- Raw video generation (seconds): `63.715`
- Post processing (seconds): `13.607`
- Transcode step (seconds): `13.607`
- Overlay step (seconds): `0.000`
- Video length (seconds): `28.120`
- Video size on disk (bytes): `649765`
- Has audio stream: `True`
- Directives generation (seconds): `0.001525`
- Story generation (seconds): `0.001239`
- Sidecar generation total (seconds): `0.002764`
