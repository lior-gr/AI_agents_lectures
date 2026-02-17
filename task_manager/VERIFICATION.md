# Verification Plan And Results

This file records concrete sanity checks for each tutorial stage.

## Lesson 1: Baseline scaffold and deterministic CLI

Sanity checks run:
- `python -m compileall main.py storage.py`
- `python main.py --add "Task A"`
- `python main.py --list`
- `python main.py --complete 1`
- `python main.py --delete 2`

Expected behavior:
- Commands are deterministic.
- `main.py` owns CLI dispatch.
- `storage.py` owns JSON persistence.

## Lesson 2: Tools + bounded agent loop + --goal

Sanity checks run:
- `python -m compileall main.py tools.py agent.py`
- Schema checks from tutorial:
  - `python -c "from pathlib import Path; s=Path('agent.py').read_text(encoding='utf-8'); print('run_agent' in s and 'max_steps' in s and 'stop' in s)"`
  - `python -c "from pathlib import Path; s=Path('agent.py').read_text(encoding='utf-8'); print('%(asctime)s [%(levelname)s] %(message)s' in s and 'agent_start' in s and 'tool_called' in s and 'stop' in s)"`
- Functional check with model call monkeypatch to avoid API spend while validating loop/tool flow.

Improved task wording:
- Original: "Run goal mode and confirm agent flow appears in logs."
- Better: "Run a monkeypatched model call that emits one tool call and one final response; assert tool_called/tool_result/stop events and task DB mutation."

## Lesson 3: MCP decoupling

Sanity checks run:
- `python -m compileall mcp_server.py mcp_client.py agent.py`
- Server request parsing checks via `mcp_server.handle_request(...)`
- Client subprocess checks via `execute_tool_via_mcp(...)`
- Agent flow check verifying tool results come through MCP response envelope.

## Lesson 4: Skills injection

Sanity checks run:
- `python -m compileall agent.py`
- Confirm skill files exist and are pure text.
- Confirm prompt construction injects skill text and loop/tool/MCP behavior is unchanged.

## Lesson 5: UI boundary + progress sidebar

Sanity checks run:
- `python -m compileall ui.py main.py`
- Shared backend check: `main.run_goal(..., progress_callback=...)` emits event objects with `time/type/name/details`.
- GUI launch check: `python main.py --gui`

Improved task wording:
- Original: "Run python main.py --gui and confirm the window opens correctly."
- Better: "If PySide6 is unavailable, confirm CLI returns a clear dependency error. After installing requirements, confirm window opens and progress updates live in both table/tree views."

## Appendix A: Deterministic routing

Sanity checks run:
- `python -m compileall skills_loader.py`
- Manual matrix verification using `load_skill_names(goal)` for all appendix examples.

## Appendix B: Bounded model-assisted routing

Sanity checks run:
- `python -m compileall skill_router.py`
- Validation tests:
  - valid JSON accepted
  - invalid JSON retried
  - unknown skills rejected
  - fail state returns `ok=False` with empty optional skills
- Agent bounded mode check confirms `always_on` still applies when routing fails.
