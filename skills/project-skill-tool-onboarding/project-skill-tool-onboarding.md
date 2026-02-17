# Project Skill/Tool Onboarding

## Purpose

Provide a repeatable workflow for:
- creating new project skills,
- adding new executable tools,
- and ensuring `SKILLS.md` + `TOOLS.md` registries exist and stay accurate.

## Step 1: Bootstrap registries (required)

Before adding anything else, ensure these files exist at project root:
- `SKILLS.md`
- `TOOLS.md`

If either file is missing, run:

```powershell
powershell -ExecutionPolicy Bypass -File tools/registry_bootstrapper/run.ps1
```

## Step 2: Add a new skill

1. Create a dedicated skill folder with a `SKILL.md` frontmatter file.
2. Create a dedicated details file for the skill (for example `<skill-name>.md`).
3. Add a row to `SKILLS.md` with:
- skill name,
- short description,
- file path to the dedicated details file.

## Step 3: Add a new tool

1. Add the tool as a dedicated folder under root `tools/`.
2. Use this baseline tool layout:

```text
tools/<tool-name>/
  run.ps1
  run.sh
  requirements.txt
  <tool-name>.py
```

3. Ensure tool inputs are LLM-usable:
- stable argument names,
- explicit defaults,
- clear value constraints,
- optional aliases for common phrasing.
4. Wrapper responsibility concept:
- create/reuse tool-local venv,
- install dependencies from local `requirements.txt`,
- install/check required system tools where practical,
- invoke Python script with forwarded args.
5. If practical, expose machine-readable schema output (for example `--print-schema`).
6. Add tool entry to `TOOLS.md` with:
- tool name,
- wrapper paths + python script path,
- purpose,
- invocation examples,
- JSON input schema,
- output artifacts.

## Registry templates

### SKILLS.md baseline

```markdown
# Skills Registry

This file lists all currently available skill scripts with name and description.

## Available skills

| Name | Description | File |
|---|---|---|
```

### TOOLS.md baseline

```markdown
# Tools Registry

This file lists executable tools and their LLM-usable argument schemas.
```

## Validation checklist

- `SKILLS.md` exists and is valid markdown.
- `TOOLS.md` exists and is valid markdown.
- New skill row appears in `SKILLS.md` and path resolves.
- New tool entry appears in `TOOLS.md` with schema block.
- If tool supports schema print, command runs successfully.

## Guardrails

- Do not add a skill without updating `SKILLS.md`.
- Do not add a tool without updating `TOOLS.md`.
- Do not document tool arguments informally only; always provide schema-style structure.
- Prefer one dedicated details file per skill instead of placing all logic in frontmatter file.
