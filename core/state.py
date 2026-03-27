from __future__ import annotations

import os
from typing import Any

from core.registry import JsonRegistry, utc_now_iso


class JanovaState:
    def __init__(self, path: str = "data/janova_state.json") -> None:
        self.registry = JsonRegistry(
            path,
            default_factory=lambda: {
                "last_app_path": "",
                "updated_at": utc_now_iso(),
            },
        )

    def get(self) -> dict[str, Any]:
        return self.registry.read()

    def set_last_app_path(self, path: str) -> None:
        payload = self.registry.read()
        payload["last_app_path"] = os.path.abspath(path)
        payload["updated_at"] = utc_now_iso()
        self.registry.write(payload)

    def get_last_app_path(self) -> str:
        return self.registry.read().get("last_app_path", "")
