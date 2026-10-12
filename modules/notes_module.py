from __future__ import annotations

import os

MODULE_INFO = {
    "name": "notes_module",
    "description": "Crée une application de notes Tkinter.",
}


def can_handle(request: str) -> bool:
    r = request.lower()
    return "notes" in r or "note" in r


def handle(request: str, workspace: str) -> str:
    project_dir = os.path.join(workspace, "notes_tk")
    os.makedirs(project_dir, exist_ok=True)
    main_file = os.path.join(project_dir, "main.py")
    code = '''import tkinter as tk\nfrom tkinter import filedialog\n\n\ndef save():\n    path = filedialog.asksaveasfilename(defaultextension=".txt")\n    if not path:\n        return\n    with open(path, "w", encoding="utf-8") as f:\n        f.write(text.get("1.0", "end-1c"))\n\nroot = tk.Tk()\nroot.title("Notes JANOVA")\nroot.geometry("480x360")\ntk.Button(root, text="Sauvegarder", command=save).pack(anchor="ne", padx=10, pady=6)\ntext = tk.Text(root, wrap="word", font=("Segoe UI", 11))\ntext.pack(fill="both", expand=True, padx=10, pady=8)\nroot.mainloop()\n'''
    with open(main_file, "w", encoding="utf-8") as f:
        f.write(code)
    return main_file
