"""Comparaison de textes sans modèle : mots normalisés, nombres remplacés par <n>, similarité cosinus."""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from typing import Iterable, TypeVar

K = TypeVar("K")

STOPWORDS = {
    "a", "au", "aux", "avec", "c", "ce", "ces", "cette", "d", "dans", "de", "des", "du", "elle", "en", "est",
    "et", "il", "j", "je", "l", "la", "le", "les", "leur", "lui", "m", "ma", "me", "mes", "moi", "mon", "n",
    "ne", "nous", "on", "ou", "par", "pas", "plait", "pour", "qu", "que", "qui", "s", "sa", "se", "ses",
    "son", "sur", "svp", "stp", "t", "ta", "te", "tes", "toi", "ton", "tu", "un", "une", "vous", "y",
    "peux", "peut", "pourrais", "veux", "voudrais", "fais", "faire", "donne", "dis", "the", "of", "to", "is",
}

_TOKEN = re.compile(r"\d+(?:[.,]\d+)?|[a-z]+")


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def tokens(text: str) -> list[str]:
    out = []
    for tok in _TOKEN.findall(normalize(text)):
        if tok[0].isdigit():
            out.append("<n>")
        elif tok not in STOPWORDS:
            out.append(tok)
    return out


def similarity(a: str, b: str) -> float:
    ca, cb = Counter(tokens(a)), Counter(tokens(b))
    if not ca or not cb:
        return 0.0
    dot = sum(ca[t] * cb[t] for t in ca)
    return dot / (math.sqrt(sum(v * v for v in ca.values())) * math.sqrt(sum(v * v for v in cb.values())))


def best_match(query: str, candidates: Iterable[tuple[K, str]]) -> tuple[K | None, float]:
    best_key, best_score = None, 0.0
    for key, text in candidates:
        score = similarity(query, text)
        if score > best_score:
            best_key, best_score = key, score
    return best_key, best_score


def same_answer(a: str, b: str) -> bool:
    return " ".join(normalize(a).split()) == " ".join(normalize(b).split())
