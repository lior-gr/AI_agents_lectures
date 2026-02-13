# Clarification And Comment Log (Consolidated)

This version merges repeated iterations on the same issue into a single entry.

## Issue 1: Project structure and scope precision
1. Used prompt:
```text
Create a minimal cross-platform Python CLI project for a task manager.
Requirements:
Must work on Windows first
Use argparse
Store tasks in tasks.json
Create virtual environment instructions
Add comments explaining each file
Do NOT implement advanced features yet.
```
1.1. Highlighted section that drove later clarifications:
```text
Store tasks in tasks.json
Add comments explaining each file
```

2. Following clarification request:
```text
I forgot to add this to previous prompt:

Expected Output:

task_manager/
 ├── main.py
 ├── storage.py
 ├── tasks.json (auto-created later)
 ├── README.md
 └── requirements.txt (likely empty)
```
```text
Did you separate CLI from storage?

Did you comment every function?

Did you avoid premature features?

Did you include Windows PowerShell setup?

If not — correct it.
```

3. Improved prompt suggestion by Codex:
```text
Create a minimal cross-platform Python task manager in a folder named task_manager with exactly:
- main.py
- storage.py
- README.md
- requirements.txt

Do not create tasks.json initially; auto-create it on first write.
main.py must only handle argparse/dispatch.
storage.py must only handle JSON persistence.
Implement only add/list/done.
Add one explicit inline comment above every function (not just docstrings).
README must include Windows PowerShell venv setup and run commands.
```

## Issue 2: Command execution context in README
1. Used prompt:
```text
python main.py list
C:\Users\LiorGrinzaig_gyhkdg3\AppData\Local\Programs\Python\Python311\python.exe: can't open file 'C:\\Alphawave\\OneDrive - Alphawave IP Inc\\Documents\\Training\\AI basics\\src\\main.py': [Errno 2] No such file or directory
```

2. Following clarification request:
No extra clarification was needed; the error itself exposed the missing README context.

3. Improved prompt suggestion by Codex:
```text
In README, explicitly document both run contexts:
- From task_manager/: python main.py ...
- From src/: python task_manager\main.py ...
```

## Issue 3: Agent defaults (API key and temperature)
1. Used prompt:
```text
Create a new file agent.py.
Implement a minimal agent loop that:
Accepts a user goal string
Calls OpenAI chat completion API
Supports tool calling
Has max_steps=5
Logs each step
Does not exceed 800 tokens per call
Includes detailed comments explaining:
Where the loop is
Where tool calls are processed
Where stopping conditions are enforced
Do not implement tools yet.
Just stub them.

Expected Output
Codex should create:
agent.py


Containing:
A function like run_agent(goal: str)
A loop
A message history list
Tool call detection logic
Stop condition
```
1.1. Highlighted section that drove later clarifications:
```text
Calls OpenAI chat completion API
```

2. Following clarification request:
```text
Is the OpenAI key read from environment variable?
Is temperature low?
```
```text
1. document the api key method.
2. I want 0.2, yes.
```

3. Improved prompt suggestion by Codex:
```text
In agent.py, explicitly document that OpenAI() reads OPENAI_API_KEY from environment.
Set TEMPERATURE=0.2 and pass it in chat.completions.create.
Also document OPENAI_API_KEY setup in README for PowerShell and macOS/Linux.
```

## Issue 4: Tool schema explanation level
1. Used prompt:
```text
Create a new file agent.py.
Implement a minimal agent loop that:
Accepts a user goal string
Calls OpenAI chat completion API
Supports tool calling
Has max_steps=5
Logs each step
Does not exceed 800 tokens per call
Includes detailed comments explaining:
Where the loop is
Where tool calls are processed
Where stopping conditions are enforced
Do not implement tools yet.
Just stub them.

Expected Output
Codex should create:
agent.py


Containing:
A function like run_agent(goal: str)
A loop
A message history list
Tool call detection logic
Stop condition
```
1.1. Highlighted section that drove later clarifications:
```text
Includes detailed comments explaining:
Where the loop is
Where tool calls are processed
Where stopping conditions are enforced
```

2. Following clarification request:
```text
where are the tool schemas defined?
```
```text
add more comments explaining the scheme and it purpose. also explain what is mandatory and what is user defined.
```
```text
I don't understand the schema yet, for an example the "required" is a key that openai set or the user? if the user, who will know how to handle it?
```
```text
so, instead of "required" I could have used "my random key string": ["input"]?
```
```text
if "required" is a recognized JSON Schema keyword, who was the one that defined it?
the json schema is not clear. you should delete the current comments relating the tool schema (above and in-line) and start over by explaining it clearly to someone with no background.
```

3. Improved prompt suggestion by Codex:
```text
Define tool schemas in a TOOLS constant near the top of agent.py.
Write beginner-level comments that explicitly cover:
1) what TOOLS is for,
2) OpenAI tool wrapper keys vs JSON Schema keys,
3) that "required" is a JSON Schema standard keyword and cannot be renamed,
4) who enforces schema (model guidance + app-side validation),
5) one plain-language example of valid vs invalid argument JSON.
```
