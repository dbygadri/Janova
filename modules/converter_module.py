from __future__ import annotations

import os

MODULE_INFO = {
    "name": "converter_module",
    "description": "Crée un convertisseur température Tkinter.",
}


def can_handle(request: str) -> bool:
    r = request.lower()
    return "convertisseur" in r or "convert" in r


def handle(request: str, workspace: str) -> str:
    project_dir = os.path.join(workspace, "convertisseur_tk")
    os.makedirs(project_dir, exist_ok=True)
    main_file = os.path.join(project_dir, "main.py")
    code = '''import tkinter as tk\n\n\ndef c_to_f():\n    try:\n        c = float(entry.get())\n        out.set(f"{(c * 9/5) + 32:.2f} °F")\n    except ValueError:\n        out.set("Entrée invalide")\n\nroot = tk.Tk()\nroot.title("Convertisseur JANOVA")\nroot.geometry("320x180")\nentry = tk.Entry(root, font=("Segoe UI", 12))\nentry.pack(padx=10, pady=10, fill="x")\ntk.Button(root, text="Celsius -> Fahrenheit", command=c_to_f).pack(pady=8)\nout = tk.StringVar(value="")\ntk.Label(root, textvariable=out, font=("Segoe UI", 12)).pack(pady=8)\nroot.mainloop()\n'''
    with open(main_file, "w", encoding="utf-8") as f:
        f.write(code)
    return main_file
