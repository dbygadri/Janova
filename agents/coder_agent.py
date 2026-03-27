from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass

from agents.base_agent import BaseAgent


@dataclass
class AppTemplate:
    slug: str
    title: str
    code: str


class CoderAgent(BaseAgent):
    agent_type = "coder"

    def __init__(self, workspace: str = "workspace") -> None:
        self.workspace = workspace
        os.makedirs(self.workspace, exist_ok=True)
        self.templates = self._build_templates()

    def _build_templates(self) -> list[AppTemplate]:
        return [
            AppTemplate(
                slug="calculatrice_tk",
                title="Calculatrice Tkinter",
                code='''import tkinter as tk\n\n\ndef compute():\n    expr = entry.get()\n    try:\n        result.set(str(eval(expr, {"__builtins__": {}}, {})))\n    except Exception:\n        result.set("Erreur")\n\nroot = tk.Tk()\nroot.title("Calculatrice JANOVA")\nroot.geometry("300x180")\n\nentry = tk.Entry(root, font=("Segoe UI", 13))\nentry.pack(fill="x", padx=10, pady=10)\n\ntk.Button(root, text="Calculer", command=compute).pack(pady=5)\nresult = tk.StringVar(value="Résultat")\ntk.Label(root, textvariable=result, font=("Segoe UI", 12)).pack(pady=10)\n\nroot.mainloop()\n''',
            ),
            AppTemplate(
                slug="calendrier_tk",
                title="Calendrier Tkinter",
                code='''import calendar\nimport datetime as dt\nimport tkinter as tk\n\nroot = tk.Tk()\nroot.title("Calendrier JANOVA")\nroot.geometry("420x320")\n\nyear = dt.datetime.now().year\nmonth = dt.datetime.now().month\ntext = tk.Text(root, font=("Consolas", 11))\ntext.pack(fill="both", expand=True, padx=10, pady=10)\ntext.insert("1.0", calendar.month(year, month))\ntext.configure(state="disabled")\n\nroot.mainloop()\n''',
            ),
            AppTemplate(
                slug="convertisseur_tk",
                title="Convertisseur Tkinter",
                code='''import tkinter as tk\n\n\ndef c_to_f():\n    try:\n        c = float(entry.get())\n        out.set(f"{(c * 9/5) + 32:.2f} °F")\n    except ValueError:\n        out.set("Entrée invalide")\n\nroot = tk.Tk()\nroot.title("Convertisseur JANOVA")\nroot.geometry("320x180")\n\nentry = tk.Entry(root, font=("Segoe UI", 12))\nentry.pack(padx=10, pady=10, fill="x")\ntk.Button(root, text="Celsius -> Fahrenheit", command=c_to_f).pack(pady=8)\nout = tk.StringVar(value="")\ntk.Label(root, textvariable=out, font=("Segoe UI", 12)).pack(pady=8)\n\nroot.mainloop()\n''',
            ),
            AppTemplate(
                slug="notes_tk",
                title="Notes Tkinter",
                code='''import tkinter as tk\nfrom tkinter import filedialog\n\n\ndef save():\n    path = filedialog.asksaveasfilename(defaultextension=".txt")\n    if not path:\n        return\n    with open(path, "w", encoding="utf-8") as f:\n        f.write(text.get("1.0", "end-1c"))\n\nroot = tk.Tk()\nroot.title("Notes JANOVA")\nroot.geometry("480x360")\n\ntk.Button(root, text="Sauvegarder", command=save).pack(anchor="ne", padx=10, pady=6)\ntext = tk.Text(root, wrap="word", font=("Segoe UI", 11))\ntext.pack(fill="both", expand=True, padx=10, pady=8)\n\nroot.mainloop()\n''',
            ),
        ]

    def _pick_template(self, request: str) -> AppTemplate:
        r = request.lower()
        if "calcul" in r:
            return self.templates[0]
        if "calend" in r:
            return self.templates[1]
        if "convert" in r:
            return self.templates[2]
        if "note" in r:
            return self.templates[3]
        return self.templates[0]

    def run(self, request: str) -> str:
        template = self._pick_template(request)
        project_dir = os.path.join(self.workspace, template.slug)
        os.makedirs(project_dir, exist_ok=True)
        main_file = os.path.join(project_dir, "main.py")

        with open(main_file, "w", encoding="utf-8") as f:
            f.write(template.code)

        return main_file

    @staticmethod
    def launch_python_file(path: str) -> str:
        subprocess.Popen([sys.executable, path], cwd=os.path.dirname(path))
        return path
