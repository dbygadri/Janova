from __future__ import annotations

from typing import Any

import requests


class OllamaClient:
    def __init__(self, base_url: str = "http://127.0.0.1:11434", model: str = "mistral", timeout: int = 60) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(self, prompt: str, system: str = "") -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            text = data.get("response", "")
            return text.strip() or "(Réponse vide du modèle.)"
        except requests.Timeout:
            return "⚠️ Timeout Ollama: la génération a pris trop de temps."
        except requests.RequestException as exc:
            return f"⚠️ Erreur Ollama: {exc}"
        except ValueError:
            return "⚠️ Réponse Ollama invalide (JSON non lisible)."
