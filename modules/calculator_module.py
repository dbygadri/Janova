from __future__ import annotations

import os

MODULE_INFO = {
    "name": "calculator_module",
    "description": "Crée une calculatrice Tkinter simple.",
}


def can_handle(request: str) -> bool:
    r = request.lower()
    return "calculatrice" in r or "calculator" in r


def handle(request: str, workspace: str) -> str:
    project_dir = os.path.join(workspace, "calculatrice_tk")
    os.makedirs(project_dir, exist_ok=True)
    main_file = os.path.join(project_dir, "main.py")
    code = '''import tkinter as tk\n\n\ndef compute():\n    expr = entry.get()\n    try:\n        result.set(str(eval(expr, {"__builtins__": {}}, {})))\n    except Exception:\n        result.set("Erreur")\n\nroot = tk.Tk()\nroot.title("Calculatrice JANOVA")\nroot.geometry("300x180")\nentry = tk.Entry(root, font=("Segoe UI", 13))\nentry.pack(fill="x", padx=10, pady=10)\ntk.Button(root, text="Calculer", command=compute).pack(pady=5)\nresult = tk.StringVar(value="Résultat")\ntk.Label(root, textvariable=result, font=("Segoe UI", 12)).pack(pady=10)\nroot.mainloop()\n'''
    with open(main_file, "w", encoding="utf-8") as f:
        f.write(code)
    return main_file
