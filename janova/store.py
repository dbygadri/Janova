"""Mémoire de JANOVA (SQLite, un seul fichier) et journal chaîné.

Chaque apprentissage est inscrit dans le journal : chaque entrée contient l'empreinte (SHA-256) de la
précédente, comme les blocs d'une blockchain. Modifier une compétence ou une connaissance en douce,
ou réécrire une entrée du journal, est détecté par `verify()`.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from array import array
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

GENESIS = "0" * 64

SCHEMA = """
CREATE TABLE IF NOT EXISTS journal (
    id INTEGER PRIMARY KEY, at TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL,
    prev_hash TEXT NOT NULL, hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL, code TEXT NOT NULL,
    code_sha TEXT NOT NULL, examples TEXT NOT NULL, uses INTEGER NOT NULL DEFAULT 0,
    successes INTEGER NOT NULL DEFAULT 0, failures INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY, question TEXT NOT NULL, answer TEXT NOT NULL, answer_sha TEXT NOT NULL,
    sources INTEGER NOT NULL, agreement REAL NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS vectors (
    model TEXT NOT NULL, text_sha TEXT NOT NULL, vector BLOB NOT NULL, PRIMARY KEY (model, text_sha)
);
CREATE TABLE IF NOT EXISTS links (
    src TEXT NOT NULL, dst TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY (src, dst)
);
CREATE TABLE IF NOT EXISTS notes (
    key TEXT PRIMARY KEY, text TEXT NOT NULL, text_sha TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY, at TEXT NOT NULL, request TEXT NOT NULL, answer TEXT NOT NULL,
    route TEXT NOT NULL, ref INTEGER, feedback INTEGER
);
"""

MAX_EXAMPLES = 20


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _entry_hash(prev_hash: str, at: str, kind: str, payload: str) -> str:
    return sha(json.dumps([prev_hash, at, kind, payload], ensure_ascii=False))


@dataclass
class Skill:
    id: int
    name: str
    description: str
    code: str
    code_sha: str
    examples: list[str]
    uses: int
    successes: int
    failures: int
    active: bool


@dataclass
class Fact:
    id: int
    question: str
    answer: str
    sources: int
    agreement: float


class Store:
    def __init__(self, path: str | Path) -> None:
        self.db = sqlite3.connect(str(path))
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    def close(self) -> None:
        self.db.close()

    # --- Journal chaîné -------------------------------------------------------------------------

    def record(self, kind: str, **payload: object) -> str:
        row = self.db.execute("SELECT hash FROM journal ORDER BY id DESC LIMIT 1").fetchone()
        prev_hash = row["hash"] if row else GENESIS
        at = now()
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        digest = _entry_hash(prev_hash, at, kind, body)
        self.db.execute(
            "INSERT INTO journal (at, kind, payload, prev_hash, hash) VALUES (?, ?, ?, ?, ?)",
            (at, kind, body, prev_hash, digest),
        )
        return digest

    def head(self) -> str:
        """Empreinte de la dernière entrée du journal : elle change à chaque apprentissage ou oubli."""
        row = self.db.execute("SELECT hash FROM journal ORDER BY id DESC LIMIT 1").fetchone()
        return row["hash"] if row else GENESIS

    def journal(self, limit: int = 20) -> list[sqlite3.Row]:
        return self.db.execute("SELECT * FROM journal ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

    def verify(self) -> list[str]:
        """Renvoie la liste des problèmes d'intégrité (vide si tout est sain)."""
        problems = []
        prev_hash = GENESIS
        learned_skills: dict[int, str] = {}
        learned_facts: dict[int, str] = {}
        learned_notes: dict[str, str] = {}
        for row in self.db.execute("SELECT * FROM journal ORDER BY id"):
            if row["prev_hash"] != prev_hash:
                problems.append(f"Journal : chaîne rompue à l'entrée {row['id']}.")
            if _entry_hash(row["prev_hash"], row["at"], row["kind"], row["payload"]) != row["hash"]:
                problems.append(f"Journal : entrée {row['id']} modifiée.")
            prev_hash = row["hash"]
            try:
                payload = json.loads(row["payload"])
            except ValueError:
                continue
            if row["kind"] == "skill_learned":
                learned_skills[payload.get("skill_id")] = payload.get("code_sha")
            elif row["kind"] == "fact_learned":
                learned_facts[payload.get("fact_id")] = payload.get("answer_sha")
            elif row["kind"] == "note_edited":
                learned_notes[payload.get("key")] = payload.get("text_sha")

        for row in self.db.execute("SELECT id, name, code, code_sha FROM skills WHERE active = 1"):
            if sha(row["code"]) != row["code_sha"] or learned_skills.get(row["id"]) != row["code_sha"]:
                problems.append(f"Compétence {row['id']} ({row['name']}) : code différent de celui appris.")
        for row in self.db.execute("SELECT id, answer, answer_sha FROM facts"):
            if sha(row["answer"]) != row["answer_sha"] or learned_facts.get(row["id"]) != row["answer_sha"]:
                problems.append(f"Connaissance {row['id']} : réponse différente de celle apprise.")
        for row in self.db.execute("SELECT key, text, text_sha FROM notes"):
            if sha(row["text"]) != row["text_sha"] or learned_notes.get(row["key"]) != row["text_sha"]:
                problems.append(f"Note {row['key']} : texte différent de celui inscrit au journal.")
        return problems

    # --- Compétences ----------------------------------------------------------------------------

    def add_skill(self, name: str, description: str, code: str, examples: list[str], teacher: str) -> Skill:
        code_sha = sha(code)
        with self.db:
            cur = self.db.execute(
                "INSERT INTO skills (name, description, code, code_sha, examples, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (name, description, code, code_sha, json.dumps(examples[:MAX_EXAMPLES], ensure_ascii=False), now()),
            )
            self.record("skill_learned", skill_id=cur.lastrowid, name=name, code_sha=code_sha, teacher=teacher)
        return self.get_skill(cur.lastrowid)

    def get_skill(self, skill_id: int) -> Skill | None:
        row = self.db.execute("SELECT * FROM skills WHERE id = ?", (skill_id,)).fetchone()
        return self._skill(row) if row else None

    def skills(self, active_only: bool = True) -> list[Skill]:
        query = "SELECT * FROM skills" + (" WHERE active = 1" if active_only else "") + " ORDER BY id"
        return [self._skill(r) for r in self.db.execute(query)]

    def skill_used(self, skill: Skill, request: str) -> None:
        examples = skill.examples
        if request not in examples and len(examples) < MAX_EXAMPLES:
            examples = examples + [request]
        with self.db:
            self.db.execute(
                "UPDATE skills SET uses = uses + 1, examples = ? WHERE id = ?",
                (json.dumps(examples, ensure_ascii=False), skill.id),
            )

    def skill_feedback(self, skill_id: int, good: bool) -> Skill:
        column = "successes" if good else "failures"
        with self.db:
            self.db.execute(f"UPDATE skills SET {column} = {column} + 1 WHERE id = ?", (skill_id,))
        return self.get_skill(skill_id)

    def disable_skill(self, skill_id: int, reason: str) -> bool:
        with self.db:
            changed = self.db.execute("UPDATE skills SET active = 0 WHERE id = ? AND active = 1", (skill_id,)).rowcount
            if changed:
                self.record("skill_disabled", skill_id=skill_id, reason=reason)
        return bool(changed)

    @staticmethod
    def _skill(row: sqlite3.Row) -> Skill:
        return Skill(
            id=row["id"], name=row["name"], description=row["description"], code=row["code"],
            code_sha=row["code_sha"], examples=json.loads(row["examples"]), uses=row["uses"],
            successes=row["successes"], failures=row["failures"], active=bool(row["active"]),
        )

    # --- Connaissances --------------------------------------------------------------------------

    def add_fact(self, question: str, answer: str, sources: int, agreement: float) -> Fact:
        answer_sha = sha(answer)
        with self.db:
            cur = self.db.execute(
                "INSERT INTO facts (question, answer, answer_sha, sources, agreement, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (question, answer, answer_sha, sources, agreement, now()),
            )
            self.record("fact_learned", fact_id=cur.lastrowid, question=question, answer_sha=answer_sha,
                        sources=sources, agreement=agreement)
        return Fact(cur.lastrowid, question, answer, sources, agreement)

    def facts(self) -> list[Fact]:
        return [
            Fact(r["id"], r["question"], r["answer"], r["sources"], r["agreement"])
            for r in self.db.execute("SELECT * FROM facts ORDER BY id")
        ]

    def forget_fact(self, fact_id: int, reason: str) -> bool:
        with self.db:
            changed = self.db.execute("DELETE FROM facts WHERE id = ?", (fact_id,)).rowcount
            if changed:
                self.record("fact_forgotten", fact_id=fact_id, reason=reason)
        return bool(changed)

    # --- Cerveau : liens choisis et notes personnelles -------------------------------------------
    # Les clés désignent un élément du cerveau : c<id> pour une compétence, f<id> pour une connaissance.

    @staticmethod
    def _pair(a: str, b: str) -> tuple[str, str]:
        return (a, b) if a <= b else (b, a)

    def add_link(self, a: str, b: str) -> bool:
        src, dst = self._pair(a, b)
        with self.db:
            changed = self.db.execute(
                "INSERT OR IGNORE INTO links (src, dst, created_at) VALUES (?, ?, ?)", (src, dst, now())
            ).rowcount
            if changed:
                self.record("link_added", src=src, dst=dst)
        return bool(changed)

    def remove_link(self, a: str, b: str) -> bool:
        src, dst = self._pair(a, b)
        with self.db:
            changed = self.db.execute("DELETE FROM links WHERE src = ? AND dst = ?", (src, dst)).rowcount
            if changed:
                self.record("link_removed", src=src, dst=dst)
        return bool(changed)

    def links(self) -> list[tuple[str, str]]:
        return [(r["src"], r["dst"]) for r in self.db.execute("SELECT src, dst FROM links ORDER BY src, dst")]

    def notes(self) -> dict[str, str]:
        return {r["key"]: r["text"] for r in self.db.execute("SELECT key, text FROM notes")}

    def set_note(self, key: str, text: str) -> bool:
        """Enregistre la note personnelle d'un élément (vide = supprimée). Renvoie True si elle a changé."""
        text = text.strip()
        if self.notes().get(key, "") == text:
            return False
        text_sha = sha(text)
        with self.db:
            if text:
                self.db.execute(
                    "INSERT OR REPLACE INTO notes (key, text, text_sha, updated_at) VALUES (?, ?, ?, ?)",
                    (key, text, text_sha, now()),
                )
            else:
                self.db.execute("DELETE FROM notes WHERE key = ?", (key,))
            self.record("note_edited", key=key, text_sha=text_sha)
        return True

    # --- Vecteurs de sens (cache) ---------------------------------------------------------------

    def get_vectors(self, model: str, text_shas: list[str]) -> dict[str, list[float]]:
        found = {}
        for i in range(0, len(text_shas), 500):
            chunk = text_shas[i: i + 500]
            rows = self.db.execute(
                f"SELECT text_sha, vector FROM vectors WHERE model = ? AND text_sha IN ({','.join('?' * len(chunk))})",
                (model, *chunk),
            )
            found.update((r["text_sha"], array("f", r["vector"]).tolist()) for r in rows)
        return found

    def put_vectors(self, model: str, vectors: dict[str, list[float]]) -> None:
        with self.db:
            self.db.executemany(
                "INSERT OR REPLACE INTO vectors (model, text_sha, vector) VALUES (?, ?, ?)",
                [(model, key, array("f", vector).tobytes()) for key, vector in vectors.items()],
            )

    # --- Épisodes (ce qui s'est passé) ----------------------------------------------------------

    def add_episode(self, request: str, answer: str, route: str, ref: int | None = None) -> int:
        with self.db:
            cur = self.db.execute(
                "INSERT INTO episodes (at, request, answer, route, ref) VALUES (?, ?, ?, ?, ?)",
                (now(), request, answer, route, ref),
            )
        return cur.lastrowid

    def last_episode(self) -> sqlite3.Row | None:
        return self.db.execute("SELECT * FROM episodes ORDER BY id DESC LIMIT 1").fetchone()

    def set_feedback(self, episode_id: int, value: int) -> None:
        with self.db:
            self.db.execute("UPDATE episodes SET feedback = ? WHERE id = ?", (value, episode_id))

    def recent_episodes(self, limit: int) -> list[sqlite3.Row]:
        rows = self.db.execute("SELECT * FROM episodes ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return list(reversed(rows))

    def route_counts(self) -> dict[str, int]:
        return {r["route"]: r["n"] for r in self.db.execute("SELECT route, COUNT(*) AS n FROM episodes GROUP BY route")}
