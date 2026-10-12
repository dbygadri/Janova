"""Banc d'essai de JANOVA avec de vrais professeurs.

    python -m bench                  # toutes les demandes (compter 15 à 60 min selon la machine)
    python -m bench --limite 5       # essai rapide

Chaque demande passe deux fois :
  1. « apprentissage » : JANOVA ne sait rien, elle doit apprendre auprès de ses professeurs ;
  2. « variante » : la même tâche avec d'autres valeurs ou une autre formulation. Elle devrait alors
     répondre seule, sans LLM, et juste.

La mémoire utilisée est temporaire : ta vraie mémoire (~/.janova) n'est pas touchée. Les professeurs et
le modèle de sens viennent de ton config.json. Le rapport est écrit en Markdown et en JSON.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

from janova.config import load_config
from janova.core import AUTONOMOUS_ROUTES, Janova
from janova.teachers import Entourage, TeacherError, build_teachers
from janova.text import normalize

REQUESTS_FILE = Path(__file__).with_name("demandes.json")
EXPECTED_ROUTE = {"competence": "apprend-competence", "connaissance": "apprend-connaissance", "conversation": "professeur"}


class CountingTeacher:
    """Enveloppe un professeur pour compter ses appels, ses erreurs et son temps de réponse."""

    def __init__(self, teacher) -> None:
        self.teacher = teacher
        self.name = teacher.name
        self.calls = 0
        self.errors = 0
        self.seconds = 0.0

    def ask(self, prompt: str, system: str = "") -> str:
        self.calls += 1
        start = time.perf_counter()
        try:
            return self.teacher.ask(prompt, system)
        except TeacherError:
            self.errors += 1
            raise
        finally:
            self.seconds += time.perf_counter() - start


def _clean(text: str) -> str:
    return " ".join(normalize(text).replace(",", ".").split())


def is_correct(answer: str, expected: list[str]) -> bool:
    answer = _clean(answer)
    for item in map(_clean, expected):
        if item.isalpha() and len(item) <= 3:
            if re.search(rf"\b{re.escape(item)}\b", answer):
                return True
        elif item in answer:
            return True
    return False


def run_request(janova: Janova, teachers: list[CountingTeacher], item: dict, phase: str) -> dict:
    message = item[phase]
    calls_before = sum(t.calls for t in teachers)
    start = time.perf_counter()
    reply = janova.handle(message)
    seconds = time.perf_counter() - start
    result = {
        "categorie": item["categorie"],
        "phase": phase,
        "demande": message,
        "route": reply.route,
        "reponse": reply.text,
        "secondes": round(seconds, 2),
        "appels_professeurs": sum(t.calls for t in teachers) - calls_before,
        "trace": list(janova.trace),
        "juste": is_correct(reply.text, item["contient"]) if phase == "variante" and item.get("contient") else None,
    }
    return result


def pct(part: int, total: int) -> str:
    return f"{part}/{total} ({100 * part / total:.0f} %)" if total else "—"


def summarize(results: list[dict]) -> dict:
    learn = [r for r in results if r["phase"] == "apprentissage"]
    variants = [r for r in results if r["phase"] == "variante"]
    reusable = [r for r in variants if r["categorie"] != "conversation"]
    checked = [r for r in variants if r["juste"] is not None]
    alone = [r for r in results if r["route"] in AUTONOMOUS_ROUTES]
    helped = [r for r in results if r["appels_professeurs"]]
    return {
        "classement_correct": (sum(r["route"] == EXPECTED_ROUTE[r["categorie"]] for r in learn), len(learn)),
        "competences_apprises": (
            sum(r["route"] == "apprend-competence" for r in learn if r["categorie"] == "competence"),
            sum(r["categorie"] == "competence" for r in learn),
        ),
        "connaissances_memorisees": (
            sum(r["route"] == "apprend-connaissance" for r in learn if r["categorie"] == "connaissance"),
            sum(r["categorie"] == "connaissance" for r in learn),
        ),
        "autonomie_variantes": (sum(r["route"] in AUTONOMOUS_ROUTES for r in reusable), len(reusable)),
        "variantes_justes": (sum(bool(r["juste"]) for r in checked), len(checked)),
        "variantes_justes_sans_llm": (
            sum(bool(r["juste"]) for r in checked if r["route"] in AUTONOMOUS_ROUTES),
            sum(r["route"] in AUTONOMOUS_ROUTES for r in checked),
        ),
        "temps_moyen_sans_llm": round(sum(r["secondes"] for r in alone) / len(alone), 2) if alone else None,
        "temps_moyen_avec_llm": round(sum(r["secondes"] for r in helped) / len(helped), 2) if helped else None,
        "appels_apprentissage": sum(r["appels_professeurs"] for r in learn),
        "appels_variantes": sum(r["appels_professeurs"] for r in variants),
    }


def markdown(info: dict, summary: dict, results: list[dict]) -> str:
    s = summary
    lines = [
        f"# Banc d'essai JANOVA — {info['date']}",
        "",
        f"- Professeurs : {', '.join(info['professeurs'])}",
        f"- Modèle de sens : {info['sens']}",
        f"- Demandes : {info['demandes']} tâches × 2 passages — durée totale {info['duree_minutes']} min",
        "",
        "## Résumé",
        "",
        "| Mesure | Résultat |",
        "|---|---|",
        f"| Demandes bien classées au 1er passage | {pct(*s['classement_correct'])} |",
        f"| Compétences apprises | {pct(*s['competences_apprises'])} |",
        f"| Connaissances mémorisées | {pct(*s['connaissances_memorisees'])} |",
        f"| **Taux d'autonomie sur les variantes** (sans LLM) | **{pct(*s['autonomie_variantes'])}** |",
        f"| Variantes répondues juste (toutes) | {pct(*s['variantes_justes'])} |",
        f"| Variantes répondues juste parmi celles faites sans LLM | {pct(*s['variantes_justes_sans_llm'])} |",
        f"| Temps moyen sans LLM / avec LLM | {s['temps_moyen_sans_llm']} s / {s['temps_moyen_avec_llm']} s |",
        f"| Appels aux professeurs : apprentissage / variantes | {s['appels_apprentissage']} / {s['appels_variantes']} |",
        "",
        "## Détail",
        "",
        "| Catégorie | Passage | Demande | Route | Juste | Temps | Appels |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        ok = {True: "✅", False: "❌", None: ""}[r["juste"]]
        demande = r["demande"].replace("|", "\\|")
        lines.append(
            f"| {r['categorie']} | {r['phase']} | {demande} | {r['route']} | {ok} | {r['secondes']} s"
            f" | {r['appels_professeurs']} |"
        )

    problems = [
        r for r in results
        if (r["phase"] == "apprentissage" and r["route"] != EXPECTED_ROUTE[r["categorie"]])
        or (r["phase"] == "variante" and r["categorie"] != "conversation" and r["route"] not in AUTONOMOUS_ROUTES)
        or r["juste"] is False
    ]
    if problems:
        lines += ["", "## Ce qui n'a pas marché", ""]
        for r in problems:
            lines += [
                f"### {r['phase']} — {r['demande']}",
                "",
                f"Attendu : {r['categorie']} · obtenu : {r['route']}",
                "",
                "Réponse :",
                "```",
                r["reponse"][:1500],
                "```",
            ]
            if r["trace"]:
                lines += ["Déroulement :", "```", "\n".join(r["trace"])[:4000], "```"]
            lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m bench", description="Banc d'essai de JANOVA")
    parser.add_argument("--config", help="dossier contenant config.json (par défaut JANOVA_HOME ou ~/.janova)")
    parser.add_argument("--sortie", default=".", help="dossier où écrire le rapport (par défaut : dossier courant)")
    parser.add_argument("--limite", type=int, help="ne prendre que les N premières tâches de chaque catégorie")
    args = parser.parse_args()
    sys.stdout.reconfigure(errors="replace")

    items = json.loads(REQUESTS_FILE.read_text(encoding="utf-8"))
    if args.limite:
        kept, seen = [], {}
        for item in items:
            seen[item["categorie"]] = seen.get(item["categorie"], 0) + 1
            if seen[item["categorie"]] <= args.limite:
                kept.append(item)
        items = kept

    config = load_config(args.config)
    teachers = [CountingTeacher(t) for t in build_teachers(config.teachers, config.teacher_timeout)]
    if not teachers:
        sys.exit("Aucun professeur dans config.json : le banc d'essai a besoin d'au moins un professeur.")
    for teacher in teachers:
        try:
            teacher.ask("Réponds seulement : OK")
        except TeacherError as exc:
            sys.exit(f"Professeur injoignable, vérifie qu'Ollama tourne et que le modèle est installé :\n{exc}")
    for teacher in teachers:
        teacher.calls = teacher.errors = 0
        teacher.seconds = 0.0

    started = time.perf_counter()
    results = []
    with tempfile.TemporaryDirectory(prefix="janova-banc-") as tmp:
        config.home = Path(tmp)
        janova = Janova(config, entourage=Entourage(teachers))
        try:
            total = 2 * len(items)
            for phase in ("apprentissage", "variante"):
                for item in items:
                    result = run_request(janova, teachers, item, phase)
                    results.append(result)
                    mark = {True: " ✅", False: " ❌", None: ""}[result["juste"]]
                    print(f"[{len(results)}/{total}] {phase:<13} {result['route']:<20} {result['secondes']:>6} s  "
                          f"{result['demande']}{mark}", flush=True)
            if janova.meaning.active:
                sense = janova.meaning.embedder.name
            elif janova.meaning.embedder is not None:
                sense = f"injoignable ({janova.meaning.error})"
            else:
                sense = "aucun"
        finally:
            janova.close()

    info = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "professeurs": [t.name for t in teachers],
        "sens": sense,
        "demandes": len(items),
        "duree_minutes": round((time.perf_counter() - started) / 60, 1),
    }
    summary = summarize(results)
    out = Path(args.sortie)
    out.mkdir(parents=True, exist_ok=True)
    stem = f"rapport-banc-{datetime.now():%Y%m%d-%H%M}"
    (out / f"{stem}.md").write_text(markdown(info, summary, results), encoding="utf-8")
    (out / f"{stem}.json").write_text(
        json.dumps({"info": info, "resume": summary, "resultats": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nTaux d'autonomie sur les variantes : {pct(*summary['autonomie_variantes'])}")
    print(f"Variantes justes : {pct(*summary['variantes_justes'])}")
    print(f"Rapport : {out / (stem + '.md')}")


if __name__ == "__main__":
    main()
