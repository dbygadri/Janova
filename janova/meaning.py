"""Le sens des phrases : comparer deux demandes par leur signification, pas seulement par leurs mots.

Un petit modèle d'embeddings (par exemple all-minilm, environ 46 Mo) transforme une phrase en vecteur ;
deux phrases de même sens donnent des vecteurs proches. Ce n'est pas un LLM : il ne génère rien et
tient sur un téléphone. Les vecteurs sont gardés en mémoire (SQLite) pour ne calculer chaque phrase
qu'une fois.

Si le modèle est injoignable, JANOVA continue avec la comparaison par mots (janova/text.py).
"""

from __future__ import annotations

import json
import math
import urllib.error
import urllib.request
from typing import Protocol

from janova.store import Store, sha


class EmbedderError(Exception):
    pass


class Embedder(Protocol):
    name: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class OllamaEmbedder:
    def __init__(self, model: str, url: str = "http://127.0.0.1:11434", timeout: float = 10.0) -> None:
        self.model = model
        self.url = url.rstrip("/")
        self.timeout = timeout
        self.name = f"ollama:{model}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        request = urllib.request.Request(
            f"{self.url}/api/embed",
            data=json.dumps({"model": self.model, "input": texts}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                vectors = json.loads(response.read().decode("utf-8")).get("embeddings", [])
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            raise EmbedderError(f"{self.name} injoignable : {exc}") from exc
        if len(vectors) != len(texts):
            raise EmbedderError(f"{self.name} a renvoyé {len(vectors)} vecteurs pour {len(texts)} phrases")
        return vectors


EMBEDDER_TYPES = {"ollama": OllamaEmbedder}


def build_embedder(spec: dict | None) -> Embedder | None:
    if not spec:
        return None
    spec = dict(spec)
    kind = spec.pop("type", "ollama")
    if kind not in EMBEDDER_TYPES:
        raise ValueError(f"Type de modèle de sens inconnu : {kind}")
    return EMBEDDER_TYPES[kind](**spec)


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


class Meaning:
    """Similarités de sens, avec cache des vecteurs. Se met en veille au premier échec du modèle."""

    def __init__(self, embedder: Embedder | None, store: Store) -> None:
        self.embedder = embedder
        self.store = store
        self.error = ""

    @property
    def active(self) -> bool:
        return self.embedder is not None and not self.error

    def similarities(self, query: str, texts: list[str]) -> list[float] | None:
        """Similarité de sens entre `query` et chaque texte, ou None si le sens n'est pas disponible."""
        if not self.active or not texts:
            return None
        try:
            vectors = self._vectors([query] + texts)
        except EmbedderError as exc:
            self.error = str(exc)
            return None
        return [cosine(vectors[0], v) for v in vectors[1:]]

    def _vectors(self, texts: list[str]) -> list[list[float]]:
        model = self.embedder.name
        keys = [sha(t) for t in texts]
        known = self.store.get_vectors(model, keys)
        missing = list(dict.fromkeys(t for t, k in zip(texts, keys) if k not in known))
        if missing:
            fresh = self.embedder.embed(missing)
            new = {sha(t): v for t, v in zip(missing, fresh)}
            self.store.put_vectors(model, new)
            known.update(new)
        return [known[k] for k in keys]
