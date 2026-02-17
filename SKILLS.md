# Skills Registry

This file lists all currently available skill scripts with name and description.

## Available skills

| Name | Description | File |
|---|---|---|
| `tutorial-content-guidance` | Reusable writing/teaching quality rules for tutorial lesson content, structure, and validation flow. | `skills/tutorial-content-guidance.md` |
| `tutorial-style-notes` | Shared visual/content style constraints for lesson cards, prompts, checkpoints, and course consistency. | `skills/tutorial-style-notes.md` |
| `true-agent-video-demo` | Workflow for producing and integrating true agent demo videos (agent core + GUI wrapper) as primary tutorial media. | `skills/true-agent-video-demo/true-agent-video-demo.md` |
| `video-director-gui-demo` | Directing rules for realistic GUI demo recordings with human-like typing pace, timing delays, and visible progress/log instrumentation. | `skills/video-director-gui-demo/video-director-gui-demo.md` |
| `video-render-policy` | Project contract for default draft rendering, release rendering on commit/push, and render-only-when-impacting change detection. | `skills/video-render-policy/video-render-policy.md` |
| `project-skill-tool-onboarding` | Workflow for creating new skills and new tools, including bootstrapping `SKILLS.md` and `TOOLS.md` when missing. | `skills/project-skill-tool-onboarding/project-skill-tool-onboarding.md` |

## Notes

- Skill details for `true-agent-video-demo` live in `skills/true-agent-video-demo/true-agent-video-demo.md`.
- Skill details for `video-director-gui-demo` live in `skills/video-director-gui-demo/video-director-gui-demo.md`.
- Skill details for `video-render-policy` live in `skills/video-render-policy/video-render-policy.md`.
- Skill details for `project-skill-tool-onboarding` live in `skills/project-skill-tool-onboarding/project-skill-tool-onboarding.md`.
- Project tools follow the `tools/<tool-name>/` package pattern (`run.ps1`, `run.sh`, `requirements.txt`, `<tool-name>.py`).
- Use `TOOLS.md` for executable tool contracts and argument schemas.
