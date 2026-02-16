# Tutorial Style Notes Skill

This is a skill-like reference for authoring lesson pages in this project.

## Purpose

Keep lesson delivery accurate, engaging, and visually consistent across the full course.

## Required style rules

- Use one shared color palette for all lessons and appendices.
- Use one shared headline pattern:
  - `Lesson N - Title`
  - `Appendix X - Title`
- Use one shared marker-icon pattern in headers (same shape, size, color treatment).
- Use one shared interaction pattern:
  - `Prompt to paste into Codex`
  - `Student task after generation`
- Use one shared checkpoint pattern:
  - each question has its own `Reveal answer` button.
- Keep prompt blocks visually distinct from student-task blocks.
- Keep all lessons on the same component system (cards, spacing, border radius, typography).
- Preserve mobile readability; do not rely on desktop-only layout assumptions.

## Clarity rules

- Never mix prompt text with student instructions in the same unlabeled block.
- Make execution order explicit:
  1. Send prompt to Codex.
  2. Review generated result.
  3. Run checkpoint questions.
- Keep architecture boundaries explicit in wording:
  - reasoning vs execution
  - agent vs MCP vs storage vs UI.

## Content fidelity rules

- Use lesson source files under `Lessons/md_only` as the factual base.
- Preserve core constraints from lessons:
  - deterministic boundaries
  - no hidden architecture changes
  - skills are reasoning-only, not execution.
