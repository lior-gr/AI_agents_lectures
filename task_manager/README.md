# Minimal Task Manager CLI

This folder contains a minimal, cross-platform Python command-line task manager.

## Files
- `main.py`: CLI entry point using `argparse` and command routing.
- `storage.py`: Task storage and basic task operations using `tasks.json`.
- `tasks.json`: Task data file; auto-created after the first write operation.
- `requirements.txt`: Dependency list for this project.

## Requirements
- Python 3.10+ (Windows, macOS, and Linux)

## Setup (Windows first)
1. Open PowerShell in `task_manager/`.
2. Create a virtual environment:
   ```powershell
   python -m venv .venv
   ```
3. Activate it:
   ```powershell
   .venv\Scripts\Activate.ps1
   ```
4. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
5. Run the CLI:
   ```powershell
   python main.py list
   ```
6. If you are in the parent `src/` folder instead, run:
   ```powershell
   python task_manager\main.py list
   ```

## Setup (macOS/Linux)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py list
```

## OpenAI API Key (for `agent.py`)
Set `OPENAI_API_KEY` before running agent code.

Windows PowerShell:
```powershell
$env:OPENAI_API_KEY="your_api_key_here"
```

macOS/Linux:
```bash
export OPENAI_API_KEY="your_api_key_here"
```

## Usage
```powershell
python main.py add "Buy milk"
python main.py add "Write report"
python main.py list
python main.py done 1
python main.py list
```

If running from the parent `src/` folder, prefix commands with `task_manager\`, for example:
```powershell
python task_manager\main.py list
```

## Agent mode (minimal behavior)
```powershell
python main.py --goal "Add buy milk and then show me all tasks"
```

Expected behavior:
- Agent calls `add_task`.
- Agent calls `list_tasks`.
- Agent stops.

No planning layer is intended yet; this mode is loop + tool execution only.

## Notes
- This is intentionally minimal: no priorities, due dates, tags, sync, or multi-user features yet.
