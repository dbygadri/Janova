from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any


class JsonRegistry:
    """Thread-safe JSON registry helper."""

    def __init__(self, path: str, default_factory: Any) -> None:
        self.path = path
        self.default_factory = default_factory
        self._lock = threading.Lock()
        self._ensure_exists()

    def _ensure_exists(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        if not os.path.exists(self.path):
            self.write(self.default_factory())

    def read(self) -> Any:
        with self._lock:
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                data = self.default_factory()
                self.write(data)
                return data

    def write(self, data: Any) -> None:
        with self._lock:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)



def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
