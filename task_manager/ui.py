"""Minimal desktop UI for submitting a goal to the task manager application.

Separation of concerns:
- This module only handles user interface events and rendering.
- Business/application logic is invoked through an injected callback from `main.py`.
- Agent/OpenAI implementation details remain outside this file.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import scrolledtext
from typing import Callable


def create_window(submit_goal: Callable[[str], str]) -> tk.Tk:
    """Create and configure the minimal UI window."""
    root = tk.Tk()
    root.title("Task Manager UI")
    root.geometry("700x450")

    # Input section: goal text entered by the user.
    input_label = tk.Label(root, text="Goal")
    input_label.pack(anchor="w", padx=10, pady=(10, 4))

    goal_var = tk.StringVar()
    input_entry = tk.Entry(root, textvariable=goal_var, width=100)
    input_entry.pack(fill="x", padx=10)

    # Output section: displays the result returned by main application function.
    output_label = tk.Label(root, text="Output")
    output_label.pack(anchor="w", padx=10, pady=(12, 4))

    output_box = scrolledtext.ScrolledText(root, height=16, wrap="word")
    output_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def on_submit() -> None:
        """Submit click handler.

        UI delegates all goal processing to the injected backend callback
        and only displays text.
        """
        goal = goal_var.get().strip()
        result = submit_goal(goal)

        output_box.delete("1.0", tk.END)
        output_box.insert(tk.END, result)

    submit_button = tk.Button(root, text="Submit", command=on_submit)
    submit_button.pack(padx=10, pady=(0, 10), anchor="e")

    return root
