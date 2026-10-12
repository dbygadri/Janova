from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

DEFAULT_TEACHERS = [{"type": "ollama", "model": "mistral", "url": "http://127.0.0.1:11434"}]


@dataclass
class Config:
    """Réglages de JANOVA. Tout est stocké dans un seul dossier (JANOVA_HOME, ~/.janova par défaut)."""

    home: Path
    teachers: list[dict] = field(default_factory=lambda: [dict(t) for t in DEFAULT_TEACHERS])
    skill_match_threshold: float = 0.55
    fact_match_threshold: float = 0.6
    sandbox_timeout: float = 5.0
    teacher_timeout: float = 120.0
    max_learning_attempts: int = 3
    history_size: int = 6

    @property
    def db_path(self) -> Path:
        return self.home / "janova.db"

    def editable(self) -> dict:
        data = asdict(self)
        data.pop("home")
        return data


def load_config(home: str | os.PathLike | None = None) -> Config:
    root = Path(home or os.environ.get("JANOVA_HOME") or Path.home() / ".janova").expanduser()
    root.mkdir(parents=True, exist_ok=True)
    config = Config(home=root)

    path = root / "config.json"
    if path.exists():
        for key, value in json.loads(path.read_text(encoding="utf-8")).items():
            if key != "home" and hasattr(config, key):
                setattr(config, key, value)
    else:
        path.write_text(json.dumps(config.editable(), ensure_ascii=False, indent=2), encoding="utf-8")
    return config
