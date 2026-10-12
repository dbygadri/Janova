"""L'entourage de JANOVA : les LLM qui lui enseignent.

Un professeur n'a qu'une méthode, `ask(prompt, system) -> str`. Ajouter un nouveau type de professeur,
c'est écrire une classe de plus et l'enregistrer dans TEACHER_TYPES.

Attention aux licences : OpenAI, Anthropic, Google… interdisent d'utiliser leurs réponses pour entraîner
un modèle concurrent. Ici les réponses servent à créer du code testé et des fiches de connaissances,
pas à entraîner un modèle ; si un jour JANOVA entraîne son propre petit modèle, il faudra n'utiliser que
des professeurs dont la licence le permet.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from janova.text import similarity


class TeacherError(Exception):
    pass


class Teacher(Protocol):
    name: str

    def ask(self, prompt: str, system: str = "") -> str: ...


class OllamaTeacher:
    def __init__(self, model: str, url: str = "http://127.0.0.1:11434", timeout: float = 120.0) -> None:
        self.model = model
        self.url = url.rstrip("/")
        self.timeout = timeout
        self.name = f"ollama:{model}"

    def ask(self, prompt: str, system: str = "") -> str:
        payload = {"model": self.model, "prompt": prompt, "system": system, "stream": False}
        request = urllib.request.Request(
            f"{self.url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                text = json.loads(response.read().decode("utf-8")).get("response", "").strip()
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            raise TeacherError(f"{self.name} injoignable : {exc}") from exc
        if not text:
            raise TeacherError(f"{self.name} a renvoyé une réponse vide")
        return text


TEACHER_TYPES = {"ollama": OllamaTeacher}


def build_teachers(specs: list[dict], timeout: float) -> list[Teacher]:
    teachers = []
    for spec in specs:
        spec = dict(spec)
        kind = spec.pop("type", "ollama")
        if kind not in TEACHER_TYPES:
            raise ValueError(f"Type de professeur inconnu : {kind}")
        teachers.append(TEACHER_TYPES[kind](timeout=timeout, **spec))
    return teachers


@dataclass
class Consensus:
    answer: str
    agreement: float
    sources: int


IGNORANCE = "je ne sais pas"


class Entourage:
    def __init__(self, teachers: list[Teacher]) -> None:
        self.teachers = teachers

    def ask_first(self, prompt: str, system: str = "") -> tuple[str, str]:
        """Interroge les professeurs dans l'ordre et renvoie (réponse, nom) du premier qui répond."""
        errors = []
        for teacher in self.teachers:
            try:
                return teacher.ask(prompt, system), teacher.name
            except TeacherError as exc:
                errors.append(str(exc))
        raise TeacherError("Aucun professeur disponible. " + " | ".join(errors))

    def consensus(self, prompt: str, system: str = "", min_similarity: float = 0.5) -> Consensus:
        """Pose la même question à tous les professeurs et garde la réponse la plus partagée.

        agreement = part des professeurs qui ont donné une réponse équivalente (1.0 = tous d'accord).
        """
        answers = []
        for teacher in self.teachers:
            try:
                answers.append(teacher.ask(prompt, system))
            except TeacherError:
                continue
        if not answers:
            raise TeacherError("Aucun professeur disponible.")

        known = [a for a in answers if IGNORANCE not in a.lower()]
        if not known:
            return Consensus(answers[0], 0.0, len(answers))
        best, supporters = known[0], 0
        for candidate in known:
            count = sum(1 for other in known if similarity(candidate, other) >= min_similarity)
            if count > supporters:
                best, supporters = candidate, count
        return Consensus(best, supporters / len(answers), len(answers))


def extract_json(text: str) -> dict:
    """Récupère le premier objet JSON d'une réponse de LLM (avec ou sans bloc ```json)."""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else text[text.find("{"): text.rfind("}") + 1]
    try:
        data = json.loads(candidate)
    except ValueError as exc:
        raise TeacherError(f"JSON illisible dans la réponse du professeur : {exc}") from exc
    if not isinstance(data, dict):
        raise TeacherError("Le professeur n'a pas renvoyé un objet JSON.")
    return data
