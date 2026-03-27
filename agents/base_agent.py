from __future__ import annotations

from abc import ABC, abstractmethod


class BaseAgent(ABC):
    agent_type = "base"

    @abstractmethod
    def run(self, request: str) -> str:
        raise NotImplementedError
