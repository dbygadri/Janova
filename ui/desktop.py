from __future__ import annotations

import tkinter as tk
import threading
from tkinter import ttk

from core.orchestrator import JanovaOrchestrator
from ui.chat_widgets import ChatBubble


class JanovaDesktopApp:
    def __init__(self, orchestrator: JanovaOrchestrator) -> None:
        self.orchestrator = orchestrator
        self.root = tk.Tk()
        self.root.title("JANOVA")
        self.root.geometry("1024x680")
        self.root.configure(bg="#16181D")

        self.status_var = tk.StringVar(value="Prêt")
        self.agent_status_var = tk.StringVar(value="Agents: idle")

        self._build_layout()
        self._load_history()

        self.orchestrator.register_event_callback(self._on_agent_event)
        self.root.after(1500, self._refresh_agent_status)

    def _build_layout(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        left = tk.Frame(self.root, bg="#111318", width=240)
        left.pack(side="left", fill="y")

        tk.Label(left, text="Conversations", bg="#111318", fg="#D0D3DB", font=("Segoe UI", 11, "bold")).pack(
            anchor="w", padx=12, pady=(12, 8)
        )
        self.conversations_list = tk.Listbox(
            left,
            bg="#1A1D24",
            fg="#D0D3DB",
            selectbackground="#2E5BFF",
            relief="flat",
            highlightthickness=0,
            font=("Segoe UI", 10),
        )
        self.conversations_list.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        right = tk.Frame(self.root, bg="#16181D")
        right.pack(side="left", fill="both", expand=True)

        top_bar = tk.Frame(right, bg="#1A1D24", height=46)
        top_bar.pack(fill="x")
        tk.Label(top_bar, text="JANOVA Desktop", bg="#1A1D24", fg="#E7E9EE", font=("Segoe UI", 11, "bold")).pack(
            side="left", padx=12, pady=10
        )
        tk.Label(top_bar, textvariable=self.agent_status_var, bg="#1A1D24", fg="#93A1B3", font=("Segoe UI", 9)).pack(
            side="right", padx=12
        )

        chat_host = tk.Frame(right, bg="#16181D")
        chat_host.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(chat_host, bg="#1D1F24", highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(chat_host, orient="vertical", command=self.canvas.yview)
        scroll.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=scroll.set)

        self.messages_frame = tk.Frame(self.canvas, bg="#1D1F24")
        self.canvas_window = self.canvas.create_window((0, 0), window=self.messages_frame, anchor="nw")

        self.messages_frame.bind("<Configure>", self._on_messages_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        bottom = tk.Frame(right, bg="#16181D")
        bottom.pack(fill="x", padx=10, pady=10)

        self.entry = tk.Entry(
            bottom,
            bg="#22262E",
            fg="#EFF2F7",
            insertbackground="#EFF2F7",
            relief="flat",
            font=("Segoe UI", 11),
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 8))
        self.entry.bind("<Return>", self._send_message)

        tk.Button(bottom, text="Envoyer", bg="#2E5BFF", fg="white", relief="flat", command=self._send_message).pack(
            side="left", padx=(0, 8)
        )
        tk.Button(bottom, text="Relancer dernière app", bg="#3A404D", fg="white", relief="flat", command=self._relaunch).pack(
            side="left"
        )

        status = tk.Label(self.root, textvariable=self.status_var, bg="#16181D", fg="#93A1B3", anchor="w")
        status.pack(fill="x", side="bottom", padx=12, pady=(0, 8))

    def _on_messages_configure(self, _event: tk.Event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _append_bubble(self, text: str, role: str) -> None:
        bubble = ChatBubble(self.messages_frame, text=text, role=role)
        bubble.pack(fill="x", anchor="w")
        self.root.after(50, lambda: self.canvas.yview_moveto(1.0))

    def _load_history(self) -> None:
        self.conversations_list.delete(0, tk.END)
        conversations = self.orchestrator.get_conversations()
        for conv in conversations:
            self.conversations_list.insert(tk.END, conv.get("title", conv.get("id", "Chat")))

        if conversations:
            for msg in conversations[0].get("messages", []):
                self._append_bubble(msg.get("content", ""), msg.get("role", "assistant"))

    def _send_message(self, _event=None) -> None:
        message = self.entry.get().strip()
        if not message:
            return
        self.entry.delete(0, tk.END)
        self._append_bubble(message, "user")
        self.status_var.set("JANOVA réfléchit...")

        def work() -> None:
            answer = self.orchestrator.handle_user_message(message)
            self.root.after(0, lambda: self._on_answer(answer))

        threading.Thread(target=work, daemon=True).start()

    def _on_answer(self, answer: str) -> None:
        self._append_bubble(answer, "assistant")
        self.status_var.set("Prêt")

    def _on_agent_event(self, event_message: str) -> None:
        self.root.after(0, lambda: self._append_bubble(event_message, "assistant"))

    def _refresh_agent_status(self) -> None:
        data = self.orchestrator.agents_registry.read().get("agents", [])
        running = sum(1 for a in data if a.get("status") == "running")
        self.agent_status_var.set(f"Agents actifs: {running}")
        self.root.after(1500, self._refresh_agent_status)

    def _relaunch(self) -> None:
        result = self.orchestrator.relaunch_last_app()
        self._append_bubble(result, "assistant")

    def run(self) -> None:
        self.root.mainloop()
