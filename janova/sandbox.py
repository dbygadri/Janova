"""Exécution isolée des compétences apprises.

Deux barrières :
1. analyse du code avant exécution : imports limités à une liste sûre, pas de fichiers, de réseau,
   d'eval/exec ni d'accès aux attributs internes (« _ ») qui permettent de sortir du cadre ;
2. exécution dans un processus Python séparé, isolé (-I), dans un dossier temporaire vide,
   sans variables d'environnement, avec une limite de temps (et de mémoire sous Linux/Android).

Ce n'est pas une prison parfaite : c'est un garde-fou raisonnable pour du code écrit par un LLM.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass

ALLOWED_IMPORTS = {
    "math", "cmath", "re", "datetime", "calendar", "json", "statistics", "fractions", "decimal", "random",
    "string", "itertools", "functools", "collections", "unicodedata", "textwrap", "operator", "heapq", "bisect",
}

FORBIDDEN_NAMES = {
    "open", "exec", "eval", "compile", "__import__", "globals", "locals", "vars", "input", "breakpoint",
    "getattr", "setattr", "delattr", "help", "exit", "quit", "memoryview", "type", "object", "super",
}

MEMORY_LIMIT_BYTES = 512 * 1024 * 1024

_RUNNER = r"""
import io, json, sys
job = json.loads(sys.stdin.read())
out, sys.stdout = sys.stdout, io.StringIO()
namespace = {"__name__": "competence"}
exec(compile(job["code"], "competence", "exec"), namespace)
results = []
for value in job["inputs"]:
    try:
        results.append([True, str(namespace["run"](value))])
    except Exception as exc:
        results.append([False, f"{type(exc).__name__}: {exc}"])
out.write(json.dumps(results))
"""


@dataclass
class RunResult:
    ok: bool
    output: str


def check_code(code: str) -> list[str]:
    """Renvoie la liste des raisons pour lesquelles le code est refusé (vide s'il est accepté)."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [f"Erreur de syntaxe : {exc}"]

    problems = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots = [alias.name.split(".")[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            roots = [(node.module or "").split(".")[0]]
        else:
            roots = []
        problems += [f"Import interdit : {r}" for r in roots if r not in ALLOWED_IMPORTS]

        if isinstance(node, ast.Name) and (node.id in FORBIDDEN_NAMES or node.id.startswith("__")):
            problems.append(f"Nom interdit : {node.id}")
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            problems.append(f"Attribut interdit : {node.attr}")
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            problems.append("global/nonlocal interdit")

    has_run = any(
        isinstance(n, ast.FunctionDef) and n.name == "run" and len(n.args.args) == 1 for n in tree.body
    )
    if not has_run:
        problems.append("Il faut une fonction run(demande) au premier niveau.")
    return problems


def _limit_memory() -> None:
    import resource

    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT_BYTES, MEMORY_LIMIT_BYTES))


def run_skill(code: str, inputs: list[str], timeout: float) -> list[RunResult]:
    problems = check_code(code)
    if problems:
        return [RunResult(False, "; ".join(problems)) for _ in inputs]

    env = {k: os.environ[k] for k in ("SYSTEMROOT",) if k in os.environ}
    with tempfile.TemporaryDirectory(prefix="janova-") as workdir:
        try:
            proc = subprocess.run(
                [sys.executable, "-I", "-X", "utf8", "-c", _RUNNER],
                input=json.dumps({"code": code, "inputs": inputs}),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=timeout,
                cwd=workdir,
                env=env,
                preexec_fn=_limit_memory if os.name == "posix" else None,
            )
        except subprocess.TimeoutExpired:
            return [RunResult(False, f"Temps dépassé ({timeout:g} s)") for _ in inputs]

    if proc.returncode != 0:
        error = (proc.stderr.strip().splitlines() or ["échec inconnu"])[-1]
        return [RunResult(False, error) for _ in inputs]
    try:
        return [RunResult(bool(ok), str(out)) for ok, out in json.loads(proc.stdout)]
    except (ValueError, TypeError):
        return [RunResult(False, "Sortie illisible") for _ in inputs]
