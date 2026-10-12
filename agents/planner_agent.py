from __future__ import annotations

from agents.base_agent import BaseAgent


class PlannerAgent(BaseAgent):
    agent_type = "planner"

    def run(self, request: str) -> str:
        return (
            "Plan court:\n"
            "1) Clarifier le besoin\n"
            "2) Découper en tâches simples\n"
            "3) Exécuter la première tâche\n"
            f"4) Suivre: {request.strip() or 'objectif utilisateur'}"
        )
