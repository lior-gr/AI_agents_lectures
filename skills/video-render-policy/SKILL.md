---
name: video-render-policy
description: Project contract for draft vs release rendering and for deciding when re-rendering is required before commit/push.
---

# Video Render Policy Skill

Use this skill when deciding whether to render videos and which encode profile to use.

## Skill details

Read and follow:
- `skills/video-render-policy/video-render-policy.md`

## Minimum completion criteria

- Default rendering profile is `draft`.
- On user requests to `commit`, `push`, or `commit and push`, check whether changes affect rendering output.
- Run `release` rendering only when rendering-impacting changes are present.
- Skip rendering when changes are non-impacting (for example docs/comments/.gitignore only).
