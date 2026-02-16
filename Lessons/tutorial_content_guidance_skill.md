# Tutorial Content Guidance Skill

This file captures reusable content rules derived from the Lesson 0 feedback cycle.
Use it as a quality checklist when writing or revising any lesson.

## 1) Naming and section labels

- Keep lesson naming consistent and sequential:
  - `Lesson 0`, `Lesson 1`, `Lesson 2`, ...
- Avoid mixed naming like `Part` in one place and `Lesson` in another.
- If marker badges are used (for example `P1`, `P2`), they must be meaningful and incremental.
- Do not combine two numbering systems in one header (for example `P2` plus `0.1`).

## 2) Intro promises must be fulfilled

- If text says "here is a map", provide a real map/list immediately below.
- Do not use placeholder wording that implies structure without showing it.

## 3) Concept-first teaching flow

- Every lesson should follow this order:
  1. Explain concept in plain language.
  2. Show a simple concrete example.
  3. Present implementation prompt(s).
  4. Present student verification tasks.
  5. End with checkpoint/reflection.
- Do not jump directly into tasks before conceptual framing.

## 4) Terminology and novice readability

- Avoid advanced terms before they are explained.
- If a technical term is necessary, define it immediately or point to a clarifying diagram.
- Prefer beginner-friendly wording over jargon.

## 5) Development vs runtime separation (critical)

- Clearly state that Codex is a VS Code plugin/extension used during development.
- Clearly state that the generated runtime agent is a separate system.
- Explicitly state:
  - Codex creates the runtime agent.
  - Codex does not call/use that runtime agent as a tool.
  - The runtime agent is not aware of Codex.

## 6) Diagram quality standards

- Every diagram must answer "what does this illustrate?" without extra interpretation.
- Avoid ambiguous arrow chains.
- Prefer explicit two-lane diagrams when needed:
  - Development flow
  - Runtime flow
- After each diagram, include one short real example tied to the course project.

## 7) Project-grounded examples

- Use the course agent scenario consistently (human task planner).
- Tie abstract statements to concrete planner actions.
- For state-change statements (for example "tools affect system state"), provide one explicit action example and the resulting data change.

## 8) Section ordering logic

- Place identity/classification sections before rule sections when rules depend on those identities.
- Example pattern:
  - "Who/what components are"
  - "How they differ"
  - "What interactions are allowed or not allowed"

## 9) Scope context must be explicit

- If a section says "not in this course", explain why and in what context.
- For "enterprise features" (or any advanced scope boundary), add one-line explanations per bullet.
- Separate "Scope" and "Summary" into distinct sections to avoid cognitive overload.

## 10) Checkpoint design

- Keep checkpoint questions aligned with key lesson claims.
- Include reveal answers for active recall.
- Ensure at least one question checks the dev-vs-runtime distinction.

## 11) Consistency across lessons

- Keep content structure predictable so students spend attention on concepts, not format changes.
- Maintain one repeated pattern of:
  - concept
  - example
  - prompt
  - student task
  - checkpoint
- Use consistent tone: clear, calm, practical, and non-rushed.

## 12) Example progression strategy

- Use a two-step example strategy when teaching new concepts:
  - Start with a generic example to establish the abstract idea.
  - Then switch to the course-specific scenario (task planner) for clarity and transfer.
- Avoid jumping into domain-specific details before the generic pattern is understood.

## 13) Content de-duplication rule

- Do not explain the same flow twice in adjacent blocks unless each block has a different purpose.
- If two neighboring blocks repeat the same concept, merge them into one stronger example.
- Use "one concept, one primary block" whenever possible.

## 14) Roadmap usability rule

- If a roadmap card is present, make it actionable:
  - add anchors/links to target sections.
- Keep the roadmap concise and aligned with section markers/headings.

## 15) Scope-closure rule

- After listing excluded scope (for example enterprise-only features), add one explicit closure sentence:
  - why these items are excluded now
  - what learning benefit this simplification provides.
- This prevents "why are we skipping this?" confusion.

## 16) Wording guardrail for early lessons

- In foundational lessons, prefer plain phrasing like:
  - "application your users run"
  - "runtime process"
  - "development session"
- Delay advanced system-design vocabulary until the student has enough context.

## Quick author checklist

- Is naming consistent (`Lesson N`)?
- Is there a real map if map is promised?
- Is roadmap clickable/useful (if shown)?
- Are concepts explained before prompts?
- Are terms beginner-safe?
- Are examples generic-first then scenario-specific?
- Is duplicate explanation removed?
- Is Codex-vs-runtime separation explicit?
- Does every diagram have a concrete example?
- Are scope boundaries explained with context?
- Is there a clear scope-closure sentence?
- Is summary separated from scope?
- Are checkpoints aligned with core claims?
