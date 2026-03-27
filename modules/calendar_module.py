from __future__ import annotations

import os

MODULE_INFO = {
    "name": "calendar_module",
    "description": "Crée un calendrier Tkinter.",
}


def can_handle(request: str) -> bool:
    r = request.lower()
    return "calendrier" in r or "calendar" in r


def handle(request: str, workspace: str) -> str:
    project_dir = os.path.join(workspace, "calendrier_tk")
    os.makedirs(project_dir, exist_ok=True)
    main_file = os.path.join(project_dir, "main.py")
    code = '''import calendar\nimport datetime as dt\nimport tkinter as tk\n\nroot = tk.Tk()\nroot.title("Calendrier JANOVA")\nroot.geometry("420x320")\nyear = dt.datetime.now().year\nmonth = dt.datetime.now().month\ntext = tk.Text(root, font=("Consolas", 11))\ntext.pack(fill="both", expand=True, padx=10, pady=10)\ntext.insert("1.0", calendar.month(year, month))\ntext.configure(state="disabled")\nroot.mainloop()\n'''
    with open(main_file, "w", encoding="utf-8") as f:
        f.write(code)
    return main_file
