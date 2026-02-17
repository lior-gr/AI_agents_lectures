# Video Render Policy

## Purpose

Define a stable project contract for when to render videos and which profile to use.

## Contract

1. Default profile is `draft` during normal iteration.
2. If the user asks to `commit`, `push`, or `commit and push`:
   - Evaluate current changes for rendering impact.
   - If rendering-impacting changes exist, render with `release` profile before commit/push.
   - Use explicit tool flags:
     - `tools/browser_video_creator/... --encode-profile release`
     - `tools/gui_demo_video_creator/... --encode-profile release`
   - If no rendering-impacting changes exist, skip rendering.
3. Do not render automatically for non-impacting changes.

## Rendering-impact decision rules

Treat changes as **rendering-impacting** when they can change visual output, timing, audio, or encoded artifacts.

### Impacting (render required before commit/push)

- Tutorial/UI content that appears in videos:
  - `Lessons/tutorial_site/**/*.html`
  - `Lessons/tutorial_site/**/*.css`
  - `Lessons/tutorial_site/**/*.js`
- Video scenario inputs:
  - `Lessons/tutorial_site/media/*.story.md`
  - `Lessons/tutorial_site/media/*.directives.md`
- Video generation tools and wrappers:
  - `tools/browser_video_creator/**`
  - `tools/gui_demo_video_creator/**`
  - `tools/tutorial_video_creator/**`
- App behavior shown in tutorial outcome demo:
  - `task_manager/**` (except docs-only changes)

### Non-impacting (no render required)

- Repository/meta changes:
  - `.gitignore`
  - branch-only metadata or git config updates
- Documentation-only changes:
  - `*.md` files outside `Lessons/tutorial_site/media/*.story.md` and `Lessons/tutorial_site/media/*.directives.md`
- Comment-only or whitespace-only edits in code.

## Practical check flow

1. Collect changed files (`staged + unstaged`).
2. Match against impacting rules above.
3. If a matched code file changed only in comments/whitespace, treat it as non-impacting.
4. Render `release` only for impacted targets.

## Enforcement

The repository includes a tracked pre-push gate:

- Hook: `.githooks/pre-push`
- Checker: `tools/video_render_policy/check_release_gate.py`

Enable tracked hooks once per clone:

```powershell
git config core.hooksPath .githooks
```

Manual check options:

```powershell
# Validate exactly what is staged for commit
python tools/video_render_policy/check_release_gate.py --check-staged

# Validate what will be pushed for a branch range
python tools/video_render_policy/check_release_gate.py --range origin/main..HEAD
```

## Examples

- Changed only `.gitignore` -> no render.
- Changed only comments in `tools/gui_demo_video_creator/gui_demo_video_creator.py` -> no render.
- Changed timing/audio logic in video tools -> render impacted videos in `release`.
- Changed lesson HTML text/structure -> render `learning-process` in `release`.
- Changed `task_manager` runtime output/log behavior -> render `tutorial-outcome` in `release`.
