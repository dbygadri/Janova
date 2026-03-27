from __future__ import annotations

from core.registry import JsonRegistry, utc_now_iso


class JanovaMemory:
    def __init__(self, path: str = "data/janova_memory.json") -> None:
        self.registry = JsonRegistry(
            path,
            default_factory=lambda: {
                "preferences": {},
                "successful_tasks": [],
                "errors": [],
                "effective_modules": {},
                "updated_at": utc_now_iso(),
            },
        )

    def read(self) -> dict:
        return self.registry.read()

    def _save(self, data: dict) -> None:
        data["updated_at"] = utc_now_iso()
        self.registry.write(data)

    def add_preference(self, key: str, value: str) -> None:
        data = self.read()
        data.setdefault("preferences", {})[key] = value
        self._save(data)

    def log_success(self, item: str) -> None:
        data = self.read()
        data.setdefault("successful_tasks", []).append({"at": utc_now_iso(), "item": item})
        self._save(data)

    def log_error(self, item: str) -> None:
        data = self.read()
        data.setdefault("errors", []).append({"at": utc_now_iso(), "item": item})
        self._save(data)

    def mark_module_effective(self, module_name: str) -> None:
        data = self.read()
        table = data.setdefault("effective_modules", {})
        table[module_name] = table.get(module_name, 0) + 1
        self._save(data)
