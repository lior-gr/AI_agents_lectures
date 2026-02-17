# Tools Registry

This file lists executable tools and their LLM-usable argument schemas.

## Tool Packaging Concept

All project tools follow this structure under the root `tools/` directory:

- one folder per tool (`tools/<tool_name>/`)
- one Python implementation (`<tool_name>.py`)
- one `requirements.txt` scoped to that tool
- one `run.ps1` wrapper for Windows
- one `run.sh` wrapper for Linux/macOS

Wrapper scripts are responsible for:

- creating/reusing a local tool venv
- installing Python dependencies from the tool-local `requirements.txt`
- handling required system dependencies where practical
- invoking the Python tool with forwarded arguments

## Tool: `tutorial_video_creator`

- Wrapper (Windows): `tools/tutorial_video_creator/run.ps1`
- Wrapper (Linux/macOS): `tools/tutorial_video_creator/run.sh`
- Python script: `tools/tutorial_video_creator/tutorial_video_creator.py`
- Purpose: Build tutorial preview videos for the real agent + GUI wrapper walkthrough.

### Invocation examples

Generate both primary MP4 videos:

```powershell
powershell -ExecutionPolicy Bypass -File tools/tutorial_video_creator/run.ps1 `
  --output-mode both `
  --outcome-input "C:\recordings\agent-outcome.mp4" `
  --process-input "C:\recordings\agent-process.mp4"
```

Generate only process video and also create fallback copies:

```powershell
powershell -ExecutionPolicy Bypass -File tools/tutorial_video_creator/run.ps1 `
  --output-mode process `
  --process-input "C:\recordings\agent-process.mp4" `
  --generate-fallback-copies
```

Print machine-readable schema for LLM/tool integration:

```powershell
powershell -ExecutionPolicy Bypass -File tools/tutorial_video_creator/run.ps1 --print-schema
```

### Input schema

```json
{
  "tool": "tutorial_video_creator",
  "entrypoints": {
    "windows": "tools/tutorial_video_creator/run.ps1",
    "unix": "tools/tutorial_video_creator/run.sh",
    "python": "tools/tutorial_video_creator/tutorial_video_creator.py"
  },
  "type": "object",
  "additionalProperties": false,
  "required": [],
  "properties": {
    "media-dir": {
      "type": "string",
      "default": "Lessons/tutorial_site/media",
      "description": "Target media directory for outputs."
    },
    "outcome-input": {
      "type": "string",
      "default": "raw-outcome.mp4",
      "aliases": ["outcome-source-path"],
      "description": "Source clip for final tutorial outcome."
    },
    "process-input": {
      "type": "string",
      "default": "raw-process.mp4",
      "aliases": ["process-source-path"],
      "description": "Source clip for accelerated learning process."
    },
    "process-speed": {
      "type": "number",
      "minimum": 0.1,
      "default": 6.0,
      "aliases": ["speed-multiplier"],
      "description": "Playback acceleration for process clip."
    },
    "width": {
      "type": "integer",
      "minimum": 320,
      "default": 1280,
      "aliases": ["resolution-width"],
      "description": "Output width; height keeps aspect ratio."
    },
    "output-mode": {
      "type": "string",
      "enum": ["both", "outcome", "process"],
      "default": "both",
      "description": "Select which output videos to generate."
    },
    "ffmpeg-path": {
      "type": "string",
      "default": "",
      "description": "Optional explicit ffmpeg path or executable name."
    },
    "include-webm": {
      "type": "boolean",
      "default": false,
      "description": "Also generate .webm versions."
    },
    "create-demo-placeholders": {
      "type": "boolean",
      "default": false,
      "description": "Generate synthetic source clips when source videos are missing."
    },
    "generate-fallback-copies": {
      "type": "boolean",
      "default": false,
      "description": "Copy primary outputs to fallback file names used by the site."
    },
    "print-schema": {
      "type": "boolean",
      "default": false,
      "description": "Print tool schema JSON and exit."
    }
  }
}
```

### Output artifacts

- `tutorial-outcome.mp4`
- `learning-process-fast.mp4`
- `tutorial-outcome.webm` (optional)
- `learning-process-fast.webm` (optional)
- `tutorial-outcome-fallback.mp4` (optional copy)
- `learning-process-fast-fallback.mp4` (optional copy)

## Tool: `browser_video_creator`

- Wrapper (Windows): `tools/browser_video_creator/run.ps1`
- Wrapper (Linux/macOS): `tools/browser_video_creator/run.sh`
- Python script: `tools/browser_video_creator/browser_video_creator.py`
- Purpose: Generate real browser-recorded videos from local HTML pages, including concept slide decks and tutorial-site walkthrough clips with visible non-occluding mouse/click overlays.

### Invocation examples

