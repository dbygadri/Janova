from __future__ import annotations

import importlib
import os
import pkgutil
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable
from uuid import uuid4

from agents.coder_agent import CoderAgent
from agents.planner_agent import PlannerAgent
from core.memory import JanovaMemory
from core.ollama_client import OllamaClient
from core.registry import JsonRegistry, utc_now_iso
from core.state import JanovaState


class JanovaOrchestrator:
    """Central brain for routing user requests to LLM, modules, or agents."""

    def __init__(self) -> None:
        os.makedirs("data", exist_ok=True)
        os.makedirs("workspace", exist_ok=True)

        self.ollama = OllamaClient()
        self.memory = JanovaMemory()
        self.state = JanovaState()
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._callbacks: list[Callable[[str], None]] = []
        self._callback_lock = threading.Lock()
        self._agents_lock = threading.Lock()

        self.conversations = JsonRegistry(
            "data/janova_conversations.json",
            default_factory=lambda: {"conversations": [{"id": "default", "title": "Général", "messages": []}]},
        )
        self.agents_registry = JsonRegistry("data/agents_registry.json", default_factory=lambda: {"agents": []})
        self.modules_registry = JsonRegistry("data/modules_registry.json", default_factory=lambda: {"modules": []})

        self.modules = self._load_modules()

    def register_event_callback(self, callback: Callable[[str], None]) -> None:
        with self._callback_lock:
            self._callbacks.append(callback)

    def _emit(self, message: str) -> None:
        with self._callback_lock:
            for cb in self._callbacks:
                try:
                    cb(message)
                except Exception:
                    pass

    def _load_modules(self) -> dict[str, object]:
        discovered: dict[str, object] = {}
        registry_rows: list[dict] = []
        modules_pkg = importlib.import_module("modules")

        for module_info in pkgutil.iter_modules(modules_pkg.__path__):
            if module_info.name.startswith("_"):
                continue
            mod = importlib.import_module(f"modules.{module_info.name}")
            if all(hasattr(mod, name) for name in ("MODULE_INFO", "can_handle", "handle")):
                discovered[module_info.name] = mod
                info = getattr(mod, "MODULE_INFO")
                registry_rows.append(
                    {
                        "name": info.get("name", module_info.name),
                        "description": info.get("description", ""),
                        "module": module_info.name,
                    }
                )
        self.modules_registry.write({"modules": registry_rows})
        return discovered

    def _append_message(self, role: str, content: str, conversation_id: str = "default") -> None:
        payload = self.conversations.read()
        convs = payload.get("conversations", [])
        target = next((c for c in convs if c.get("id") == conversation_id), None)
        if target is None:
            target = {"id": conversation_id, "title": conversation_id, "messages": []}
            convs.append(target)
        target.setdefault("messages", []).append({"role": role, "content": content, "at": utc_now_iso()})
        self.conversations.write(payload)

    def get_conversations(self) -> list[dict]:
        return self.conversations.read().get("conversations", [])

    def list_agents(self) -> str:
        agents = self.agents_registry.read().get("agents", [])
        if not agents:
            return "Aucun agent enregistré."
        lines = [f"- {a['id']} | {a['type']} | {a['status']} | objectif: {a['objective']}" for a in agents[-10:]]
        return "Agents:\n" + "\n".join(lines)

    def list_modules(self) -> str:
        rows = self.modules_registry.read().get("modules", [])
        if not rows:
            return "Aucun module chargé."
        return "Modules:\n" + "\n".join(f"- {m['name']}: {m['description']}" for m in rows)

    def _new_agent_entry(self, agent_type: str, objective: str) -> dict:
        return {
            "id": str(uuid4())[:8],
            "type": agent_type,
            "objective": objective,
            "status": "running",
            "created_at": utc_now_iso(),
            "result": "",
            "error": "",
        }

    def _save_agent(self, entry: dict) -> None:
        with self._agents_lock:
            payload = self.agents_registry.read()
            payload.setdefault("agents", []).append(entry)
            self.agents_registry.write(payload)

    def _update_agent(self, agent_id: str, **updates: str) -> None:
        with self._agents_lock:
            payload = self.agents_registry.read()
            for row in payload.get("agents", []):
                if row.get("id") == agent_id:
                    row.update(updates)
                    break
            self.agents_registry.write(payload)

    def _launch_if_main(self, path: str) -> None:
        abs_path = os.path.abspath(path)
        if os.path.basename(abs_path) == "main.py" and os.path.exists(abs_path):
            subprocess.Popen([sys.executable, abs_path], cwd=os.path.dirname(abs_path))
            self.state.set_last_app_path(abs_path)

    def relaunch_last_app(self) -> str:
        path = self.state.get_last_app_path()
        if not path or not os.path.exists(path):
            return "Aucune application précédente à relancer."
        self._launch_if_main(path)
        return f"Application relancée: {path}"

    def handle_user_message(self, message: str) -> str:
        self._append_message("user", message)
        text = message.strip().lower()

        if text in {"liste les agents", "list agents"}:
            answer = self.list_agents()
            self._append_message("assistant", answer)
            return answer

        if text in {"liste les modules", "list modules"}:
            answer = self.list_modules()
            self._append_message("assistant", answer)
            return answer

        if "relance" in text and "derni" in text:
            answer = self.relaunch_last_app()
            self._append_message("assistant", answer)
            return answer

        if any(k in text for k in ["crée", "cree", "génère", "genere", "fabrique"]) and any(
            k in text for k in ["calculatrice", "calendrier", "convertisseur", "notes"]
        ):
            agent = self._new_agent_entry("coder", message)
            self._save_agent(agent)
            self.executor.submit(self._run_coder_agent, agent["id"], message)
            answer = f"Agent codeur lancé ({agent['id']}). Je reste disponible pendant l'exécution."
            self._append_message("assistant", answer)
            return answer

        for name, mod in self.modules.items():
            if mod.can_handle(message):
                try:
                    path = mod.handle(message, "workspace")
                    self.memory.mark_module_effective(name)
                    self.memory.log_success(f"Module {name} exécuté")
                    self._launch_if_main(path)
                    answer = f"Module {name} exécuté. Application créée: {path}"
                    self._append_message("assistant", answer)
                    return answer
                except Exception as exc:
                    err = f"Module {name} en échec: {exc}"
                    self.memory.log_error(err)

        if any(k in text for k in ["plan", "organise", "planning"]):
            agent = self._new_agent_entry("planner", message)
            self._save_agent(agent)
            self.executor.submit(self._run_planner_agent, agent["id"], message)
            answer = f"Agent planificateur lancé ({agent['id']})."
            self._append_message("assistant", answer)
            return answer

        answer = self.ollama.generate(
            prompt=message,
            system="Tu es JANOVA, IA locale orientée orchestration, concise et utile.",
        )
        self._append_message("assistant", answer)
        return answer

    def _run_coder_agent(self, agent_id: str, message: str) -> None:
        try:
            agent = CoderAgent(workspace="workspace")
            path = agent.run(message)
            self._launch_if_main(path)
            self._update_agent(agent_id, status="done", result=path)
            self.memory.log_success(f"Coder agent {agent_id} -> {path}")
            self._emit(f"✅ Agent codeur terminé ({agent_id}): {path}")
        except Exception as exc:
            self._update_agent(agent_id, status="error", error=str(exc))
            self.memory.log_error(f"Coder agent {agent_id} -> {exc}")
            self._emit(f"❌ Agent codeur en erreur ({agent_id}): {exc}")

    def _run_planner_agent(self, agent_id: str, message: str) -> None:
        try:
            agent = PlannerAgent()
            result = agent.run(message)
            self._update_agent(agent_id, status="done", result=result)
            self.memory.log_success(f"Planner agent {agent_id}")
            self._emit(f"✅ Agent planificateur terminé ({agent_id}).")
        except Exception as exc:
            self._update_agent(agent_id, status="error", error=str(exc))
            self.memory.log_error(f"Planner agent {agent_id} -> {exc}")
            self._emit(f"❌ Agent planificateur en erreur ({agent_id}): {exc}")
