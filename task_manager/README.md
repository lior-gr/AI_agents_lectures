# Task Manager Tutorial Project

This project follows the lesson flow from the tutorial site.

## Baseline goals
- Keep command parsing in `main.py`.
- Keep persistence in `storage.py`.
- Add advanced agent/MCP/skills/UI layers incrementally.

## PowerShell setup (Windows-first)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Commands
```powershell
python main.py --add "Buy milk"
python main.py --list
python main.py --complete 1
python main.py --delete 2
python main.py --delete 3 4
python main.py --goal "Plan my tasks for today"
python main.py --gui
```

## Notes
- `tasks_db.json` is auto-created on first storage access.
- `OPENAI_API_KEY` is required for live goal execution.
- `SKILL_ROUTING_MODE=bounded` (default) uses Appendix B router.
- `SKILL_ROUTING_MODE=deterministic` uses Appendix A keyword router.
- `VERIFICATION.md` contains step-by-step sanity checks.