Generate both tutorial videos from the local tutorial site with fallback copies:

```powershell
powershell -ExecutionPolicy Bypass -File tools/browser_video_creator/run.ps1 `
  --mode site-videos `
  --output-mode both `
  --browser chrome `
  --show-mouse-overlay `
  --pre-click-delay-seconds 1 `
  --generate-fallback-copies
```

Generate a single custom HTML tour video:

```powershell
powershell -ExecutionPolicy Bypass -File tools/browser_video_creator/run.ps1 `
  --mode html-tour `
  --tour-pages "index.html,lesson-0-foundations.html,lesson-2-agent-loop.html" `
  --tour-output "tutorial-site-tour.mp4"
```

Generate a slideshow video directly from concept text:

```powershell
powershell -ExecutionPolicy Bypass -File tools/browser_video_creator/run.ps1 `
  --mode concept-slideshow `
  --concept "Agent loop controls tool usage; MCP isolates execution; skills inject reasoning guidance." `
  --slideshow-output "agent-concepts.mp4"
```

Print machine-readable schema:

```powershell
powershell -ExecutionPolicy Bypass -File tools/browser_video_creator/run.ps1 --print-schema
```

### Input schema

```json
{
  "tool": "browser_video_creator",
  "entrypoints": {
    "windows": "tools/browser_video_creator/run.ps1",
    "unix": "tools/browser_video_creator/run.sh",
    "python": "tools/browser_video_creator/browser_video_creator.py"
  },
  "type": "object",
  "additionalProperties": false,
  "required": [],
  "properties": {
    "mode": {
      "type": "string",
      "enum": ["site-videos", "html-tour", "concept-slideshow"],
      "default": "site-videos"
    },
    "site-dir": {
      "type": "string",
      "default": "Lessons/tutorial_site"
    },
    "media-dir": {
      "type": "string",
      "default": "Lessons/tutorial_site/media"
    },
    "output-mode": {
      "type": "string",
      "enum": ["both", "outcome", "process"],
      "default": "both",
      "description": "Used when mode is site-videos."
    },
    "site-pages": {
      "type": "string",
      "default": "index.html,lesson-0-foundations.html,lesson-1-baseline.html,lesson-2-agent-loop.html,lesson-3-mcp-decoupling.html,lesson-4-skills.html,lesson-5-ui-boundary.html,appendix-a-multiple-skills.html,appendix-b-bounded-routing.html"
    },
    "tour-pages": {
      "type": "string",
      "default": "index.html,lesson-0-foundations.html,lesson-1-baseline.html"
    },
    "tour-output": {
      "type": "string",
      "default": "html-tour.mp4"
    },
    "concept": {
      "type": "string",
      "default": ""
    },
    "concept-file": {
      "type": "string",
      "default": ""
    },
    "slideshow-output": {
      "type": "string",
      "default": "concept-slideshow.mp4"
    },
    "slideshow-title": {
      "type": "string",
      "default": "Concept Slideshow"
    },
    "slide-duration": {
      "type": "number",
      "minimum": 0.5,
      "default": 3.0
    },
    "points-per-slide": {
      "type": "integer",
      "minimum": 1,
      "default": 4
    },
    "width": {
      "type": "integer",
      "minimum": 640,
      "default": 1280
    },
    "height": {
      "type": "integer",
      "minimum": 360,
      "default": 720
    },
    "fps": {
      "type": "integer",
      "minimum": 12,
      "default": 30
    },
    "browser": {
      "type": "string",
      "enum": ["auto", "chrome", "edge"],
      "default": "auto"
    },
    "browser-path": {
      "type": "string",
      "default": ""
    },
    "show-browser": {
      "type": "boolean",
      "default": false
    },
    "show-mouse-overlay": {
      "type": "boolean",
      "default": true
    },
    "pre-click-delay-seconds": {
      "type": "number",
      "minimum": 0.0,
      "default": 1.0
    },
    "ffmpeg-path": {
      "type": "string",
      "default": ""
    },
    "generate-fallback-copies": {
      "type": "boolean",
      "default": false
    },
    "print-schema": {
      "type": "boolean",
      "default": false
    }
  }
}
```

### Output artifacts

- `tutorial-outcome.mp4` (site-videos mode)
- `learning-process-fast.mp4` (site-videos mode)
- `tutorial-outcome-fallback.mp4` (optional copy)
- `learning-process-fast-fallback.mp4` (optional copy)
- custom tour output (html-tour mode)
- custom slideshow output (concept-slideshow mode)
- for each generated video file `name.mp4`:
  - `name.directives.md` (rendering/interaction directives + performance status)
  - `name.story.md` (narrative intent/beats + performance status)

## Tool: `gui_demo_video_creator`

