from __future__ import annotations

import tkinter as tk


class ChatBubble(tk.Frame):
    def __init__(self, parent: tk.Widget, text: str, role: str) -> None:
        bg_user = "#2E5BFF"
        bg_assistant = "#2A2D35"
        fg = "#E8EAF0"
        bg = bg_user if role == "user" else bg_assistant
        anchor = "e" if role == "user" else "w"

        super().__init__(parent, bg="#1D1F24")
        label = tk.Label(
            self,
            text=text,
            bg=bg,
            fg=fg,
            wraplength=600,
            justify="left",
            padx=12,
            pady=8,
            font=("Segoe UI", 10),
        )
        label.pack(anchor=anchor, pady=4, padx=8)