- Wrapper (Windows): `tools/gui_demo_video_creator/run.ps1`
- Wrapper (Linux/macOS): `tools/gui_demo_video_creator/run.sh`
- Python script: `tools/gui_demo_video_creator/gui_demo_video_creator.py`
- Purpose: Launch the real `task_manager` PySide6 GUI, simulate directed user interactions with fixed character-rate typing, visible non-occluding mouse cursor cues, click highlights, and render an outcome video showing agent progress/logging and aligned ASCII-table results.

### Invocation examples

Generate tutorial outcome video (with fallback copy):

```powershell
powershell -ExecutionPolicy Bypass -File tools/gui_demo_video_creator/run.ps1 `
  --output "Lessons/tutorial_site/media/tutorial-outcome.mp4" `
  --fallback-output "Lessons/tutorial_site/media/tutorial-outcome-fallback.mp4"
```

Adjust directing pace:

```powershell
powershell -ExecutionPolicy Bypass -File tools/gui_demo_video_creator/run.ps1 `
  --type-words-per-second 3 `
  --avg-chars-per-word 5 `
  --pre-click-delay-seconds 1 `
  --post-type-wait-seconds 3 `
  --between-goals-wait-seconds 5
```

Print machine-readable schema:

```powershell
powershell -ExecutionPolicy Bypass -File tools/gui_demo_video_creator/run.ps1 --print-schema
```

### Input schema

```json
{
  "tool": "gui_demo_video_creator",
  "entrypoints": {
    "windows": "tools/gui_demo_video_creator/run.ps1",
    "unix": "tools/gui_demo_video_creator/run.sh",
    "python": "tools/gui_demo_video_creator/gui_demo_video_creator.py"
  },
  "type": "object",
  "additionalProperties": false,
  "required": [],
  "properties": {
    "output": { "type": "string", "default": "Lessons/tutorial_site/media/tutorial-outcome.mp4" },
    "fallback-output": { "type": "string", "default": "Lessons/tutorial_site/media/tutorial-outcome-fallback.mp4" },
    "generate-fallback-copy": { "type": "boolean", "default": true },
    "width": { "type": "integer", "default": 1366, "minimum": 900 },
    "height": { "type": "integer", "default": 820, "minimum": 600 },
    "fps": { "type": "integer", "default": 12, "minimum": 6 },
    "type-words-per-second": { "type": "number", "default": 3.0, "minimum": 0.5 },
    "avg-chars-per-word": { "type": "number", "default": 5.0, "minimum": 1.0 },
    "pre-click-delay-seconds": { "type": "number", "default": 1.0, "minimum": 0.0 },
    "post-type-wait-seconds": { "type": "number", "default": 3.0, "minimum": 0.0 },
    "between-goals-wait-seconds": { "type": "number", "default": 5.0, "minimum": 0.0 },
    "ffmpeg-path": { "type": "string", "default": "" },
    "max-demo-seconds": { "type": "integer", "default": 240, "minimum": 30 },
    "print-schema": { "type": "boolean", "default": false }
  }
}
```

### Output artifacts

- `tutorial-outcome.mp4` (default)
- `tutorial-outcome-fallback.mp4` (optional copy)
- for each generated video file `name.mp4`:
  - `name.directives.md` (rendering/interaction directives + performance status)
  - `name.story.md` (narrative intent/beats + performance status)

## Tool: `registry_bootstrapper`

- Wrapper (Windows): `tools/registry_bootstrapper/run.ps1`
- Wrapper (Linux/macOS): `tools/registry_bootstrapper/run.sh`
- Python script: `tools/registry_bootstrapper/registry_bootstrapper.py`
- Purpose: Create `SKILLS.md` and `TOOLS.md` when missing.

### Invocation examples

Create missing registries only:

```powershell
powershell -ExecutionPolicy Bypass -File tools/registry_bootstrapper/run.ps1
```

Force overwrite baseline templates:

```powershell
powershell -ExecutionPolicy Bypass -File tools/registry_bootstrapper/run.ps1 --project-root . --force
```

### Input schema

```json
{
  "tool": "registry_bootstrapper",
  "entrypoints": {
    "windows": "tools/registry_bootstrapper/run.ps1",
    "unix": "tools/registry_bootstrapper/run.sh",
    "python": "tools/registry_bootstrapper/registry_bootstrapper.py"
  },
  "type": "object",
  "additionalProperties": false,
  "required": [],
  "properties": {
    "project-root": {
      "type": "string",
      "default": ".",
      "description": "Project root where SKILLS.md and TOOLS.md should be created."
    },
    "force": {
      "type": "boolean",
      "default": false,
      "description": "Overwrite existing registry files with baseline templates."
    }
  }
}
```

### Output artifacts

- `SKILLS.md` (created/updated)
- `TOOLS.md` (created/updated)
